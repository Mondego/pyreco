__FILENAME__ = analyzer
# -*- coding: utf-8 -*-

from re import match
import re
from io import StringIO, BytesIO

class UnknownToken(Exception):
    ''' Unknown token error when trying to tokenize a single line '''
    def __init__(self, line, column, line_code):
        self.line_code = line_code
        self.line = line
        self.column = column
        super(UnknownToken, self).__init__(self.message)

    @property
    def message(self):
        msg = 'Unknown token @({line},{column}): {0}'
        return msg.format(self.line_code.rstrip(), **vars(self))


def code_line_generator(code):
    ''' A generator for lines from a file/string, keeping the \n at end '''
    if isinstance(code, unicode):
        stream = StringIO(code)
    elif isinstance(code, str):
        stream = BytesIO(code)
    else:
        stream = code # Should be a file input stream, already

    while True:
        line = stream.readline()
        if line:
            yield line
        else: # Line is empty (without \n) at EOF
            break


def analyse(code, token_types):
    for line, line_code in enumerate(code_line_generator(code), 1):
        column = 1
        while column <= len(line_code):
            remaining_line_code = line_code[column - 1:]
            for ttype in token_types:
                m = match(ttype['regex'], remaining_line_code, re.S)
                if m:
                    value = m.group(0)
                    if ttype['store']:
                        yield dict(
                            type=ttype['type'],
                            value=value,
                            line=line,
                            column=column
                        )
                    column += len(value)
                    break
            else:
                raise UnknownToken(line, column, line_code)


########NEW FILE########
__FILENAME__ = bitbag
# -*- coding: utf-8 -*-
from pynes.nes_types import NesRs, NesArray, NesSprite, NesString, NesChrFile
from pynes.game import PPUSprite


class BitPak:

    def __init__(self, game):
        self.game = game
        self.assigned = None

    def __call__(self):
        return None

    def asm(self):
        return ''

    def procedure(self):
        return None

    def attribute(self):
        return ''

    def assigned_to(self, assigned):
        self.assigned = assigned


class rs(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self, size):
        return NesRs(size)


class get_sprite(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self, sprite):
        return PPUSprite(sprite, self.game)


class wait_vblank(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self):
        return None

    def asm(self):
        return '  JSR WAITVBLANK\n'

    def procedure(self):
        return ('WAITVBLANK:\n'
                '  BIT $2002\n'
                '  BPL WAITVBLANK\n'
                '  RTS\n')


class clearmem(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def asm(self):
        return ('CLEARMEM:\n'
                '  LDA #$00\n'
                '  STA $0000, x\n'
                '  STA $0100, x\n'
                '  STA $0200, x\n'
                '  STA $0400, x\n'
                '  STA $0500, x\n'
                '  STA $0600, x\n'
                '  STA $0700, x\n'
                '  LDA #$FE\n'
                '  STA $0300, x\n'
                '  INX\n'
                '  BNE CLEARMEM\n')


class import_chr(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self, string):
        assert isinstance(string, NesString)
        return NesChrFile(string)


class define_sprite(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self, x, y, tile, attrib=0x80):
        assert isinstance(x, int)
        assert isinstance(y, int)
        assert isinstance(tile, int) or isinstance(tile, NesArray)
        return NesSprite(x, y, tile, attrib)


class cls(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self):
        self.line = self.game.get_param('line', 1)

    def asm(self):
        return '  JSR CLS\n'

    def procedure(self):
        return ('CLS:\n'
                '  LDA $2002\n'
                '  LDA $20\n'
                '  LDA $2006\n'
                '  LDA $00\n'
                '  LDA $2006\n'
                '  LDA #00\n'
                'LineLoop:'
                '  STA line\n'
                '  LDY #00\n'
                '  LDA #$25\n'  # blank == space
                'ColumnLoop:'
                '  STA $2007\n'
                '  INY'
                '  CPY #16\n'
                '  BNE ColumnLoop\n'
                '  LDA line\n'
                '  CLC\n'
                '  ADC #01\n'
                # '  STA line\n'
                '  CMP #16\n'
                '  BNE LineLoop\n'

                "  LDA #00\n"
                "  STA $2005\n"
                "  STA $2005\n")


class show(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)
        self.game.ppu.nmi_enable = True
        self.game.ppu.background_enable = True
        self.game.ppu.background_pattern_table = 1
        self.game.has_nmi = True

        self.addressLow = game.get_param('addressLow', 1)
        self.addressHigh = game.get_param('addressHigh', 1)
        self.posLow = game.get_param('posLow', 1)
        self.posHigh = game.get_param('posHigh', 1)

    def __call__(self, string, y=None, x=None, nametable=0):
        assert isinstance(string, NesString)
        string.is_used = True
        self.string = string
        base_adress = 0x2000

        if y is None:
            y = 15
        if x is None:
            x = 16 - len(string) / 2
        pos = base_adress + y * 32 + x
        self.posHigh = (pos & 0xff00) >> 8
        self.posLow = (pos & 0x00ff)

    def asm(self):
        asmcode = ("  LDA #LOW(%s)\n"
                   "  STA addressLow\n"
                   "  LDA #HIGH(%s)\n"
                   "  STA addressHigh\n"
                   "  LDA #$%02X\n"
                   "  STA posHigh\n"
                   "  LDA #$%02X\n"
                   "  STA posLow\n"
                   "  JSR Show\n") % (self.string.instance_name,
                                      self.string.instance_name,
                                      self.posHigh,
                                      self.posLow)
        return asmcode

    def procedure(self):
        asmcode = ("Show:\n"
                   "  LDA $2002\n"
                   "  LDA posHigh\n"
                   "  STA $2006\n"
                   "  LDA posLow\n"
                   "  STA $2006\n"
                   "  LDY #$00\n"
                   "PrintLoop:\n"
                   "  LDA (addressLow), y\n"
                   "  CMP #$25\n"
                   "  BEQ PrintEnd\n"
                   "  STA $2007\n"
                   "  INY\n"
                   "  JMP PrintLoop\n"
                   "PrintEnd:\n"
                   "  LDA #00\n"
                   "  STA $2005\n"
                   "  STA $2005\n"
                   "  RTS\n")
        return asmcode


class load_palette(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)

    def __call__(self, palette):
        assert isinstance(palette, NesArray)
        assert palette.instance_name is not None
        self.palette = palette
        return palette

    def asm(self):
        asmcode = (
            'LoadPalettes:\n'
            '  LDA $2002             ; Reset PPU, start writing\n'
            '  LDA #$3F\n'
            '  STA $2006             ; High byte = $3F00\n'
            '  LDA #$00\n'
            '  STA $2006             ; Low byte = $3F00\n'
            '  LDX #$00\n'
            'LoadPalettesIntoPPU:\n'
            '  LDA %s, x\n'
            '  STA $2007\n'
            '  INX\n') % self.palette.instance_name
        asmcode += '  CPX #$%02x\n' % len(self.palette)
        asmcode += '  BNE LoadPalettesIntoPPU\n'
        return asmcode


class load_sprite(BitPak):

    def __init__(self, game):
        BitPak.__init__(self, game)
        self.game.has_nmi = True  # TODO remove this
        self.game.ppu.sprite_enable = True
        self.game.ppu.nmi_enable = True

    def __call__(self, sprite, ppu_pos):
        assert isinstance(sprite, NesSprite)
        assert ppu_pos < 64
        self.sprite = sprite
        self.start_address = 0x0200 + (ppu_pos * 4)
        self.sprite.ppu_address = ppu_pos
        return None

    def asm(self):
        size = len(self.sprite)
        load_sprites = self.game.get_label_for('LoadSprites')
        load_sprites_into_PPU = self.game.get_label_for('LoadSpritesIntoPPU')
        '''
        Proposal
        with asm(self.game) as a:
            a.label('LoadSprites')
            a.ldx = 0
            a.lda = ('LoadSpritesIntoPPU', a.x)
            a.sta = (self.start_address, a.x)
            a.inx()
            a.cpx(size * 4)
            bne('LoadSpritesIntoPPU')
        '''
        asmcode = (
            '%s:\n'
            '  LDX #$00\n'
            '%s:\n'
            '  LDA %s, x\n'
            '  STA $%04X, x\n'
            '  INX\n'
            '  CPX #%d\n'
            '  BNE %s\n'
        ) % (load_sprites,
             load_sprites_into_PPU,
             self.sprite.instance_name,
             self.start_address,
             size * 4,
             load_sprites_into_PPU)
        return asmcode

########NEW FILE########
__FILENAME__ = c6502
# -*- coding: utf-8 -*-

address_mode_def = {}
address_mode_def['S_IMPLIED'] = dict(size=1, short='sngl')
address_mode_def['S_IMMEDIATE'] = dict(size=2, short='imm')
address_mode_def['S_IMMEDIATE_WITH_MODIFIER'] = dict(size=2, short='imm')
address_mode_def['S_ACCUMULATOR'] = dict(size=1, short='acc')
address_mode_def['S_IMMEDIATE'] = dict(size=2, short='imm')
address_mode_def['S_ZEROPAGE'] = dict(size=2, short='zp')
address_mode_def['S_ZEROPAGE_X'] = dict(size=2, short='zpx')
address_mode_def['S_ZEROPAGE_Y'] = dict(size=2, short='zpy')
address_mode_def['S_ABSOLUTE'] = dict(size=3, short='abs')
address_mode_def['S_ABSOLUTE_X'] = dict(size=3, short='absx')
address_mode_def['S_ABSOLUTE_Y'] = dict(size=3, short='absy')
address_mode_def['S_INDIRECT_X'] = dict(size=2, short='indx')
address_mode_def['S_INDIRECT_Y'] = dict(size=2, short='indy')
address_mode_def['S_RELATIVE'] = dict(size=2, short='rel')

opcodes = {}
opcodes['ADC'] = dict(imm=0x69, zp=0x65, zpx=0x75, abs=0x6d, absx=0x7d,
                      absy=0x79, indx=0x61, indy=0x71)
opcodes['AND'] = dict(imm=0x29, zp=0x25, zpx=0x35, abs=0x2d, absx=0x3d,
                      absy=0x39, indx=0x21, indy=0x31)
opcodes['ASL'] = dict(acc=0x0a, imm=0x0a, zp=0x06, zpx=0x16, abs=0x0e,
                      absx=0x1e)
opcodes['BCC'] = dict(rel=0x90)
opcodes['BCS'] = dict(rel=0xb0)
opcodes['BEQ'] = dict(rel=0xf0)
opcodes['BIT'] = dict(zp=0x24, abs=0x2c)
opcodes['BMI'] = dict(rel=0x30)
opcodes['BNE'] = dict(rel=0xd0)
opcodes['BPL'] = dict(rel=0x10)
opcodes['BVC'] = dict(rel=0x50)
opcodes['BVS'] = dict(rel=0x70)
opcodes['CLC'] = dict(sngl=0x18)
opcodes['CLD'] = dict(sngl=0xd8)
opcodes['CLI'] = dict(sngl=0x58)
opcodes['CLV'] = dict(sngl=0xb8)
opcodes['CMP'] = dict(imm=0xc9, zp=0xc5, zpx=0xd5, abs=0xcd, absx=0xdd,
                      absy=0xd9, indx=0xc1, indy=0xd1)
opcodes['CPX'] = dict(imm=0xe0, zp=0xe4, abs=0xec)
opcodes['CPY'] = dict(imm=0xc0, zp=0xc4, abs=0xcc)
opcodes['DEC'] = dict(zp=0xc6, zpx=0xd6, abs=0xce, absx=0xde)
opcodes['DEX'] = dict(sngl=0xca)
opcodes['DEY'] = dict(sngl=0x88)
opcodes['EOR'] = dict(imm=0x49, zp=0x45, zpx=0x55, abs=0x4d, absx=0x5d,
                      absy=0x59, indx=0x41, indy=0x51)
opcodes['INC'] = dict(zp=0xe6, zpx=0xf6, abs=0xee, absx=0xfe)
opcodes['INX'] = dict(sngl=0xe8)
opcodes['INY'] = dict(sngl=0xc8)
opcodes['JMP'] = dict(abs=0x4c)
opcodes['JSR'] = dict(abs=0x20)
opcodes['LDA'] = dict(imm=0xa9, zp=0xa5, zpx=0xb5, abs=0xad, absx=0xbd,
                      absy=0xb9, indx=0xa1, indy=0xb1)
opcodes['LDX'] = dict(imm=0xa2, zp=0xa6, zpy=0xb6, abs=0xae, absy=0xbe)
opcodes['LDY'] = dict(imm=0xa0, zp=0xa4, zpx=0xb4, abs=0xac, absx=0xbc)
opcodes['LSR'] = dict(acc=0x4a, imm=0x4a, zp=0x46, zpx=0x56, abs=0x4e,
                      absx=0x5e)
opcodes['NOP'] = dict(sngl=0xea)
opcodes['ORA'] = dict(imm=0x09, zp=0x05, zpx=0x15, abs=0x0d, absx=0x1d,
                      absy=0x19, indx=0x01, indy=0x11)
opcodes['PHA'] = dict(sngl=0x48)
opcodes['PHP'] = dict(sngl=0x08)
opcodes['PLA'] = dict(sngl=0x68)
opcodes['PLP'] = dict(sngl=0x28)
opcodes['SBC'] = dict(imm=0xe9, zp=0xe5, zpx=0xf5, abs=0xed, absx=0xfd,
                      absy=0xf9, indx=0xe1, indy=0xf1)
opcodes['SEC'] = dict(sngl=0x38)
opcodes['SED'] = dict(sngl=0xf8)
opcodes['SEI'] = dict(sngl=0x78)
opcodes['STA'] = dict(zp=0x85, zpx=0x95, abs=0x8d, absx=0x9d, absy=0x99,
                      indx=0x81, indy=0x91)
opcodes['STX'] = dict(zp=0x86, zpy=0x96, abs=0x8e)
opcodes['STY'] = dict(zp=0x84, zpx=0x94, abs=0x8c)
opcodes['ROL'] = dict(imm=0x2a, zp=0x26, zpx=0x36, abs=0x2e, absx=0x3e)
opcodes['ROR'] = dict(imm=0x6a, zp=0x66, zpx=0x76, abs=0x6e, absx=0x7e)
opcodes['RTI'] = dict(sngl=0x40)
opcodes['RTS'] = dict(sngl=0x60)
opcodes['TAX'] = dict(sngl=0xaa)
opcodes['TAY'] = dict(sngl=0xa8)
opcodes['TSX'] = dict(sngl=0xba)
opcodes['TXA'] = dict(sngl=0x8a)
opcodes['TXS'] = dict(sngl=0x9a)
opcodes['TYA'] = dict(sngl=0x98)

########NEW FILE########
__FILENAME__ = cartridge
class Cartridge:

    def __init__(self):
        self.banks = {}
        self.bank_id = 0
        self.pc = 0
        self.inespgr = 1
        self.ineschr = 1
        self.inesmap = 1
        self.inesmir = 1
        self.rs = 0
        self.path = ''

    def nes_id(self):
        # NES
        return [0x4e, 0x45, 0x53, 0x1a]

    def nes_get_header(self):
        id = self.nes_id()
        unused = [0, 0, 0, 0, 0, 0, 0, 0]
        header = []
        header.extend(id)
        header.append(self.inespgr)
        header.append(self.ineschr)
        header.append(self.inesmir)
        header.append(self.inesmap)
        header.extend(unused)
        return header

    def set_iNES_prg(self, inespgr):
        self.inespgr = inespgr

    def set_iNES_chr(self, ineschr):
        self.ineschr = ineschr

    def set_iNES_map(self, inesmap):
        self.inesmap = inesmap

    def set_iNES_mir(self, inesmir):
        self.inesmir = inesmir

    def set_bank_id(self, id):
        if id not in self.banks:
            self.banks[id] = dict(code=[], start=None, size=(1024 * 8))
        self.bank_id = id

    def set_org(self, org):
        if self.bank_id not in self.banks:
            self.set_bank_id(self.bank_id)
        if not self.banks[self.bank_id]['start']:
            self.banks[self.bank_id]['start'] = org
            self.pc = org
        else:
            while self.pc < org:
                self.append_code([0xff])
            self.pc = org

    def append_code(self, code):
        if self.bank_id not in self.banks:
            self.set_bank_id(self.bank_id)
        for c in code:
            assert c <= 0xff
        self.banks[self.bank_id]['code'].extend(code)
        self.pc += len(code)

    def get_code(self):
        if self.bank_id not in self.banks:
            self.set_bank_id(self.bank_id)
        return self.banks[self.bank_id]['code']

    def get_ines_code(self):
        if self.bank_id not in self.banks:
            self.set_bank_id(self.bank_id)
        bin = []
        nes_header = self.nes_get_header()
        bin.extend(nes_header)
        for i in self.banks:
            for j in range(len(self.banks[i]['code']), self.banks[i]['size']):
                self.banks[i]['code'].append(0xff)
            bin.extend(self.banks[i]['code'])
        return bin

########NEW FILE########
__FILENAME__ = compiler
# -*- coding: utf-8 -*-
from re import match

import pynes
from pynes.analyzer import analyse
from pynes.c6502 import opcodes, address_mode_def

import io
import inspect
from binascii import hexlify

from pynes.directives import directive_list
from pynes.cartridge import Cartridge


asm65_tokens = [
    dict(type='T_INSTRUCTION',
         regex=(r'^(ADC|AND|ASL|BCC|BCS|BEQ|BIT|BMI|BNE|BPL|BRK|BVC|BVS|CLC|'
                'CLD|CLI|CLV|CMP|CPX|CPY|DEC|DEX|DEY|EOR|INC|INX|INY|JMP|JSR|'
                'LDA|LDX|LDY|LSR|NOP|ORA|PHA|PHP|PLA|PLP|ROL|ROR|RTI|RTS|SBC|'
                'SEC|SED|SEI|STA|STX|STY|TAX|TAY|TSX|TXA|TXS|TYA)'),
         store=True),
    dict(type='T_ADDRESS', regex=r'\$([\dA-F]{2,4})', store=True),
    dict(type='T_HEX_NUMBER', regex=r'\#\$([\dA-F]{2})', store=True),
    dict(type='T_BINARY_NUMBER', regex=r'\#?%([01]{8})', store=True),
    dict(type='T_DECIMAL_NUMBER', regex=r'\#(\d{1,3})', store=True),
    dict(type='T_LABEL', regex=r'^([a-zA-Z]{2}[a-zA-Z\d]*)\:', store=True),
    dict(type='T_MARKER', regex=r'^[a-zA-Z]{2}[a-zA-Z\d]*', store=True),
    dict(type='T_STRING', regex=r'^"[^"]*"', store=True),
    dict(type='T_SEPARATOR', regex=r'^,', store=True),
    dict(type='T_ACCUMULATOR', regex=r'^(A|a)', store=True),
    dict(type='T_REGISTER', regex=r'^(X|x|Y|y)', store=True),
    dict(type='T_MODIFIER', regex=r'^(#LOW|#HIGH)', store=True),
    dict(type='T_OPEN', regex=r'^\(', store=True),
    dict(type='T_CLOSE', regex=r'^\)', store=True),
    dict(type='T_OPEN_SQUARE_BRACKETS', regex=r'^\[', store=True),
    dict(type='T_CLOSE_SQUARE_BRACKETS', regex=r'^\]', store=True),
    dict(type='T_DIRECTIVE', regex=r'^\.[a-z]+', store=True),
    dict(type='T_DECIMAL_ARGUMENT', regex=r'^[\d]+', store=True),
    dict(type='T_ENDLINE', regex=r'^\n', store=True),
    dict(type='T_WHITESPACE', regex=r'^[ \t\r]+', store=False),
    dict(type='T_COMMENT', regex=r'^;[^\n]*', store=False)
]


def look_ahead(tokens, index, type, value=None):
    if index > len(tokens) - 1:
        return 0
    token = tokens[index]
    if token['type'] == type:
        if value is None or token['value'].upper() == value.upper():
            return 1
    return 0


def t_endline(tokens, index):
    return look_ahead(tokens, index, 'T_ENDLINE', '\n')


def t_modifier(tokens, index):
    return look_ahead(tokens, index, 'T_MODIFIER')


def t_directive(tokens, index):
    return look_ahead(tokens, index, 'T_DIRECTIVE')


def t_directive_argument(tokens, index):
    return OR([t_list, t_address, t_marker, t_address,
               t_decimal_argument, t_string], tokens, index)


def t_decimal_argument(tokens, index):
    return look_ahead(tokens, index, 'T_DECIMAL_ARGUMENT')


def t_relative(tokens, index):
    if (look_ahead(tokens, index, 'T_INSTRUCTION')
            and tokens[index]['value'] in ['BCC', 'BCS', 'BEQ', 'BNE',
                                           'BMI', 'BPL', 'BVC', 'BVS']):
        return 1
    return 0


def t_instruction(tokens, index):
    return look_ahead(tokens, index, 'T_INSTRUCTION')


def t_zeropage(tokens, index):
    lh = look_ahead(tokens, index, 'T_ADDRESS')
    if lh and len(tokens[index]['value']) == 3:
        return 1
    return 0


def t_label(tokens, index):
    return look_ahead(tokens, index, 'T_LABEL')


def t_marker(tokens, index):
    return look_ahead(tokens, index, 'T_MARKER')


def t_address(tokens, index):
    return look_ahead(tokens, index, 'T_ADDRESS')


def t_string(tokens, index):
    return look_ahead(tokens, index, 'T_STRING')


def t_address_or_t_marker(tokens, index):
    return OR([t_address, t_marker], tokens, index)


def t_address_or_t_binary_number(tokens, index):
    return OR([t_address, t_binary_number], tokens, index)


def t_hex_number(tokens, index):
    return look_ahead(tokens, index, 'T_HEX_NUMBER')


def t_binary_number(tokens, index):
    return look_ahead(tokens, index, 'T_BINARY_NUMBER')


def t_decimal_number(tokens, index):
    return look_ahead(tokens, index, 'T_DECIMAL_NUMBER')


def t_number(tokens, index):
    return OR([t_hex_number, t_binary_number, t_decimal_number], tokens, index)


def t_separator(tokens, index):
    return look_ahead(tokens, index, 'T_SEPARATOR')


def t_accumulator(tokens, index):
    return look_ahead(tokens, index, 'T_ACCUMULATOR', 'A')


def t_register_x(tokens, index):
    return look_ahead(tokens, index, 'T_REGISTER', 'X')


def t_register_y(tokens, index):
    return look_ahead(tokens, index, 'T_REGISTER', 'Y')


def t_open(tokens, index):
    return look_ahead(tokens, index, 'T_OPEN', '(')


def t_close(tokens, index):
    return look_ahead(tokens, index, 'T_CLOSE', ')')


def t_open_square_brackets(tokens, index):
    return look_ahead(tokens, index, 'T_OPEN_SQUARE_BRACKETS', '[')


def t_close_square_brackets(tokens, index):
    return look_ahead(tokens, index, 'T_CLOSE_SQUARE_BRACKETS', ']')


def t_nesasm_compatible_open(tokens, index):
    return OR([t_open, t_open_square_brackets], tokens, index)


def t_nesasm_compatible_close(tokens, index):
    return OR([t_close, t_close_square_brackets], tokens, index)


def t_list(tokens, index):
    if (t_address_or_t_binary_number(tokens, index)
            and t_separator(tokens, index + 1)):
        islist = 1
        arg = 0
        while (islist):
            islist = islist and t_separator(tokens, index + (arg * 2) + 1)
            var_index = index + (arg * 2) + 2
            islist = islist and t_address_or_t_binary_number(tokens, var_index)
            if (t_endline(tokens, index + (arg * 2) + 3)
                    or (index + (arg * 2) + 3) == len(tokens)):
                break
            arg += 1
        if islist:
            return ((arg + 1) * 2) + 1
    return 0


def get_list_jump(tokens, index):
    keep = True
    a = 0
    while keep:
        keep = keep & (
            t_address(tokens, index + a) | t_separator(tokens, index + a))
        a += 1
    return a


def OR(args, tokens, index):
    for t in args:
        if t(tokens, index):
            return t(tokens, index)
    return 0

asm65_bnf = [
    dict(type='S_RS', bnf=[t_marker, t_directive, t_directive_argument]),
    dict(type='S_DIRECTIVE', bnf=[t_directive, t_directive_argument]),
    dict(type='S_RELATIVE', bnf=[t_relative, t_address_or_t_marker]),
    dict(type='S_IMMEDIATE', bnf=[t_instruction, t_number]),
    dict(type='S_IMMEDIATE_WITH_MODIFIER',
         bnf=[t_instruction, t_modifier, t_open, t_address_or_t_marker,
              t_close]),
    dict(type='S_ACCUMULATOR', bnf=[t_instruction, t_accumulator]),
    dict(type='S_ZEROPAGE_X',
         bnf=[t_instruction, t_zeropage, t_separator, t_register_x]),
    dict(type='S_ZEROPAGE_Y',
         bnf=[t_instruction, t_zeropage, t_separator, t_register_y]),
    dict(type='S_ZEROPAGE', bnf=[t_instruction, t_zeropage]),
    dict(type='S_ABSOLUTE_X',
         bnf=[t_instruction, t_address_or_t_marker, t_separator,
              t_register_x]),
    dict(type='S_ABSOLUTE_Y',
         bnf=[t_instruction, t_address_or_t_marker, t_separator,
              t_register_y]),
    dict(type='S_ABSOLUTE', bnf=[t_instruction, t_address_or_t_marker]),
    dict(type='S_INDIRECT_X',
         bnf=[t_instruction, t_nesasm_compatible_open, t_address_or_t_marker,
              t_separator, t_register_x, t_nesasm_compatible_close]),
    dict(type='S_INDIRECT_Y',
         bnf=[t_instruction, t_nesasm_compatible_open, t_address_or_t_marker,
              t_nesasm_compatible_close, t_separator, t_register_y]),
    dict(type='S_IMPLIED', bnf=[t_instruction]),
]


def lexical(code):
    return analyse(code, asm65_tokens) # A generator


def get_value(token, labels=[]):
    if token['type'] == 'T_ADDRESS':
        m = match(asm65_tokens[1]['regex'], token['value'])
        return int(m.group(1), 16)
    elif token['type'] == 'T_HEX_NUMBER':
        m = match(asm65_tokens[2]['regex'], token['value'])
        return int(m.group(1), 16)
    elif token['type'] == 'T_BINARY_NUMBER':
        m = match(asm65_tokens[3]['regex'], token['value'])
        return int(m.group(1), 2)
    elif token['type'] == 'T_DECIMAL_NUMBER':
        m = match(asm65_tokens[4]['regex'], token['value'])
        return int(m.group(1), 10)
    elif token['type'] == 'T_LABEL':
        m = match(asm65_tokens[5]['regex'], token['value'])
        return m.group(1)
    elif token['type'] == 'T_MARKER' and token['value'] in labels:
        return labels[token['value']]
    elif token['type'] == 'T_DECIMAL_ARGUMENT':
        return int(token['value'])
    elif token['type'] == 'T_STRING':
        return token['value'][1:-1]
    else:
        raise Exception('could not get value:' + token['type'] +
                        token['value'] + str(token['line']))


def syntax(tokens):
    tokens = list(tokens)
    ast = []
    x = 0  # consumed
    # debug = 0
    labels = []
    move = 0
    while (x < len(tokens)):
        if t_label(tokens, x):
            labels.append(get_value(tokens[x]))
            x += 1
        elif t_endline(tokens, x):
            x += 1
        else:
            for bnf in asm65_bnf:
                leaf = {}
                look_ahead = 0
                move = 0
                for i in bnf['bnf']:
                    move = i(tokens, x + look_ahead)
                    if not move:
                        break
                    look_ahead += 1
                if move:
                    if len(labels) > 0:
                        leaf['labels'] = labels
                        labels = []
                    size = 0
                    look_ahead = 0
                    for b in bnf['bnf']:
                        size += b(tokens, x + look_ahead)
                        look_ahead += 1
                    leaf['children'] = tokens[x: x + size]
                    leaf['type'] = bnf['type']
                    ast.append(leaf)
                    x += size
                    break
            if not move:
                # TODO: deal with erros like on nodeNES
                # walk = 0
                print('------------')
                print(tokens[x])
                print(tokens[x + 1])
                print(tokens[x + 2])
                print(tokens[x + 3])

                raise(Exception('UNKNOW TOKEN'))
    return ast


def get_labels(ast):
    labels = {}
    address = 0
    for leaf in ast:
        if ('S_DIRECTIVE' == leaf['type']
                and '.org' == leaf['children'][0]['value']):
            address = int(leaf['children'][1]['value'][1:], 16)
        if 'labels' in leaf:
            for label in leaf['labels']:
                labels[label] = address
        if leaf['type'] != 'S_DIRECTIVE' and leaf['type'] != 'S_RS':
            size = address_mode_def[leaf['type']]['size']
            address += size
        elif ('S_DIRECTIVE' == leaf['type']
                and '.db' == leaf['children'][0]['value']):
            for i in leaf['children']:
                if 'T_ADDRESS' == i['type']:
                    address += 1
        elif ('S_DIRECTIVE' == leaf['type']
                and '.incbin' == leaf['children'][0]['value']):
            address += 4 * 1024  # TODO check file size;
    return labels


def semantic(ast, iNES=False, cart=None):
    if cart is None:
        cart = Cartridge()
    labels = get_labels(ast)
    address = 0
    # translate statments to opcode
    for leaf in ast:
        if leaf['type'] == 'S_RS':
            labels[leaf['children'][0]['value']] = cart.rs
            cart.rs += get_value(leaf['children'][2])
        elif leaf['type'] == 'S_DIRECTIVE':
            directive = leaf['children'][0]['value']
            if len(leaf['children']) == 2:
                argument = get_value(leaf['children'][1], labels)
            else:
                argument = leaf['children'][1:]
            if directive in directive_list:
                directive_list[directive](argument, cart)
            else:
                raise Exception('UNKNOW DIRECTIVE')
        else:
            if leaf['type'] in ['S_IMPLIED', 'S_ACCUMULATOR']:
                instruction = leaf['children'][0]['value']
                address = False
            elif leaf['type'] == 'S_RELATIVE':
                instruction = leaf['children'][0]['value']
                address = get_value(leaf['children'][1], labels)
            elif leaf['type'] == 'S_IMMEDIATE_WITH_MODIFIER':
                instruction = leaf['children'][0]['value']
                modifier = leaf['children'][1]['value']
                address = get_value(leaf['children'][3], labels)
                if modifier == '#LOW':
                    address = (address & 0x00ff)
                elif modifier == '#HIGH':
                    address = (address & 0xff00) >> 8
            elif leaf['type'] in ['S_RELATIVE', 'S_IMMEDIATE', 'S_ZEROPAGE',
                                  'S_ABSOLUTE', 'S_ZEROPAGE_X',
                                  'S_ZEROPAGE_Y', 'S_ABSOLUTE_X',
                                  'S_ABSOLUTE_Y']:
                instruction = leaf['children'][0]['value']
                address = get_value(leaf['children'][1], labels)
            elif leaf['type'] in ['S_INDIRECT_X', 'S_INDIRECT_Y']:
                instruction = leaf['children'][0]['value']
                address = get_value(leaf['children'][2], labels)

            address_mode = address_mode_def[leaf['type']]['short']
            opcode = opcodes[instruction][address_mode]
            if address_mode != 'sngl' and address_mode != 'acc':
                if 'rel' == address_mode:
                    address = 126 + (address - cart.pc)
                    if address == 128:
                        address = 0
                    elif address < 128:
                        address = address | 0b10000000
                    elif address > 128:
                        address = address & 0b01111111

                if address_mode_def[leaf['type']]['size'] == 2:
                    cart.append_code([opcode, address])
                else:
                    arg1 = (address & 0x00ff)
                    arg2 = (address & 0xff00) >> 8
                    cart.append_code([opcode, arg1, arg2])
            else:
                cart.append_code([opcode])
    # nes_code = []
    if iNES:
        return cart.get_ines_code()
    else:
        return cart.get_code()


def compile_file(asmfile, output=None, path=None):
    from os.path import dirname, realpath

    if path is None:
        path = dirname(realpath(asmfile)) + '/'

    if output is None:
        output = 'output.nes'

    with io.open(asmfile, "r", encoding="utf-8") as f:
        opcodes = compile(f, path)

    pynes.write_bin_code(opcodes, output)


def compile(code, path):

    cart = Cartridge()
    cart.path = path

    tokens = lexical(code)
    ast = syntax(tokens)
    opcodes = semantic(ast, True, cart)

    return opcodes

########NEW FILE########
__FILENAME__ = composer
# -*- coding: utf-8 -*-

import pynes.compiler
import ast
from re import match
from inspect import getmembers

import pynes.bitbag  # TODO fix import to be able to remove this

from pynes.game import Game, PPU, PPUSprite, Joypad
from pynes.nes_types import NesType, NesInt, NesRs, NesArray, NesString, NesSprite, NesChrFile
from pynes.compiler import compile as nes_compile

from _ast import *


class OperationStack:

    def __init__(self):
        self._stack = []
        self._pile = []

    def __call__(self, operand=None):
        if operand is not None:
            self._stack.append(operand)
        return self._stack

    def store(self):
        if len(self._stack) > 0:
            self._pile.append(self._stack)
            self._stack = []

    def current(self):
        return self._stack

    def wipe(self):
        self._stack = []

    def last(self):
        if len(self._pile) > 0:
            return self._pile[-1]
        return []  # TODO if none breaks some len()

    def pendding(self):
        return self._pile

    def resolve(self):
        return self._pile.pop()


class PyNesTransformer(ast.NodeTransformer):

    def visit_Num(self, node):
        return Num(NesInt(node.n))

    def visit_List(self, node):
        expr = self.generic_visit(node)
        # print dir(expr)
        # lst = [l.n for l in expr.elts]
        # List(elts=[Num(n=1), Num(n=2), Num(n=3), Num(n=4)]
        return List(elts=expr.elts)
        return NesArray(expr.elts)

    def visit_Compare(self, node):
        expr = self.generic_visit(node)
        if (expr.left.id == '__name__' and
                len(expr.ops) == 1 and
                isinstance(expr.ops[0], Eq)):
            return Name(id='False', ctx=Load())
        # print dir(node)
        return expr

    def visit_If(self, node):
        expr = self.generic_visit(node)
        if (isinstance(expr.test, Name) and expr.test.id == 'False'):
            return None
        return expr


class PyNesVisitor(ast.NodeVisitor):

    def __init__(self):
        self.stack = OperationStack()

    def generic_visit(self, node, debug=False):
        if isinstance(node, list):
            for n in node:
                if debug:
                    print(n)
                self.visit(n)
        else:
            for field, value in reversed(list(ast.iter_fields(node))):
                if debug:
                    print(value)
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, ast.AST):
                            if debug:
                                print(item)
                            self.stack.store()
                            self.visit(item)
                elif isinstance(value, ast.AST):
                    self.visit(value)

    def visit_ImportFrom(self, node):
        pass  # TODO fix imports

    def visit_Import(self, node):
        pass  # TODO fix imports

    def visit_If(self, node):
        if 'comparators' not in dir(node.test):
            pass
        elif(len(node.test.comparators) == 1):
            # TODO: fix this hack, using just piles
            global game
            label = node.test.left.id
            index = node.test.comparators[0].n
            end = game.get_label_for('EndIf')
            elseif = game.get_label_for('ElseIf')
            game += '  LDA %s\n' % label
            game += '  CMP #%d\n' % index
            game += '  BNE %s\n' % elseif
            self.generic_visit(node.body)
            game += '  JMP %s\n' % end
            game += '%s:\n' % elseif
            self.generic_visit(node.orelse)
            game += '%s:\n' % end

    def visit_Expr(self, node):
        # TODO: perfect place to unpile list
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self.generic_visit(node)
        global game
        if len(self.stack.current()) == 2 and len(self.stack.last()) == 2:
            # TODO how to check
            # TODO op
            if (isinstance(self.stack.last()[0], int) and
                    isinstance(self.stack.last()[1], str) and
                    isinstance(self.stack.current()[0], PPUSprite) and
                    isinstance(self.stack.current()[1], str)):
                address = getattr(
                    self.stack.current()[0], self.stack.current()[1])
                self.stack.wipe()
                operation = self.stack.last()[1]
                operand = self.stack.resolve()
                if operation == '+':
                    address += operand[0]
                elif operation == '-':
                    address -= operand[0]
                game += address.to_asm()
        # TODO op
        # TODO how to check
        elif (len(self.stack.current()) == 3 and
              isinstance(self.stack.current()[0], int) and
                isinstance(self.stack.current()[1], str) and
                isinstance(self.stack.current()[2], NesRs)):
            operand = self.stack.current()[0]
            operation = self.stack.current()[1]
            rs = self.stack.current()[2]
            game += '  LDA %s\n' % rs.instance_name
            if operation == '+':
                game += (
                    '  CLC\n'
                    '  ADC #%02d\n') % operand
            elif operation == '-':
                game += (
                    '  SEC\n'
                    '  SBC #%02d\n') % operand
            game += '  STA %s\n' % rs.instance_name

    def visit_Assign(self, node):
        global game
        if (len(node.targets) == 1):
            if isinstance(node.value, ast.Call):
                self.generic_visit(node)
                varname = node.targets[0].id
                call = node.value
                if call.func.id:
                    if (len(self.stack.last()) == 1 and
                            isinstance(self.stack.last()[0], NesType)):
                        rs = self.stack.resolve()[0]
                        self.stack.wipe()
                        game.set_var(varname, rs)
            elif isinstance(node.value, ast.List):
                self.generic_visit(node)
                # TODO: just umpile
                varname = node.targets[0].id
                assert isinstance(self.stack.last()[0], NesArray)
                assert varname == self.stack.current()[0]
                lst = [l.n for l in node.value.elts]
                game.set_var(varname, NesArray(lst))
            elif isinstance(node.value, ast.Str):
                self.generic_visit(node)
                varname = node.targets[0].id
                assert isinstance(self.stack.last()[0], NesString)
                assert varname == self.stack.current()[0]
                value = self.stack.resolve()[0]
                self.stack.wipe()
                game.set_var(varname, value)
            elif 'ctx' in dir(node.targets[0]):  # TODO fix this please
                self.generic_visit(node)  # TODO: upthis
                if (len(self.stack.last()) == 1 and
                        isinstance(self.stack.last()[0], int)):
                    game += '  LDA #%02d\n' % self.stack.resolve()[0]
                if len(self.stack.current()) == 2:
                    address = getattr(
                        self.stack.current()[0], self.stack.current()[1])
                    game += '  STA $%04x\n' % address
                elif (len(self.stack.current()) == 1 and
                      isinstance(self.stack.current()[0], NesRs)):
                    rs = self.stack.current()[0]
                    self.stack.wipe()
                    name = rs.instance_name
                    game += ' STA %s\n' % name

    def visit_Attribute(self, node):
        self.generic_visit(node)
        attrib = node.attr
        self.stack(attrib)

    def visit_FunctionDef(self, node):
        global game
        if 'reset' == node.name:
            game.state = node.name.upper()
            game += game.init()
            self.generic_visit(node)
        elif 'nmi' == node.name:
            game.state = node.name.upper()
            self.generic_visit(node)
        elif match('^joypad[12]_(a|b|select|start|up|down|left|right)',
                   node.name):
            game.state = node.name
            self.generic_visit(node)
        else:
            game.state = node.name

    def visit_Call(self, node):
        global game
        if 'id' in dir(node.func):
            self.stack.store()
            if len(node.args) > 0:
                self.generic_visit(node.args)
                args = self.stack.current()
                self.stack.wipe()
            else:
                args = []
            print "call"
            print args

            # check this condition, seens strange
            if node.func.id not in game.bitpaks:
                obj = getattr(pynes.bitbag, node.func.id, None)
                if (obj):
                    try:
                        bp = obj(game)
                        game.bitpaks[node.func.id] = bp
                        self.stack(bp(*args))
                        game += bp.asm()
                    except TypeError as ex:
                        msg = ex.message.replace('__call__', node.func.id, 1)
                        raise(TypeError(msg))
                else:
                    raise(NameError("name '%s' is not defined" % node.func.id))
            else:
                bp = game.bitpaks[node.func.id]
                self.stack(bp(*args))
                game += bp.asm()
        else:
            self.generic_visit(node)
            attrib = getattr(
                self.stack.current()[0], self.stack.current()[1], None)
            self.stack.wipe()
            if callable(attrib):
                attrib()

    def visit_Add(self, node):
        self.stack('+')

    def visit_Sub(self, node):
        self.stack('-')

    def visit_BinOp(self, node):
        if (isinstance(node.left, ast.Num) and
                isinstance(node.right, ast.Num)):
            a = node.left.n
            b = node.right.n
            self.stack(a + b)
        else:
            self.generic_visit(node)

    def visit_Str(self, node):
        self.stack(NesString(node.s))

    def visit_List(self, node):
        self.stack(NesArray(node.elts))

    def visit_Num(self, node):
        self.stack(node.n)

    def visit_Name(self, node):
        if node.id in game._vars:
            value = game.get_var(node.id)
            value.instance_name = node.id
            self.stack(value)
        else:
            self.stack(node.id)  # TODO

game = None


def compose_file(input, output=None, path=None, asm=False):
    from os.path import dirname, realpath

    f = open(input)
    code = f.read()
    f.close()

    if path is None:
        path = dirname(realpath(input)) + '/'
    elif path[-1] != '/':
        path += '/'

    if output is None:
        output = 'output.nes'

    game = compose(code)
    asmcode = game.to_asm()
    if asm:
        asmfile = open('output.asm', 'w')
        asmfile.write(asmcode)
        asmfile.close()
    opcodes = nes_compile(asmcode, path)
    pynes.write_bin_code(opcodes, output)


def compose(code, game_program=game):
    global game
    if game_program is None:
        game = game_program = Game()

    python_land = ast.parse(code)

    builder = PyNesTransformer()
    builder.visit(python_land)

    turist = PyNesVisitor()
    turist.visit(python_land)

    python_land = ast.fix_missing_locations(python_land)

    # exec compile(python_land, '<string>', 'exec')

    game = None
    return game_program

########NEW FILE########
__FILENAME__ = directives
# -*- coding: utf-8 -*-


def d_inesprg(arg, cart):
    cart.set_iNES_prg(arg)


def d_ineschr(arg, cart):
    cart.set_iNES_chr(arg)


def d_inesmap(arg, cart):
    cart.set_iNES_map(arg)


def d_inesmir(arg, cart):
    cart.set_iNES_mir(arg)


def d_bank(arg, cart):
    cart.set_bank_id(arg)


def d_org(arg, cart):
    cart.set_org(arg)


def d_db(arg, cart):
    l = []
    for token in arg:
        if token['type'] == 'T_ADDRESS':
            l.append(int(token['value'][1:], 16))
    cart.append_code(l)


def d_dw(arg, cart):
    arg1 = (arg & 0x00ff)
    arg2 = (arg & 0xff00) >> 8
    cart.append_code([arg1, arg2])


def d_incbin(arg, cart):
    f = open(cart.path + arg, 'rw')
    content = f.read()
    for c in content:
        cart.append_code([ord(c)])


def d_rsset(arg, cart):
    pass


def d_rs(arg, cart):
    pass

directive_list = {}
directive_list['.inesprg'] = d_inesprg
directive_list['.ineschr'] = d_ineschr
directive_list['.inesmap'] = d_inesmap
directive_list['.inesmir'] = d_inesmir
directive_list['.bank'] = d_bank
directive_list['.org'] = d_org
directive_list['.db'] = d_db
directive_list['.dw'] = d_dw
directive_list['.incbin'] = d_incbin
directive_list['.rsset'] = d_rsset
directive_list['.rs'] = d_rs

########NEW FILE########
__FILENAME__ = helloworld
import pynes

from pynes.bitbag import *  

if __name__ == "__main__":
    pynes.press_start()
    exit()

palette = [
    0x22,0x29, 0x1A,0x0F, 0x22,0x36,0x17,0x0F,  0x22,0x30,0x21,0x0F,  0x22,0x27,0x17,0x0F,
    0x22,0x16,0x27,0x18,  0x22,0x1A,0x30,0x27,  0x22,0x16,0x30,0x27,  0x22,0x0F,0x36,0x17]

chr_asset = import_chr('mario.chr')

helloworld = "Hello World"

def reset():
    wait_vblank()
    clearmem()
    wait_vblank()
    load_palette(palette)
    show(helloworld, 15, 10)

########NEW FILE########
__FILENAME__ = mario
import pynes

from pynes.bitbag import *  

if __name__ == "__main__":
    pynes.press_start()
    exit()


palette = [
    0x22,0x29, 0x1A,0x0F, 0x22,0x36,0x17,0x0F,  0x22,0x30,0x21,0x0F,  0x22,0x27,0x17,0x0F,
    0x22,0x16,0x27,0x18,  0x22,0x1A,0x30,0x27,  0x22,0x16,0x30,0x27,  0x22,0x0F,0x36,0x17]

chr_asset = import_chr('mario.chr')

tinymario = define_sprite(108,144, [50,51,52,53], 0)

mario = define_sprite(128, 128, [0, 1, 2, 3, 4, 5, 6, 7], 0)

firemario = define_sprite(164,128, [0, 1, 2, 3, 4, 5, 6, 7], 0)

def reset():
    wait_vblank()
    clearmem()
    wait_vblank()
    load_palette(palette)
    load_sprite(tinymario, 0)
    load_sprite(mario, 4)
    load_sprite(firemario, 12)

def joypad1_up():
    get_sprite(mario).y -= 1

def joypad1_down():
    get_sprite(mario).y += 1

def joypad1_left():
    get_sprite(mario).x -= 1

def joypad1_right():
    get_sprite(mario).x += 1


########NEW FILE########
__FILENAME__ = movingsprite
import pynes

from pynes.bitbag import *  

if __name__ == "__main__":
    pynes.press_start()
    exit()

palette = [ 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,
        0x0F, 48, 49, 50, 51, 53, 54, 55, 56, 57, 58, 59,
        60, 61, 62, 63 ]

chr_asset = import_chr('player.chr')

sprite = define_sprite(128, 128, 0, 3)

def reset():
    global palette, sprite
    wait_vblank()
    clearmem()
    wait_vblank()
    load_palette(palette)
    load_sprite(sprite, 0)

def joypad1_up():
    get_sprite(0).y -= 1

def joypad1_down():
    get_sprite(0).y += 1

def joypad1_left():
    get_sprite(0).x -=1

def joypad1_right():
    get_sprite(0).x +=1

########NEW FILE########
__FILENAME__ = movingsprite_translated
import pynes

from pynes.game import Game
from pynes.bitbag import *
from pynes.nes_types import *

game = Game()

palette = game.assign('palette',
            NesArray([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,15,
                    0x0F, 48, 49, 50, 51, 53, 54, 55, 56, 57, 58, 59, 60, 61,
                    62, 63])
            )

sprite = game.assign('sprite', game.call('define_sprite', [128, 128, 0, 3]))

game.assign('chr_asset', NesChrFile('player.chr'))

game.asmFunction("reset")
game.call('wait_vblank')
game.call('clearmem')
game.call('wait_vblank')

game.call('load_palette', [palette])
game.call('load_sprite', [sprite, 0])

game.asmFunction("joypad1_up")

game.minusAssign(game.call('get_sprite', [0]).y, 1)

#game.asmFunction("joypad1_up")

#game.call(load_sprite(sprite, 0))

#game.asmFunction("reset")
#game.call(wait_vblank())
#game.call(clearmem())
#game.call(wait_vblank())
#game.call(load_palette(palette))


game.press_start()



'''
def waitvblank()
    asm.bit(0x2002)
    asm.bpl(waitvblank)


sprite = define_sprite(128, 128, 0, 3)

def reset():
    global palette, sprite
    wait_vblank()
    clearmem()
    wait_vblank()
    load_palette(palette)
    load_sprite(sprite, 0)

def joypad1_up():
    get_sprite(0).y -= 1

def joypad1_down():
    get_sprite(0).y += 1

def joypad1_left():
    get_sprite(0).x -=1

def joypad1_right():
    get_sprite(0).x +=1
'''
########NEW FILE########
__FILENAME__ = slides
import pynes

from pynes.bitbag import *  

palette = [
    0x22,0x29, 0x1A,0x0F, 0x22,0x36,0x17,0x0F,  0x22,0x30,0x21,0x0F,  0x22,0x27,0x17,0x0F,
    0x22,0x16,0x27,0x18,  0x22,0x1A,0x30,0x27,  0x22,0x16,0x30,0x27,  0x22,0x0F,0x36,0x17]

chr_asset = import_chr('mario.chr')

title = "pyNES"
subtitle = "Python Programming for NES"

gutomaia = "Guto Maia gutomaia"

slide1 = "slide 1111"
slide2 = "slide 2  2222"

slide = rs(1)
block = rs(1)
wait = rs(1)

def reset():
    wait_vblank()
    clearmem()
    wait_vblank()
    load_palette(palette)
    slide = 0
    block = 0
    wait = 0

def joypad1_a():
    if block == 0:
        slide += 1
        block = 1

def joypad1_b():
    if block == 0:
        slide -= 1
        block = 1

def nmi():
    if slide == 0:
        show(title, 5)
    elif slide == 1:
        show(subtitle, 8)
    elif slide == 2:
        show(slide2, 9,10)
    if block == 1:
        wait += 1

    if wait == 100:
        wait = 0
        block = 0

########NEW FILE########
__FILENAME__ = game
from re import match

from collections import OrderedDict
from pynes.nes_types import NesType, NesRs, NesArray, NesString, NesSprite, NesChrFile

# TODO remove this
from pynes.bitbag import *

import pynes


class Bit(object):

    def __init__(self, varname, bit, options=False):
        assert bit >= 0 and bit < 8
        self.varname = varname
        self.bit = bit

    def __get__(self, instance, owner):
        assert hasattr(instance, self.varname)
        flag = pow(2, self.bit)
        return getattr(instance, self.varname) & flag == flag

    def __set__(self, instance, value):
        assert isinstance(value, (bool, int))
        assert value == 0 or value == 1
        assert hasattr(instance, self.varname)
        flag = pow(2, self.bit)
        if not value:
            flag = (~flag & 0xFF)
            byte = getattr(instance, self.varname) & flag
        else:
            byte = getattr(instance, self.varname) | flag
        setattr(instance, self.varname, byte)


class PPU(object):

    # TODO base_nametable = Bit('ctrl', 1, options=[0,1,2,3]) #suports 0-3
    sprite_pattern_table = Bit('ctrl', 3)
    background_pattern_table = Bit('ctrl', 4)
    # TODO sprite_size = Bit('ctrl', 5, options=['8x8', '8x16'])
    nmi_enable = Bit('ctrl', 7)

    grayscale_enable = Bit('mask', 0)
    background_enable = Bit('mask', 3)
    sprite_enable = Bit('mask', 4)

    def __init__(self):
        self.ctrl = 0
        self.mask = 0
        self.scrolling = True

    def on_reset(self):
        asm = ('  LDA #%{ctrl:08b}\n'
               '  STA $2000\n'
               '  LDA #%{mask:08b}\n'
               '  STA $2001\n').format(
            ctrl=self.ctrl,
            mask=self.mask)
        return asm

    def on_nmi(self):
        if self.nmi_enable and self.scrolling:
            asm = (
                '  LDA #00\n'
                '  STA $2005\n'
                '  STA $2005\n')
            return asm
        return ''

# change to SpriteSwarmOperation


class NesAddressSet(NesType):

    def __init__(self, addresses, width):
        NesType.__init__(self)
        self.addresses = addresses
        self.width = width
        self.stk = ''
        self.total_addresses = len(addresses)

    def __add__(self, operand):
        self.stk += (
            '  LDA $%04X\n'
            '  CLC\n'
            '  ADC #%d\n') % (self.addresses[0], operand)
        # cols = this.total_addresses / 2  # width
        # lines = this.total_addresses / cols
        for i in range(self.total_addresses):
            self.stk += '  STA $%04X\n' % self.addresses[i]
            if ((i + 1) % self.width) == 0 and i < self.total_addresses - 1:
                self.stk += '  CLC\n  ADC #8\n'
        return self

    def __sub__(self, operand):
        self.addresses.reverse()
        self.stk += (
            '  LDA $%04X\n'
            '  SEC\n'
            '  SBC #%d\n') % (self.addresses[self.width - 1], operand)
        # cols = this.total_addresses / self.width
        # lines = this.total_addresses / cols
        for i in range(self.total_addresses):
            self.stk += '  STA $%04X\n' % self.addresses[i]
            if ((i + 1) % self.width) == 0 and i < self.total_addresses - 1:
                self.stk += '  SEC\n  SBC #8\n'
        self.addresses.reverse()
        return self

    def to_asm(self):
        return self.stk

# change to SpriteOperation


class NesAddress(int, NesType):

    def __new__(cls, val, **kwargs):
        inst = super(NesAddress, cls).__new__(cls, val)
        return inst

    def __init__(self, number):
        NesType.__init__(self)
        int.__init__(self, number)
        self.game = ''

    def __add__(self, operand):
        if isinstance(operand, int):
            self.game += '  LDA $%04x\n' % self
            self.game += '  CLC\n'
            self.game += '  ADC #%d\n' % operand
            self.game += '  STA $%04x\n' % self
        return self

    def __sub__(self, operand):
        if isinstance(operand, int):
            self.game += '  LDA $%04x\n' % self
            self.game += '  SEC\n'
            self.game += '  SBC #%d\n' % operand
            self.game += '  STA $%04x\n' % self
        return self

    def to_asm(self):
        return self.game


# TODO: very ugly, make it better


class Byte(object):

    def __init__(self, address=0):
        self.set_name(self.__class__.__name__, id(self))

    def set_name(self, prefix, key):
        self.target = '%s_%s' % (prefix, key)

    def __get__(self, instance, owner):
        if hasattr(instance, 'base_address'):
            base_address = getattr(instance, 'base_address')
            pos = getattr(instance, self.target)
            address = base_address + pos
            if hasattr(instance, 'sprite'):
                sprite = getattr(instance, 'sprite')
                addresses = []
                if self.target == '__PPUSprite_y':
                    for i in range(len(sprite.tile)):
                        addresses.append(address + i * 4)
                    width = sprite.width
                elif self.target == '__PPUSprite_x':
                    cols = len(sprite.tile) / sprite.width
                    lines = len(sprite.tile) / cols
                    swap = {}
                    for c in range(cols):
                        for l in range(lines):
                            i = (2 * c) + l
                            if l not in swap:
                                swap[l] = []
                            swap[l].append(address + i * 4)
                    for v in swap.values():
                        addresses += v
                    width = cols
                return NesAddressSet(addresses, width)
            else:
                return NesAddress(address)
        return NesAddress(getattr(instance, self.target))

    def __set__(self, instance, value):
        setattr(instance, self.target, value)


class PPUSprite(object):
    y = Byte()  # TODO: should be be Byte(0)
    tile = Byte()
    attrib = Byte()
    x = Byte()

    def __new__(cls, *args, **kwargs):
        for key, atr in cls.__dict__.items():
            if hasattr(atr, 'set_name'):
                atr.set_name('__' + cls.__name__, key)
        return super(PPUSprite, cls).__new__(cls, *args, **kwargs)

    def __init__(self, sprite, game):
        assert isinstance(sprite, (int, NesSprite))

        if isinstance(sprite, int):
            pos = sprite
        elif isinstance(sprite, NesSprite):
            pos = sprite.ppu_address
            self.sprite = sprite

        self.base_address = 0x0200 + (4 * pos)
        self.y = 0
        self.tile = 1
        self.attrib = 2
        self.x = 3
        self.game = game

    def flip_vertical(self):
        asm = (
            '  LDA $%04X\n'
            '  EOR #%d\n'
            '  STA $%04X\n'
        ) % (
            self.attrib,
            128,
            self.attrib
        )
        self.game += asm

    def flip_horizontal(self):
        asm = (
            '  LDA $%04X\n'
            '  EOR #%d\n'
            '  STA $%04X\n'
        ) % (
            self.attrib,
            64,
            self.attrib
        )
        self.game += asm


class Joypad():

    def __init__(self, player_num, game):
        assert player_num == 1 or player_num == 2
        self.num = player_num
        if player_num == 1:
            self.port = '$4016'
        else:
            self.port = '$4017'
        self.game = game
        self.actions = ['a', 'b', 'select', 'start',
                        'up', 'down', 'left', 'right']

    def __iter__(self):
        for action in self.actions:
            tag = action.capitalize()
            asm_code = (
                "JoyPad" + str(self.num) + tag + ":\n"
                "  LDA " + self.port + "\n"
                "  AND #%00000001\n"
                "  BEQ End" + tag + "\n"
            )
            index = 'joypad' + str(self.num) + '_' + action
            if index in self.game._asm_chunks:
                asm_code += self.game._asm_chunks[index]
            asm_code += "End" + tag + ":\n"
            yield asm_code

    def init(self):
        return ('StartInput:\n'
                '  LDA #$01\n'
                '  STA $4016\n'
                '  LDA #$00\n'
                '  STA $4016\n')

    @property
    def is_used(self):
        for status in self.game._asm_chunks:
            if match('^joypad[12]_(a|b|select|start|up|down|left|right)', status):
                return True
        return False

    def to_asm(self):
        if self.is_used:
            return '\n'.join(self)
        return ''


class Game(object):

    def __init__(self, optimized=True):
        self.ppu = PPU()

        self._asm_chunks = {}
        self.has_nmi = False
        self.state = 'prog'

        self._header = {'.inesprg': 1, '.ineschr': 1,
                        '.inesmap': 0, '.inesmir': 1}
        self._vars = OrderedDict()  # game nes vars
        self.bitpaks = {}
        self.labels = []

        # TODO: self.local_scope = {}
        # TODO: self.global_scope = {}

    def define(self, varname, value, size=1):
        if isinstance(value, NesRs):
            self._vars[varname] = value

    def assign(self, varname, value):
        if isinstance(value, NesType):
            value.instance_name = varname
        self._vars[varname] = value
        return value

    def minusAssign(self, varname, value):
        return
        self += (
            '  SEC\n'
            '  SBC #%02d\n') % value
        # self += '  STA %s\n' % value.instance_name
        return value

    def asmFunction(self, functionname):
        self.state = functionname

    # used just for bitpacks
    def call(self, bitpak_name, args=[]):
        if bitpak_name not in self.bitpaks:
            obj = getattr(pynes.bitbag, bitpak_name, None)
            bp = obj(self)
            self.bitpaks[bitpak_name] = bp
        print args
        returnValue = self.bitpaks[bitpak_name](*args)
        self.add_asm_chunk(self.bitpaks[bitpak_name].asm())
        return returnValue
        if (obj):
            try:
                # self.stack(bp(*args))
                bp(*args)
                self += bp.asm()
            except TypeError as ex:
                msg = ex.message.replace('__call__', bitpak_name, 1)
                raise(TypeError(msg))
        else:
            raise(NameError("name '%s' is not defined" % bitpak_name))

    def add_asm_chunk(self, asm_chunk):
        if asm_chunk and isinstance(asm_chunk, str):
            if self.state not in self._asm_chunks:
                self._asm_chunks[self.state] = asm_chunk
            else:
                self._asm_chunks[self.state] += asm_chunk

    def press_start(self):
        return self.to_asm()

    def __add__(self, other):
        if other and isinstance(other, str):
            if self.state not in self._asm_chunks:
                self._asm_chunks[self.state] = other
            else:
                self._asm_chunks[self.state] += other
        return self

    def get_param(self, name, size):
        while name in self._vars:
            name = name + '1'
        self._vars[name] = NesRs(size)
        return name

    def get_label_for(self, label):
        while label in self.labels:
            label = label + '1'
        self.labels.append(label)
        return label

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        # if self._state not in self._asm_chunks:
        #    self._asm_chunks[self.state] = ''
        if value == 'reset':
            self._state = value.upper()
            self += self.init()
        else:
            self._state = value

    def headers(self):
        return '\n'.join(['%s %d' % (h, self._header[h])
                          for h in ['.inesprg', '.ineschr', '.inesmap',
                                    '.inesmir']]) + '\n\n'

    def boot(self):
        asm_code = ("  .org $FFFA\n"
                    "  .dw %s\n"
                    "  .dw %s\n"
                    "  .dw 0\n"
                    ) % (
            'NMI' if self.has_nmi else '0',
            'RESET' if 'RESET' in self._asm_chunks else '0'
        )
        return asm_code

    def init(self):
        return (
            '  SEI          ; disable IRQs\n' +
            '  CLD          ; disable decimal mode\n' +
            '  LDX #$40\n' +
            '  STX $4017    ; disable APU frame IRQ\n' +
            '  LDX #$FF\n' +
            '  TXS          ; Set up stack\n' +
            '  INX          ; now X = 0\n' +
            '  STX $2000    ; disable NMI\n' +
            '  STX $2001    ; disable rendering\n' +
            '  STX $4010    ; disable DMC IRQs\n'
        )

    def rsset(self):
        asm_code = '\n'.join([
            '%s .rs %d' % (varname, var.size)
            for varname, var in self._vars.items()
            if isinstance(var, NesRs)
        ])
        if asm_code:
            return ("  .rsset $0000\n%s\n\n" % asm_code)
        return ""

    def infinity_loop(self):
        return (
            "InfiniteLoop:\n"
            "  JMP InfiniteLoop\n"
        )

    def prog(self):
        asm_code = ""
        if 'prog' in self._asm_chunks:
            asm_code += self._asm_chunks['prog']
        for bp in self.bitpaks:
            procedure = self.bitpaks[bp].procedure()
            if isinstance(procedure, str):
                asm_code += procedure + '\n'
        if 'RESET' in self._asm_chunks:
            asm_code += 'RESET:\n'
            asm_code += self._asm_chunks['RESET']
            asm_code += self.ppu.on_reset()
            asm_code += self.infinity_loop()
        if len(asm_code) > 0:
            return ("  .bank 0\n  .org $C000\n\n" + asm_code + '\n\n')
        return ""

    def bank1(self):
        asm_code = ''. join(
            ['%s:\n%s' % (varname, var.to_asm())
             for varname, var in self._vars.items()
             if isinstance(var, (NesArray, NesSprite, NesString)) and
                var.is_used])
        if asm_code:
            return ("  .bank 1\n  .org $E000\n\n" + asm_code + '\n\n')
        return "  .bank 1\n"

    def bank2(self):
        asm_code = '\n'.join(
            ['  .incbin "%s"' % var.filename
             for varname, var in self._vars.items()
             if isinstance(var, NesChrFile)
             ])

        if asm_code:
            return ("  .bank 2\n  .org $0000\n\n" + asm_code + '\n\n')
        return ""

    def nmi(self):
        joypad_1 = Joypad(1, self)
        # joypad_2 = Joypad(2, self)
        joypad_code = ''
        if joypad_1.is_used:
            joypad_code += joypad_1.init()
            joypad_code += joypad_1.to_asm()
        if len(joypad_code) > 0 or self.has_nmi:
            self.has_nmi = True  # TODO remove this, use ppu.enable_nmi insted
            nmi_code = (
                "NMI:\n"
                "  LDA #$00\n"
                "  STA $2003 ; Write Only: Sets the offset in sprite ram.\n"
                "  LDA #$02\n"
                "  STA $4014 ; Write Only; DMA\n"
            )
            nmi_code += self.ppu.on_nmi()
            nmi_code += joypad_code
            if 'NMI' in self._asm_chunks:
                nmi_code += self._asm_chunks['NMI']
            return nmi_code + "\n\n" + "  RTI   ;Return NMI\n"
        return ""

    def set_var(self, varname, value):
        self._vars[varname] = value

    def get_var(self, varname):
        return self._vars[varname]

    def to_asm(self):
        asm_code = (
            ';Generated by PyNES\n\n' +
            self.headers() +
            self.rsset() +
            self.prog() +
            self.nmi() +
            self.bank1() +
            self.boot() +
            self.bank2()
        )
        return asm_code

########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-

from PIL import Image, ImageDraw
from collections import Counter, OrderedDict

from pynes import write_bin_code
import sprite
import nametable

from sprite import SpriteSet

from pynes.tests import show_sprite

palette = [
    (0, 0, 0),
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255)
]

'''create a whole palette based on RGB colos'''


def create_palette():
    palette = []
    for p in sprite.palette:
        r = (p >> 16) & 0xff
        g = (p >> 8) & 0xff
        b = p & 0xff
        palette.append((r, g, b))
    return palette

'''Create a palette to be used in pil'''


def create_pil_palette():
    pps = create_palette()
    pps = [pps[15], pps[2], pps[32], pps[41]]  # TODO hack
    palette = []
    for p in pps:
        palette.extend(p)
    while len(palette) < (256 * 3):
        palette.extend(pps[3])
    return palette


def get_colors(image):
    assert image.size[0] % 8 == 0
    assert image.size[1] % 8 == 0
    colors = []
    pixels = image.load()
    for i in range(image.size[0]):
        for j in range(image.size[1]):
            if pixels[i, j] not in colors:
                colors.append(pixels[i, j])
    assert len(colors) <= 4, ("Image has {} colors, it can only have at most "
                              "4").format(len(colors))
    return colors

'''
Acquire a regular image to a CHR file,
That could be used to import a whole sprite table,
or also to create a tile set for a nametable
if optimize is False
'''


def acquire_chr(image, nes_palette=palette, optimize_repeated=False):
    assert image.size[0] % 8 == 0
    assert image.size[1] % 8 == 0
    colors = get_colors(image)
    assert len(colors) <= 4, ("Image has {} colors, it can only have at most "
                              "4").format(len(colors))
    default = (
        (0, 0, 0) in colors and
        (255, 0, 0) in colors and
        (0, 255, 0) in colors and
        (0, 0, 255) in colors
    )
    if default:
        nes_palette = palette
    else:
        nes_palette = colors

    sprite_keys = OrderedDict()

    sprs = []
    index = 0
    pixels = image.load()
    for y in range(image.size[1] / 8):
        for x in range(image.size[0] / 8):
            spr = fetch_chr(pixels, x, y, nes_palette)
            encoded = sprite.encode_sprite(spr)
            key = ''.join([chr(e) for e in encoded])
            if not optimize_repeated or key not in sprite_keys:
                sprite_keys[key] = index
                sprs.extend(encoded)
                index += 1
            else:
                pass
                # print index
    return sprs, sprite_keys

'''
fetch part of the image
'''


def fetch_chr(pixels, x, y, palette=palette):
    dx = x * 8
    dy = y * 8
    spr = []
    for j in range(dy, dy + 8):
        line = []
        for i in range(dx, dx + 8):
            if isinstance(pixels[i, j], int):
                color = pixels[i, j]
            else:
                color = palette.index(pixels[i, j])
            assert color >= 0 and color <= 3
            line.append(color)
        spr.append(line)
    return spr

''' function that wrap the acquisition(acquire_chr),
with the input and output file'''


def import_chr(img_file, chr_file):
    img = Image.open(img_file)
    sprs, indexes = acquire_chr(img)
    write_bin_code(sprs, chr_file)

'''
Transform a chr file into a image file
'''


def export_chr(chr_data, image_file, palette=palette, width=8):
    if isinstance(chr_data, str):
        sprs = SpriteSet(chr_data)
    else:
        sprs = SpriteSet(chr_data)
    spr_len = len(sprs)
    height = spr_len / width
    size = (width * 8, height * 8)

    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)

    for s_index in range(spr_len):
        spr = sprs.get(s_index)
        dx = s_index % width
        dy = s_index / width
        for y in range(8):
            for x in range(8):
                color = spr[y][x]
                draw.point((x + (8 * dx), y + (8 * dy)), palette[color])
    img.save(image_file, 'PNG')

'''
Thats the oposite of fetch_chr,
it draws a sprite into a PIL image.
'''


def draw_sprite(spr, dx, dy, draw, palette):
    for y in range(8):
        for x in range(8):
            color = spr[y][x]
            draw.point((x + (8 * dx), y + (8 * dy)), palette[color])

'''
Export a nametable to a image
using a chr_file
'''


def export_nametable(nametable_data, chr_data, png_file, palette=palette):
    if isinstance(nametable_data, str):
        nts = nametable.load_nametable(nametable_data)
    else:
        nts = nametable_data

    if isinstance(chr_data, str):
        sprs = SpriteSet(chr_data)
    else:
        sprs = SpriteSet(chr_data)

    nt = nametable.get_nametable(0, nts)
    size = (256, 256)
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)

    nt_index = 0

    # num_nt = nametable.length(nts)

    if len(sprs) == 512:
        start = 256
    else:
        start = 0

    for y in range(32):
        for x in range(32):
            dx = nt_index / 32
            dy = nt_index % 32
            spr_index = nt[y][x] + start  # TODO something strange with X and Y
            spr = sprs.get(spr_index)
            draw_sprite(spr, dx, dy, draw, palette)
            nt_index += 1

    img.save(png_file, 'PNG')

'''
The function call is read, 'cause the processe is like reading
a text with 64 cols x 64 lines on witch, caracter is a sprite
'''


def read_nametable(image, sprs, palette=palette):
    pixels = image.load()
    colors = get_colors(image)

    default = (
        (0, 0, 0) in colors and
        (255, 0, 0) in colors and
        (0, 255, 0) in colors and
        (0, 0, 255) in colors
    )
    if default:
        nes_palette = palette
    else:
        nes_palette = colors

    nametable = []

    # TODO huge stealing here
    if sprite.length(sprs) == 512:
        start = 256
    else:
        start = 0

    if isinstance(sprs, tuple):
        sprs = sprs[0]

    for y in range(image.size[0] / 8):
        for x in range(image.size[1] / 8):
            spr = fetch_chr(pixels, y, x, nes_palette)
            index = sprite.find_sprite(sprs, spr, start)
            if index != -1:
                nametable.append(index)
            else:
                show_sprite(spr)
                raise Exception('Sprite not found')

            # TODO:
            # encoded = sprite.encode_sprite(spr)
            # key = ''.join([chr(e) for e in encoded])
            # if key in sprs:
            #    if key > 256:
            #        show_sprite(spr)
            #        pass
            # print sprs[key]
            # print sprs[key]
            #    nametable.append(sprs[key])
            # else:
            #   show_sprite(spr)
            #   print x
            #   print y
            #   print '===' + key + '===='
            #   raise Exception('Sprite not found')
    return nametable


def acquire_nametable(image_file, palette=palette):
    image = Image.open(image_file)
    sprs = acquire_chr(image, optimize_repeated=True)
    nametable = read_nametable(image, sprs, palette)
    return nametable, sprs


def import_nametable(png_file, chr_file, nametable_file, palette=palette):
    image = Image.open(png_file)
    sprs = sprite.load_sprites(chr_file)
    nametable = read_nametable(image, sprs, palette)
    write_bin_code(nametable, nametable_file)


def convert_to_nametable(image_file):
    colors = []
    original = Image.open(image_file)
    original = original.convert('RGB')

    template = Image.new('P', original.size)
    template.putpalette(create_pil_palette())

    converted = original.quantize(palette=template, colors=4)
    pixels = converted.load()

    assert converted.size[0] == 256
    assert converted.size[1] == 256

    cnt = Counter()
    for i in range(converted.size[0]):
        for j in range(converted.size[1]):
            if pixels[i, j] not in colors:
                colors.append(pixels[i, j])
            cnt[pixels[i, j]] += 1
        break

    return
    # cnt.most_common(4)

    # TODO: implement convert_chr and convert_nametable or delete these lines
    # sprs, indexes = convert_chr(converted, optimize_repeated=True)
    # nametable = convert_nametable(converted, indexes)

    # write_bin_code(sprs, 'sprite.chr')
    # write_bin_code(nametable, 'nametable.bin')

    # return nametable, sprs

########NEW FILE########
__FILENAME__ = nametable
# -*- coding: utf-8 -*-


def load_nametable(nt_file):
    f = open(nt_file)
    nt_content = f.read()
    nt_bin = []
    for nt in nt_content:
        nt_bin.append(ord(nt))
    return nt_bin


def get_nametable(index, nt):
    tile_index = index * 1024
    nametable = []
    for y in range(32):
        line = []
        for x in range(32):
            # dx = tile_index / 32
            # dy = tile_index % 32
            spr_index = nt[tile_index]
            line.append(spr_index)
            tile_index += 1
        nametable.append(line)
    return nametable


def length(nt):
    return len(nt) / 1024

########NEW FILE########
__FILENAME__ = nes_types
# -*- coding: utf-8 -*-

from ast import Num, List


class NesType:

    def __init__(self, size=1):
        self.instance_name = None
        self.is_used = False  # define if a var is used
        self.is_attrib = False  # define is assigned more than once
        self.size = size
        self.lineno = 0


class NesRs(NesType):

    def __init__(self, size=1):
        NesType.__init__(self, size)


class NesSprite(NesType):

    def __init__(self, x, y, tile, attrib, width=2):
        NesType.__init__(self)
        self.is_used = True
        self.x = x
        self.y = y
        self.tile = tile
        self.attrib = attrib
        self.width = width

    def __len__(self):
        print self.tile
        print dir(self.tile)
        print self.tile
        print self.tile.__class__
        print isinstance(self.tile, list)
        if isinstance(self.tile, List):
            return len(self.tile)
        return 1

    def to_asm(self):
        if isinstance(self.tile, int):
            return (
                '  .db $%02X, $%02X, $%02X, $%02X' %
                (
                    self.y,
                    self.tile,
                    self.attrib,
                    self.x
                ))
        else:
            asmcode = ''
            x = 0
            # TODO: assert list mod width == 0
            for t in self.tile:
                i = x % self.width
                j = x / self.width
                asmcode += ('  .db $%02X, $%02X, $%02X, $%02X\n' %
                            (
                                self.y + (j * 8),
                                t,
                                self.attrib,
                                self.x + (i * 8)
                            ))
                x += 1
            return asmcode


class NesArray(NesType, list, List):

    def __init__(self, elts):
        NesType.__init__(self)
        List.__init__(self, elts=elts)
        lst = [l.n if isinstance(l, Num) else l for l in elts]
        list.__init__(self, lst)
        self.is_used = True
        self.locked = False

    def to_asm(self):
        self.locked = True
        hexes = ["$%02X" % v for v in self]
        asm = ''
        length = (len(hexes) / 16)
        if len(hexes) % 16:
            length += 1
        for i in range(length):
            asm += '  .db ' + ','.join(hexes[i * 16:i * 16 + 16]) + '\n'
        if len(asm) > 0:
            return asm
        return False


class NesInt(int, Num, NesType):

    def __init__(self, number):
        int.__init__(self, number)
        Num.__init__(self, n=number)
        NesType.__init__(self)


class NesString(str, NesType):

    def __init__(self, string):
        str.__init__(self, string)
        NesType.__init__(self)
        self.locked = False

    def to_asm(self):
        s = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ "
        start = 0
        bytes = [(s.index(c) + start) for c in self.upper()]
        bytes.append(0x25)  # TODO: EndString
        hexes = ["$%02X" % v for v in bytes]
        asm = ''
        length = (len(hexes) / 16)
        if len(hexes) % 16:
            length += 1
        for i in range(length):
            asm += '  .db ' + ','.join(hexes[i * 16:i * 16 + 16]) + '\n'
        if len(asm) > 0:
            return asm
        return False


class NesChrFile(NesType):

    def __init__(self, filename):
        self.filename = filename

########NEW FILE########
__FILENAME__ = sprite
# -*- coding: utf-8 -*-

from collections import OrderedDict

palette = [
    0x788084, 0x0000fc, 0x0000c4, 0x4028c4,
    0x94008c, 0xac0028, 0xac1000, 0x8c1800,
    0x503000, 0x007800, 0x006800, 0x005800,
    0x004058, 0x000000, 0x000000, 0x000008,

    0xbcc0c4, 0x0078fc, 0x0088fc, 0x6848fc,
    0xdc00d4, 0xe40060, 0xfc3800, 0xe46918,
    0xac8000, 0x00b800, 0x00a800, 0x00a848,
    0x008894, 0x2c2c2c, 0x000000, 0x000000,

    0xfcf8fc, 0x38c0fc, 0x6888fc, 0x9c78fc,
    0xfc78fc, 0xfc589c, 0xfc7858, 0xfca048,
    0xfcb800, 0xbcf818, 0x58d858, 0x58f89c,
    0x00e8e4, 0x606060, 0x000000, 0x000000,

    0xfcf8fc, 0xa4e8fc, 0xbcb8fc, 0xdcb8fc,
    0xfcb8fc, 0xf4c0e0, 0xf4d0b4, 0xfce0b4,
    0xfcd884, 0xdcf878, 0xb8f878, 0xb0f0d8,
    0x00f8fc, 0xc8c0c0, 0x000000, 0x000000
]


def load_sprites(src):
    f = open(src, 'rb')
    content = f.read()
    f.close()
    assert len(content) % 16 == 0
    bin = [ord(c) for c in content]
    return bin


def load_indexed_sprites(src):
    f = open(src, 'rb')
    content = f.read()
    assert len(content) % 16 == 0
    bin = [ord(c) for c in content]
    assert len(bin) % 16 == 0
    indexes = OrderedDict()
    for i in range(len(content) / 16):
        indexes[content[i * 16: i * 16 + 16]] = i
    return bin, indexes


def decode_sprite(channelA, channelB):
    s = []
    y = 0
    for y in range(0, 8):
        a = channelA[y]
        b = channelB[y]
        line = []
        for x in range(0, 8):
            bit = pow(2, 7 - x)
            pixel = -1
            if (not (a & bit) and not (b & bit)):
                pixel = 0
            elif ((a & bit) and not (b & bit)):
                pixel = 1
            elif (not (a & bit) and (b & bit)):
                pixel = 2
            elif ((a & bit) and (b & bit)):
                pixel = 3
            line.append(pixel)
        s.append(line)
    return s


def get_sprite(index, sprites):
    assert len(sprites) > index
    iA = index * 16
    iB = iA + 8
    iC = iB + 8
    channelA = sprites[iA:iB]
    channelB = sprites[iB:iC]
    return decode_sprite(channelA, channelB)


def encode_sprite(sprite):
    channelA = []
    channelB = []
    for y in range(8):
        a = 0
        b = 0
        for x in range(8):
            pixel = sprite[y][x]
            bit = pow(2, 7 - x)
            if pixel == 1:
                a = a | bit
            elif pixel == 2:
                b = b | bit
            elif pixel == 3:
                a = a | bit
                b = b | bit
        channelA.append(a)
        channelB.append(b)
    return channelA + channelB


def put_sprite(index, sprites, spr):
    start = index * 16
    encoded = encode_sprite(spr)
    j = 0
    for i in range(start, start + 16):
        sprites[i] = encoded[j]
        j += 1
    return sprites


def length(sprites):
    return len(sprites) / 16


def find_sprite(sprites, spr, start=0):
    for index in range(start, length(sprites)):
        if spr == get_sprite(index, sprites):
            return index - start
    return -1


class SpriteSet():

    def __init__(self, sprite_data=None):
        if isinstance(sprite_data, str):
            self.sprs, self.indexes = load_indexed_sprites(sprite_data)
        else:
            (self.sprs, self.indexes) = sprite_data

    def __len__(self):
        return length(self.sprs)

    def get(self, index):
        return get_sprite(index, self.sprs)

    def put(self, index, spr):
        return put_sprite(index, spr, self.sprs)

    def has_sprite(self, spr):
        if isinstance(spr, list):
            spr = encode_sprite(spr)
            spr = ''.join(chr(c) for c in spr)
        if spr in self.indexes:
            return self.indexes[spr]
        return False

########NEW FILE########
__FILENAME__ = adc_test
# -*- coding: utf-8 -*-
'''
ADC, Add with Carry Test

This is an arithmetic instruction of the 6502.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class AdcTest(unittest.TestCase):

    def test_adc_imm(self):
        '''
        Test the arithmetic operation ADC between decimal 16
        and the content of the accumulator.
        '''
        tokens = list(lexical('ADC #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x69, 0x10])

    def test_adc_imm_with_decimal(self):
        '''
        Test the arithmetic operation ADC between decimal 10
        and the content of the accumulator.
        '''
        tokens = list(lexical('ADC #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x69, 0x0A])

    def test_adc_imm_with_binary(self):
        '''
        Test the arithmetic operation ADC between binary %00000100
        (Decimal 4) and the content of the accumulator.
        '''
        tokens = list(lexical('ADC #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x69, 0x04])

    def test_adc_zp(self):
        '''
        Test the arithmetic operation ADC between the content of
        the accumulator and the content of the zero page address.
        '''
        tokens = list(lexical('ADC $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x65, 0x00])

    def test_adc_zpx(self):
        '''
        Test the arithmetic operation ADC between the content of the
        accumulator and the content of the zero page with address
        calculated from $10 adding content of X.
        '''
        tokens = list(lexical('ADC $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x75, 0x10])

    def test_adc_abs(self):
        '''
        Test the arithmetic operation ADC between the content of
        the accumulator and the content located at address $1234.
        '''
        tokens = list(lexical('ADC $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x6d, 0x34, 0x12])

    def test_adc_absx(self):
        '''
        Test the arithmetic operation ADC between the content of the
        accumulator and the content located at address $1234
        adding the content of X.
        '''
        tokens = list(lexical('ADC $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x7d, 0x34, 0x12])

    def test_adc_absy(self):
        '''
        Test the arithmetic operation ADC between the content of the
        accumulator and the content located at address $1234
        adding the content of Y.
        '''
        tokens = list(lexical('ADC $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x79, 0x34, 0x12])

    def test_adc_indx(self):
        '''
        Test the arithmetic ADC operation between the content of the
        accumulator and the content located at the address
        obtained from the address calculated from the value
        stored in the address $20 adding the content of Y.
        '''
        tokens = list(lexical('ADC ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x61, 0x20])

    def test_adc_indy(self):
        '''
        Test arithmetic operation ADC between the content of the
        accumulator and the content located at the address
        obtained from the address calculated from the value
        stored in the address $20 adding the content of Y.
        '''
        tokens = list(lexical('ADC ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x71, 0x20])

########NEW FILE########
__FILENAME__ = analyzer_test
# -*- coding: utf-8 -*-

from unittest import TestCase
from types import GeneratorType
from pynes.analyzer import analyse, UnknownToken

asm_test_tokens = [
    dict(type='T_FAKE_INSTRUCTION', regex='^(ONE|TEST)', store=True),
    dict(type='T_SOME_SYMBOL', regex='^([*+-])', store=True),
    dict(type='T_ENDLINE', regex=r'^\n', store=True),
    dict(type='T_WHITESPACE', regex=r'^[ \t\r]+', store=False),
    dict(type='T_COMMENT', regex=r'^;[^\n]*', store=False)
]

class AnalyzerTest(TestCase):

    def test_raise_unknown_token(self):
        tokens = analyse('ONE *unknown', asm_test_tokens)
        self.assertIsInstance(tokens, GeneratorType)
        self.assertEquals('T_FAKE_INSTRUCTION', next(tokens)['type'])
        self.assertEquals('T_SOME_SYMBOL', next(tokens)['type'])
        with self.assertRaises(UnknownToken):
            next(tokens) # unknown

    def test_unknown_token_message(self):
        tokens = analyse(';test\n  @--Case \n;TUTEM acronym test',
                         asm_test_tokens)
        self.assertIsInstance(tokens, GeneratorType)
        try:
            list(tokens)
        except UnknownToken as ut:
            self.assertEquals(2, ut.line)
            self.assertEquals(3, ut.column)
            self.assertEquals('  @--Case \n', ut.line_code) # W/ trail wspaces
            self.assertEquals('Unknown token @(2,3):   @--Case', ut.message)
        else:
            self.fail("UnkownToken not raised")

    def test_empty_token_types_list(self):
        tokens = analyse('something', [])
        with self.assertRaises(UnknownToken):
            next(tokens) # unknown

    def test_empty_inputs(self):
        tokens = analyse('', [])
        with self.assertRaises(StopIteration):
            next(tokens) # unknown

########NEW FILE########
__FILENAME__ = and_test
# -*- coding: utf-8 -*-
'''
AND, Logical AND with Accumulator Test

This is a test for the logical instruction AND of
the 6502. In the 6502 the logical AND could be
performed against the content of the accumulator or
a content at a specific location.
'''
import unittest
from pynes.compiler import lexical, syntax, semantic


class AndTest(unittest.TestCase):

    def test_and_imm(self):
        '''
        Test the logical operation AND between $10(Decimal 16)
        and the content of the Accumulator
        '''
        tokens = list(lexical('AND #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x29, 0x10])

    def test_and_imm_with_decimal(self):
        '''
        Test the logical operation AND between #10(Decimal 10)
        and the content of the Accumulator
        '''
        tokens = list(lexical('AND #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x29, 0x0a])

    def test_and_imm_with_binary(self):
        '''
        Test the logical operation AND between #%00000100 (Decimal 4)
        and the content of the Accumulator
        '''
        tokens = list(lexical('AND #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x29, 0x04])

    def test_and_zp(self):
        '''
        Test the logical operation AND between the content of
        accumulator and the content of zero page address $00
        '''
        tokens = list(lexical('AND $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x25, 0x00])

    def test_and_zpx(self):
        '''
        Test the logical operation AND between the content of
        accumulator and the content located at zero page with
        address calculated from $10 adding content of X
        '''
        tokens = list(lexical('AND $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x35, 0x10])

    def test_and_abs(self):
        tokens = list(lexical('AND $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2d, 0x34, 0x12])

    def test_and_absx(self):
        tokens = list(lexical('AND $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x3d, 0x34, 0x12])

    def test_and_absy(self):
        tokens = list(lexical('AND $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x39, 0x34, 0x12])

    def test_and_indx(self):
        tokens = list(lexical('AND ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x21, 0x20])

    def test_and_indy(self):
        tokens = list(lexical('AND ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x31, 0x20])

########NEW FILE########
__FILENAME__ = asl_test
# -*- coding: utf-8 -*-
'''
ASL, Arithmetic Shift Left

This is a test for the bit manipulation instruction ASL.
'''
import unittest
from pynes.compiler import lexical, syntax, semantic


class AslTest(unittest.TestCase):

    # TODO see the accumulator type instruction, ASL A
    def test_asl_imm(self):
        tokens = list(lexical('ASL #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x0a, 0x10])

    def test_asl_imm_with_decimal(self):
        tokens = list(lexical('ASL #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x0a, 0x0a])

    def test_asl_imm_with_binary(self):
        tokens = list(lexical('ASL #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x0a, 0x04])

    def test_asl_zp(self):
        tokens = list(lexical('ASL $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x06, 0x00])

    def test_asl_zpx(self):
        tokens = list(lexical('ASL $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x16, 0x10])

    def test_asl_abs(self):
        tokens = list(lexical('ASL $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x0e, 0x34, 0x12])

    def test_asl_absx(self):
        tokens = list(lexical('ASL $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x1e, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = background_test
# -*- coding: utf-8 -*-
from pynes.tests import HexTestCase
from pynes.compiler import lexical, syntax, semantic
from pynes.cartridge import Cartridge


class BackgroundTest(HexTestCase):

    def __init__(self, testname):
        HexTestCase.__init__(self, testname)

    def assertAsmResults(self, source_file, bin_file):
        path = 'fixtures/nerdynights/background/'
        f = open(path + source_file)
        code = f.read()
        f.close()
        tokens = lexical(code)
        ast = syntax(tokens)

        cart = Cartridge()
        cart.path = 'fixtures/nerdynights/background/'

        opcodes = semantic(ast, True, cart=cart)

        self.assertIsNotNone(opcodes)
        bin = ''.join([chr(opcode) for opcode in opcodes])
        f = open(path + bin_file, 'rb')
        content = f.read()
        f.close()
        self.assertHexEquals(content, bin)

    def test_asm_compiler_background(self):
        self.assertAsmResults('background.asm', 'background.nes')

    def test_asm_compiler_background3(self):
        self.assertAsmResults('background3.asm', 'background3.nes')

########NEW FILE########
__FILENAME__ = bcc_test
# -*- coding: utf-8 -*-
'''
BCC, Branch on Carry Clear Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if C == 0.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BccTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bcc_rel(self):
        tokens = list(lexical('BCC $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x90, 0x0e])

########NEW FILE########
__FILENAME__ = bcs_test
# -*- coding: utf-8 -*-
'''
BCS, Branch on Carry Set Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if C == 0.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BcsTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bcs_rel(self):
        tokens = list(lexical('BCS $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb0, 0x0e])

########NEW FILE########
__FILENAME__ = beq_test
# -*- coding: utf-8 -*-
'''
BEQ, Branch on Result Zero Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if Z == 1.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BneTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_beq_rel(self):
        tokens = list(lexical('BEQ $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf0, 0x0e])

########NEW FILE########
__FILENAME__ = bit_test
# -*- coding: utf-8 -*-

import unittest
from pynes.compiler import lexical, syntax, semantic


class BitTest(unittest.TestCase):

    def test_bit_zp(self):
        tokens = list(lexical('BIT $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x24, 0x00])

    def test_bit_abs(self):
        tokens = list(lexical('BIT $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2c, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = bmi_test
# -*- coding: utf-8 -*-

'''
BMI, Branch on Result Minus Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if N == 1.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BmiTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bmi_rel(self):
        tokens = list(lexical('BMI $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x30, 0x0e])

########NEW FILE########
__FILENAME__ = bne_test
# -*- coding: utf-8 -*-
'''
BNE, Branch on Result not Zero Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if Z == 0.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BneTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bne_rel(self):
        tokens = list(lexical('BNE $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd0, 0x0e])

########NEW FILE########
__FILENAME__ = bpl_test
# -*- coding: utf-8 -*-

'''
BPL, Branch on Result Plus Test

This is a test for the branch instruction BPL of
the 6502. This instruction performs the branch
if N == 0.

'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BplTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bpl_rel(self):
        tokens = list(lexical('BPL $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x10, 0x0e])

########NEW FILE########
__FILENAME__ = bvc_test
# -*- coding: utf-8 -*-
'''
BVC, Branch on Overflow Clear Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if V == 0.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BvcTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bvc_rel(self):
        tokens = list(lexical('BVC $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x50, 0x0e])

########NEW FILE########
__FILENAME__ = bvs_test
# -*- coding: utf-8 -*-
'''
BVS, Branch on Overflow Set Test

This is a test for the branch instruction BMI of
the 6502. This instruction performs the branch
if V == 1.
'''

import unittest
from pynes.compiler import lexical, syntax, semantic


class BvsTest(unittest.TestCase):

    '''This is an relative instruction, so it works quite different
    from others. The instruction uses an offset witch can range from
    -128 to +127. The offset is added to the program counter.'''

    def test_bvs_rel(self):
        tokens = list(lexical('BVS $10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_RELATIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x70, 0x0e])

########NEW FILE########
__FILENAME__ = cartridge_test
import unittest

from pynes.cartridge import Cartridge


class CartridgeTest(unittest.TestCase):

    def setUp(self):
        self.cart = Cartridge()

    def tearDown(self):
        self.cart = None

    def test_inesprg_1(self):
        self.cart.set_iNES_prg(1)
        self.assertEquals(1, self.cart.inespgr)

    def test_inesprg_2(self):
        self.cart.set_iNES_prg(2)
        self.assertEquals(2, self.cart.inespgr)

    def test_ineschr(self):
        self.cart.set_iNES_chr(1)
        self.assertEquals(1, self.cart.ineschr)

    def test_inesmap(self):
        self.cart.set_iNES_map(1)
        self.assertEquals(1, self.cart.inesmap)

    def test_inesmir(self):
        self.cart.set_iNES_mir(1)
        self.assertEquals(1, self.cart.inesmir)

    def test_bank_1(self):
        self.cart.set_bank_id(0)
        self.assertEquals(1, len(self.cart.banks))

    def test_bank_2(self):
        self.cart.set_bank_id(0)
        self.cart.set_bank_id(1)
        self.assertEquals(2, len(self.cart.banks))

    def test_org_1(self):
        self.cart.set_bank_id(0)
        self.cart.set_org(0xc000)
        self.assertEquals(0xc000, self.cart.banks[0]['start'])

    def test_append_code(self):
        code = [0x4e, 0x45, 0x53, 0x1a]
        self.cart.append_code(code)
        self.assertEquals(4, self.cart.pc)
        self.assertEquals(code, self.cart.get_code())

    def test_using_org_to_jump(self):
        self.cart.set_bank_id(0)
        self.cart.set_org(0xc000)
        code = [0x4e, 0x45, 0x53, 0x1a]
        self.cart.append_code(code)
        self.cart.set_org(0xc000 + 8)
        self.cart.append_code(code)
        self.assertEquals(
            [0x4e, 0x45, 0x53, 0x1a, 0xff, 0xff,
                0xff, 0xff, 0x4e, 0x45, 0x53, 0x1a],
            self.cart.get_code()
        )

########NEW FILE########
__FILENAME__ = clc_test
# -*- coding: utf-8 -*-
'''
CLC, Clear Carry

This is a test for the clear carry instruction
'''
import unittest
from pynes.compiler import lexical, syntax, semantic


class ClcTest(unittest.TestCase):

    def test_clc_sngl(self):
        tokens = list(lexical('CLC'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x18])

########NEW FILE########
__FILENAME__ = cld_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class CldTest(unittest.TestCase):

    def test_cld_sngl(self):
        tokens = list(lexical('CLD'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd8])

########NEW FILE########
__FILENAME__ = cli_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class CliTest(unittest.TestCase):

    def test_cli_sngl(self):
        tokens = list(lexical('CLI'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x58])

########NEW FILE########
__FILENAME__ = clv_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class ClvTest(unittest.TestCase):

    def test_clv_sngl(self):
        tokens = list(lexical('CLV'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb8])

########NEW FILE########
__FILENAME__ = cmp_test
# -*- coding: utf-8 -*-
'''
CMP, Compare with Accumulator Test
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class CpmTest(unittest.TestCase):

    def test_cmp_imm(self):
        tokens = list(lexical('CMP #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc9, 0x10])

    def test_cmp_imm_with_decimal(self):
        tokens = list(lexical('CMP #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc9, 0x0a])

    def test_cmp_imm_with_binary(self):
        tokens = list(lexical('CMP #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc9, 0x04])

    def test_cmp_zp(self):
        tokens = list(lexical('CMP $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc5, 0x00])

    def test_cmp_zpx(self):
        tokens = list(lexical('CMP $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd5, 0x10])

    def test_cmp_abs(self):
        tokens = list(lexical('CMP $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xcd, 0x34, 0x12])

    def test_cmp_absx(self):
        tokens = list(lexical('CMP $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xdd, 0x34, 0x12])

    def test_cmp_absy(self):
        tokens = list(lexical('CMP $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd9, 0x34, 0x12])

    def test_cmp_indx(self):
        tokens = list(lexical('CMP ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc1, 0x20])

    def test_cmp_indy(self):
        tokens = list(lexical('CMP ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd1, 0x20])

########NEW FILE########
__FILENAME__ = code_line_generator_test
# -*- coding: utf-8 -*-

from unittest import TestCase
from pynes.analyzer import code_line_generator
from types import GeneratorType
from tempfile import NamedTemporaryFile

class CodeLineGeneratorTest(TestCase):

    def test_unicode(self):
        code = u'; Something\nCPY #$11'
        gen = code_line_generator(code)
        self.assertIsInstance(gen, GeneratorType)
        self.assertEqual(u'; Something\n', next(gen))
        self.assertEqual(u'CPY #$11', next(gen))
        with self.assertRaises(StopIteration):
            next(gen)

    def test_byte_string(self):
        code = 'CPX #$0A\n; Another\n; idea\n'
        gen = code_line_generator(code)
        self.assertIsInstance(gen, GeneratorType)
        self.assertEqual('CPX #$0A\n', next(gen))
        self.assertEqual('; Another\n', next(gen))
        self.assertEqual('; idea\n', next(gen))
        with self.assertRaises(StopIteration):
            next(gen)

    def test_real_file(self):
        with NamedTemporaryFile(mode="r+") as f:
            f.write("; this\nADC #$0A\n;test\n\n")
            f.seek(0)
            gen = code_line_generator(f)
            self.assertEqual('; this\n', next(gen))
            self.assertEqual('ADC #$0A\n', next(gen))
            self.assertEqual(';test\n', next(gen))
            self.assertEqual('\n', next(gen))
            with self.assertRaises(StopIteration):
                next(gen)

########NEW FILE########
__FILENAME__ = commandline_test
# -*- coding: utf-8 -*-
from pynes import main
from pynes.tests import FileTestCase
from mock import patch


class CommandLineTest(FileTestCase):

    @patch('pynes.compiler.compile_file')
    def test_asm(self, compiler):
        main("pynes asm fixtures/movingsprite/movingsprite.asm".split())
        compiler.assert_called_once_with(
            'fixtures/movingsprite/movingsprite.asm',
            output=None, path=None)

    @patch('pynes.compiler.compile_file')
    def test_asm_with_output(self, compiler):
        main("pynes asm fixtures/movingsprite/movingsprite.asm --output"
             " /tmp/movingsprite.nes".split())
        compiler.assert_called_once_with(
            'fixtures/movingsprite/movingsprite.asm',
            output='/tmp/movingsprite.nes', path=None)

    @patch('pynes.compiler.compile_file')
    def test_asm_with_path(self, compiler):
        main("pynes asm fixtures/movingsprite/movingsprite.asm --path "
             "fixtures/movingsprite".split())
        compiler.assert_called_once_with(
            'fixtures/movingsprite/movingsprite.asm',
            output=None, path='fixtures/movingsprite')

    @patch('pynes.composer.compose_file')
    def test_py(self, composer):
        main("pynes py pynes/examples/movingsprite.py".split())
        composer.assert_called_once_with(
            'pynes/examples/movingsprite.py',
            output=None, asm=False, path=None)

    @patch('pynes.composer.compose_file')
    def test_py_with_asm(self, composer):
        main("pynes py pynes/examples/movingsprite.py --asm".split())
        composer.assert_called_once_with(
            'pynes/examples/movingsprite.py',
            output=None, asm=True, path=None)

    @patch('pynes.composer.compose_file')
    def test_py_with_output(self, composer):
        main("pynes py pynes/examples/movingsprite.py --output "
             "output.nes".split())
        composer.assert_called_once_with(
            'pynes/examples/movingsprite.py',
            output='output.nes', asm=False, path=None)

    @patch('pynes.composer.compose_file')
    def test_py_with_path(self, composer):
        main("pynes py pynes/examples/movingsprite.py --path "
             "fixtures/movingsprite".split())
        composer.assert_called_once_with(
            'pynes/examples/movingsprite.py',
            output=None, path='fixtures/movingsprite', asm=False)

    def test_py_real_build_movingsprite(self):
        args = (
            "pynes py pynes/examples/movingsprite.py "
            "--path fixtures/movingsprite "
            "--output pynes/examples/movingsprite.nes"
        ).split()
        main(args)

    def test_py_real_build_mario(self):
        args = (
            "pynes py pynes/examples/mario.py "
            "--path fixtures/nerdynights/scrolling "
            "--output pynes/examples/mario.nes"
        ).split()
        main(args)

    def test_py_real_build_helloworld(self):
        args = (
            "pynes py pynes/examples/helloworld.py "
            "--path fixtures/nerdynights/scrolling "
            "--output pynes/examples/helloworld.nes"
        ).split()
        main(args)

    def test_py_real_build_slides(self):
        args = (
            "pynes py pynes/examples/slides.py "
            "--path fixtures/nerdynights/scrolling "
            "--output pynes/examples/slides.nes --asm"
        ).split()
        main(args)

########NEW FILE########
__FILENAME__ = compiler_test
# -*- coding: utf-8 -*-

import unittest
from types import GeneratorType
from pynes.compiler import (lexical, syntax,
                            t_zeropage, t_address, t_separator, get_labels)


class CompilerTest(unittest.TestCase):

    def setUp(self):
        self.zeropage = dict(
            type='T_ADDRESS',
            value='$00'
        )
        self.address10 = dict(
            type='T_ADDRESS',
            value='$1234'
        )
        self.separator = dict(
            type='T_SEPARATOR',
            value=','
        )

    def test_t_zeropage(self):
        self.assertTrue(t_zeropage([self.zeropage], 0))

    def test_t_address(self):
        self.assertTrue(t_address([self.address10], 0))

    def test_t_separator(self):
        self.assertTrue(t_separator([self.separator], 0))

    def test_compile_more_than_on_instruction(self):
        code = '''
            SEC         ;clear the carry
            LDA $20     ;get the low byte of the first number
            '''
        tokens = list(lexical(code))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_ENDLINE', tokens[0]['type'])
        self.assertEquals('T_INSTRUCTION', tokens[1]['type'])
        self.assertEquals('T_ENDLINE', tokens[2]['type'])
        self.assertEquals('T_INSTRUCTION', tokens[3]['type'])
        self.assertEquals('T_ADDRESS', tokens[4]['type'])
        self.assertEquals('T_ENDLINE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(2, len(ast))

    def test_compile_decimal(self):
        code = '''
            LDA #128
            STA $0203
        '''
        tokens = list(lexical(code))
        self.assertEquals(7, len(tokens))
        self.assertEquals('T_ENDLINE', tokens[0]['type'])
        self.assertEquals('T_INSTRUCTION', tokens[1]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[2]['type'])
        self.assertEquals('T_ENDLINE', tokens[3]['type'])
        self.assertEquals('T_INSTRUCTION', tokens[4]['type'])
        self.assertEquals('T_ADDRESS', tokens[5]['type'])
        self.assertEquals('T_ENDLINE', tokens[6]['type'])

    def test_compile_list(self):
        code = '''
            palette:
              .db $0F,$01,$02,$03,$04,$05,$06,$07,$08,$09,$0A,$0B,$0C,$0D,$0E,$0F
              .db $0F,$30,$31,$32,$33,$35,$36,$37,$38,$39,$3A,$3B,$3C,$3D,$3E,$0F
        '''
        tokens = list(lexical(code))
        ast = syntax(tokens)
        self.assertEquals(2, len(ast))

        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        self.assertEquals('.db', ast[0]['children'][0]['value'])
        self.assertEquals(32, len(ast[0]['children']))
        palette1 = [0x0f, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
                    0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f]
        for i in range(len(palette1)):
            h = '$%02X' % palette1[i]
            self.assertEquals(h, ast[0]['children'][i * 2 + 1]['value'])
            self.assertEquals('S_DIRECTIVE', ast[1]['type'])

        self.assertEquals('S_DIRECTIVE', ast[1]['type'])
        self.assertEquals('.db', ast[0]['children'][0]['value'])
        self.assertEquals(32, len(ast[1]['children']))
        palette2 = [0x0f, 0x30, 0x31, 0x32, 0x33, 0x35, 0x36, 0x37, 0x38, 0x39,
                    0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x0f]
        for i in range(len(palette2)):
            h = '$%02X' % palette2[i]
            self.assertEquals(h, ast[1]['children'][i * 2 + 1]['value'])

    def test_instructions_with_labels(self):
        code = '''
              .org $C000

            WAITVBLANK:
              BIT $2002
              BPL WAITVBLANK
              RTS'''

        tokens = list(lexical(code))
        ast = syntax(tokens)
        self.assertEquals(4, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        self.assertEquals('S_ABSOLUTE', ast[1]['type'])
        self.assertEquals(['WAITVBLANK'], ast[1]['labels'])

        labels = get_labels(ast)
        expected = {'WAITVBLANK': 0xc000}

        self.assertEquals(expected, labels)

    def test_several_lists_with_labels(self):
        code = '''
            .org $E000

            palette:
              .db $0F,$01,$02,$03,$04,$05,$06,$07,$08,$09,$0A,$0B,$0C,$0D,$0E,$0F
              .db $0F,$30,$31,$32,$33,$35,$36,$37,$38,$39,$3A,$3B,$3C,$3D,$3E,$0F

            sprites:
              .db $80, $00, $03, $80; Y pos, tile id, attributes, X pos
              '''

        tokens = list(lexical(code))
        ast = syntax(tokens)
        self.assertEquals(4, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        self.assertEquals('.org', ast[0]['children'][0]['value'])
        self.assertEquals('S_DIRECTIVE', ast[1]['type'])
        self.assertEquals('.db', ast[1]['children'][0]['value'])
        self.assertEquals(['palette'], ast[1]['labels'])

        self.assertEquals('S_DIRECTIVE', ast[2]['type'])
        self.assertEquals('.db', ast[2]['children'][0]['value'])

        self.assertEquals('S_DIRECTIVE', ast[3]['type'])
        self.assertEquals('.db', ast[3]['children'][0]['value'])
        self.assertEquals(['sprites'], ast[3]['labels'])

        labels = get_labels(ast)
        expected = {'palette': 0xE000, 'sprites': 0xE000 + 32}

        self.assertEquals(expected, labels)

    def test_raise_erro_with_unknow_label(self):
        return
        with self.assertRaises(Exception):
            tokens = lexical('LDA unknow')
            list(tokens)

    def test_lexical_returns_a_generator(self):
        tokens = lexical('BIT $00')
        self.assertIsInstance(tokens, GeneratorType)


########NEW FILE########
__FILENAME__ = composer_conditional_test
# -*- coding: utf-8 -*-

import unittest

from pynes.tests import ComposerTestCase


class ComposerConditionalTest(ComposerTestCase):

    @unittest.skip("refactoring")
    def test_if_main(self):
        (
            self.assert_asm_without_ines_from(
                'if __name__ == "main":\n'
                '  pass\n'
            )
            # .has('.rsset $0000')
            # .and_then('variable .rs 1')
        )

    def test_if_true(self):
        (
            self.assert_asm_without_ines_from(
                'variable = True\n'
                'if variable:\n'
                '  variable = False\n'
                'else:\n'
                '  variable = True\n'
            )
            # .has('.rsset $0000')
            # .and_then('variable .rs 1')
        )

########NEW FILE########
__FILENAME__ = composer_example_mario_test
# -*- coding: utf-8 -*-

import unittest

from pynes.tests import ComposerTestCase


class ComposerMarioTest(ComposerTestCase):

    def test_mario(self):
        self.path = 'fixtures/nerdynights/scrolling/'
        f = open('pynes/examples/mario.py')
        code = f.read()
        f.close()
        (
            self.assert_asm_from(code)
                .has('.bank 0')
                .and_then('WAITVBLANK:')
                .and_then('RESET:')
                .and_then('JSR WAITVBLANK')
                .and_then('CLEARMEM:')
                .and_then('JSR WAITVBLANK')
                .and_then('LoadPalettes:')
                .and_then('LDA #%10000000')
                .and_then('STA $2000')
                .and_then('LDA #%00010000')
                .and_then('STA $2001')

                .and_then('NMI:')
                .and_then('.bank 1')
                .and_then('palette:')
                .and_then('tinymario:')
                .and_then('mario:')
        )

########NEW FILE########
__FILENAME__ = composer_example_movingsprite_test
# -*- coding: utf-8 -*-

import unittest

from pynes.tests import ComposerTestCase


class ComposerExampleMovingSpriteTest(ComposerTestCase):

    def test_compile_moving_sprite(self):
        self.path = 'fixtures/movingsprite/'
        f = open('pynes/examples/movingsprite.py')
        code = f.read()
        f.close()
        (
            self.assert_asm_from(code)
                .has('.bank 0')
                .and_then('WAITVBLANK:')
                .and_then('RESET:')
                .and_then('JSR WAITVBLANK')
                .and_then('CLEARMEM:')
                .and_then('JSR WAITVBLANK')
                .and_then('LoadPalettes:')
                .and_then('LoadSprites:')
            # TODO:
            # .and_then('LDA #%10000000')
                .and_then('NMI:')
                .and_then('JoyPad1A:')
                .and_then('JoyPad1B:')
                .and_then('JoyPad1Select:')
                .and_then('JoyPad1Start:')
                .and_then('JoyPad1Up:')
                .and_then('JoyPad1Down:')
                .and_then('JoyPad1Left:')
                .and_then('JoyPad1Right:')
                .and_then('sprite:')
        )

########NEW FILE########
__FILENAME__ = composer_example_slide_test
# -*- coding: utf-8 -*-
from pynes.tests import ComposerTestCase


class ComposerSlideTest(ComposerTestCase):

    def test_mario(self):
        self.path = 'fixtures/nerdynights/scrolling/'
        f = open('pynes/examples/slides.py')
        code = f.read()
        f.close()
        (
            self.assert_asm_from(code)


                .has('.rsset $0000')
                .and_then('slide .rs 1')

                .and_then('.bank 0')
                .and_then('WAITVBLANK:')
                .and_then('RESET:')
                .and_then('JSR WAITVBLANK')
                .and_then('CLEARMEM:')
                .and_then('JSR WAITVBLANK')
                .and_then('LoadPalettes:')
            # .and_then('LDA #%10000000')

                .and_then('LDA #00')
                .and_then('STA slide')
                .and_then('STA $2000')
            # .and_then('LDA #%00010000')
                .and_then('STA $2001')

                .and_then('NMI:')

                .and_then('JoyPad1A:')
                .and_then('LDA slide')
                .and_then('CLC')
                .and_then('ADC #01')
                .and_then('STA slide')
                .and_then('EndA:')

                .and_then('.bank 1')

            # .and_then('palette:')
            # .and_then('tinymario:')
            # .and_then('mario:')
        )

########NEW FILE########
__FILENAME__ = composer_test
# -*- coding: utf-8 -*-
from pynes.tests import ComposerTestCase

from pynes.game import Game, PPUSprite

from pynes.composer import compose

from pynes.nes_types import NesString


class ComposerTest(ComposerTestCase):

    def test_sprite_assigned_128_to_x(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).x = 128'
        )
            .has('LDA #128')
            .and_then('STA $0203'))

    def test_sprite_assigned_126_plus_2_optimized(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).x = 126 + 2')
         .has('LDA #128')
         .and_then('STA $0203'))

    def test_sprite_zero_assigned_127_plus_1_optimized(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).x = 127 + 1')
         .has('LDA #128')
         .and_then('STA $0203'))

    def test_sprite_zero_assigned_129_to_y(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).y = 129')
         .has('LDA #129')
         .and_then('STA $0200'))

    def test_sprite_zero_augassign_y_plus_five(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).y += 5')
         .has('LDA $0200')
         .and_then('CLC')
         .and_then('ADC #5')
         .and_then('STA $0200'))

    def test_sprite_zero_augassign_x_plus_five(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'get_sprite(0).x += 5')
         .has('LDA $0203')
         .and_then('CLC')
         .and_then('ADC #5')
         .and_then('STA $0203'))

    def test_sprite_zero_augassign_y_minus_five(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).y -= 5')
         .has('LDA $0200')
         .and_then('SEC')
         .and_then('SBC #5')
         .and_then('STA $0200'))

    def test_sprite_zero_augassign_x_minus_five(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).x -= 5')
         .has('LDA $0203')
         .and_then('SEC')
         .and_then('SBC #5')
         .and_then('STA $0203'))

    def test_sprite_zero_augassign_plus_two_inside_a_joystick_up(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'def joypad1_up():'
            '   get_sprite(0).y += 5')
         .has('NMI:')
         .and_then('BEQ EndUp')
         .and_then('LDA $0200')
         .and_then('CLC')
         .and_then('ADC #5')
         .and_then('STA $0200')
         .and_then('EndUp:')
         .and_then('.dw NMI')
         )

    def test_ppusprite_with_0(self):
        s = PPUSprite(0, Game())
        self.assertEquals(0x0200, s.y)
        self.assertEquals(0x0203, s.x)

    def test_ppusprite_with_1(self):
        s = PPUSprite(1, Game())
        self.assertEquals(0x0204, s.y)
        self.assertEquals(0x0207, s.x)

    def test_sprite_one_assign_100(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(1).y += 100')
         .has('LDA $0204')
         .and_then('CLC')
         .and_then('ADC #100')
         .and_then('STA $0204'))

    def test_show_gutomaia(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'gutomaia = "Guto Maia"\n'

            'def reset():'
            '  show(gutomaia, 0, 0)\n'
        )
            .has('.rsset $0000')
            .and_then('addressLow .rs 1')
            .and_then('addressHigh .rs 1')
            .and_then('posLow .rs 1')
            .and_then('posHigh .rs 1')
            .and_then('Show:')
            .and_then('LDA $2002')
            .and_then('LDA posHigh')
            .and_then('STA $2006')
            .and_then('LDA posLow')
            .and_then('STA $2006')
            .and_then('LDY #$00')
            .and_then('PrintLoop:')
            .and_then('LDA (addressLow), y')
            .and_then('CMP #$25')
            .and_then('BEQ PrintEnd')
            .and_then('STA $2007')
            .and_then('INY')
            .and_then('JMP PrintLoop')
            .and_then('PrintEnd:')
            .and_then('RTS')

            .and_then('RESET:')
            .and_then('LDA #LOW(gutomaia)')
            .and_then('STA addressLow')
            .and_then('LDA #HIGH(gutomaia)')
            .and_then('STA addressHigh')

            .and_then('LDA #$20')
            .and_then('STA posHigh')
            .and_then('LDA #$00')
            .and_then('STA posLow')
            .and_then('JSR Show')

            .and_then('LDA #%10010000')
            .and_then('STA $2000')
            .and_then('LDA #%00001000')
            .and_then('STA $2001')

            .and_then('NMI:')

            .and_then('LDA #00')
            .and_then('STA $2005')
            .and_then('STA $2005')

            .and_then('.bank 1')
            .and_then('gutomaia:')
            .and_then('.db $10,$1E,$1D,$18,$24,$16,$0A,$12,$0A,$25')
        )

    def test_show_guto(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'guto = "Guto"\n'

            'def reset():'
            '  show(guto, 0, 2)\n'
        )
            .has('.rsset $0000')
            .and_then('addressLow .rs 1')
            .and_then('addressHigh .rs 1')
            .and_then('posLow .rs 1')
            .and_then('posHigh .rs 1')
            .and_then('Show:')
            .and_then('LDA $2002')
            .and_then('LDA posHigh')
            .and_then('STA $2006')
            .and_then('LDA posLow')
            .and_then('STA $2006')
            .and_then('LDY #$00')
            .and_then('PrintLoop:')
            .and_then('LDA (addressLow), y')
            .and_then('CMP #$25')
            .and_then('BEQ PrintEnd')
            .and_then('STA $2007')
            .and_then('INY')
            .and_then('JMP PrintLoop')
            .and_then('PrintEnd:')
            .and_then('RTS')

            .and_then('RESET:')
            .and_then('LDA #LOW(guto)')
            .and_then('STA addressLow')
            .and_then('LDA #HIGH(guto)')
            .and_then('STA addressHigh')

            .and_then('LDA #$20')
            .and_then('STA posHigh')
            .and_then('LDA #$02')
            .and_then('STA posLow')
            .and_then('JSR Show')

            .and_then('guto:')
            .and_then('.db $10,$1E,$1D,$18,$25')
        )

    def test_show_guto_at_line_1_col_0(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'guto = "Guto"\n'

            'def reset():'
            '  show(guto, 1, 0)\n'
        )
            .and_then('RESET:')
            .and_then('LDA #LOW(guto)')
            .and_then('STA addressLow')
            .and_then('LDA #HIGH(guto)')
            .and_then('STA addressHigh')

            .and_then('LDA #$20')
            .and_then('STA posHigh')
            .and_then('LDA #$20')
            .and_then('STA posLow')
            .and_then('JSR Show')

            .and_then('guto:')
            .and_then('.db $10,$1E,$1D,$18,$25')
        )

    def test_show_guto_at_line_1_col_1(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'guto = "Guto"\n'

            'def reset():'
            '  show(guto, 1, 1)\n'
        )
            .and_then('RESET:')
            .and_then('LDA #LOW(guto)')
            .and_then('STA addressLow')
            .and_then('LDA #HIGH(guto)')
            .and_then('STA addressHigh')

            .and_then('LDA #$20')
            .and_then('STA posHigh')
            .and_then('LDA #$21')
            .and_then('STA posLow')
            .and_then('JSR Show')

            .and_then('guto:')
            .and_then('.db $10,$1E,$1D,$18,$25')
        )

    def test_load_palette_with_nes_array(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'palette = [0,1,2,3,4,5,6,7]\n'

            'load_palette(palette)\n'
        )
            .has('.bank 0')
            .and_then('LoadPalettes:')
            .and_then('LoadPalettesIntoPPU:')
            .and_then('LDA palette, x')
            .and_then('STA $2007')
            .and_then('INX')
            .and_then('CPX #$08')
            .and_then('palette:')

        )

    def test_load_palette_with_nes_array_2(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'
            'mypalette = [0,1,2,3,4,5,6,7]\n'

            'load_palette(mypalette)\n'
        )
            .has('.bank 0')
            .and_then('LoadPalettes:')
            .and_then('LoadPalettesIntoPPU:')
            .and_then('LDA mypalette, x')
            .and_then('STA $2007')
            .and_then('INX')
            .and_then('CPX #$08')
            .and_then('mypalette:')
        )

    def test_import_chr_player(self):
        self.path = 'fixtures/movingsprite/'
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'chrfile = import_chr("player.chr")\n'
        )
            .has('.bank 2')
            .and_then('.org $0000')
            .and_then('.incbin "player.chr"')
        )

    def test_string_hellow(self):
        (self.assert_asm_from(
            'hello = "world"'
        )
        )
        self.assertEquals(1, len(self.game._vars))
        self.assertTrue(isinstance(self.game._vars['hello'], NesString))
        self.assertEquals("world", self.game._vars['hello'])

    def test_import_chr_mario(self):
        self.path = 'fixtures/nerdynights/scrolling/'
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'chrfile = import_chr("mario.chr")\n'
        )
            .has('.bank 2')
            .and_then('.org $0000')
            .and_then('.incbin "mario.chr"')
        )

    def test_movingsprite(self):
        code = (
            'from pynes.bitbag import *\n'

            # 'import_chr("player.chr")\n'
            'palette = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,\n'
            '    0x0F, 48, 49, 50, 51, 53, 54, 55, 56, 57, 58, 59,\n'
            '    60, 61, 62, 63 ]\n'
            # 'sprite = define_sprite()\n'
            'px = rs(1)\n'
            'py = rs(1)\n'

            'def reset():\n'
            '    wait_vblank()\n'
            # '    clearmen()\n'
            '    wait_vblank()\n'
            # '    load_palette(palette)\n'
            # '    load_sprite(sprite)\n'

            'def joypad1_up():\n'
            '    global y\n'
            '    py += 1\n'

            'def joypad1_down():\n'
            '    global y\n'
            '    py -= 1\n'

            'def joypad1_left():\n'
            '     get_sprite(0).x += 1'
            # '    global x\n'
            # '    px -= 1\n'

            # 'def joypad1_right():\n'
            # '    global x\n'
            # '    px += 1\n'
        )

        game = compose(code)
        asm = game.to_asm()
        # self.assertEquals(1, len(game.bitpaks))
        self.assertTrue('.bank 0' in asm)
        self.assertTrue('.org $C000' in asm)
        self.assertTrue('.bank 1' in asm)
        self.assertTrue('.org $E000' in asm)
        self.assertTrue('NMI:' in asm)
        self.assertTrue('JoyPad1Select:' in asm)
        self.assertTrue('JoyPad1Start:' in asm)
        self.assertTrue('JoyPad1A:' in asm)
        self.assertTrue('JoyPad1B:' in asm)
        self.assertTrue('JoyPad1Up:' in asm)
        self.assertTrue('JoyPad1Down:' in asm)
        self.assertTrue('JoyPad1Left:' in asm)
        self.assertTrue('JoyPad1Right:' in asm)

    def test_wait_vblank(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'def reset():\n'
            '    wait_vblank()')
         .has('.bank 0')
         .and_then('.org $C000')
         .and_then('WAITVBLANK:')
         .and_then('RTS')
         .and_then('RESET:')
         .and_then('.bank 1')
         .and_then('.dw 0')
         .and_then('.dw RESET')
         .and_then('.dw 0')
         )
        self.assertTrue('.org $E000' not in self.asm)
        self.assertTrue('NMI:' not in self.asm)
        self.assertEquals(1, len(self.game.bitpaks))

    def test_wait_vblank_called_twice(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'def reset():\n'
            '    wait_vblank()\n'
            '    wait_vblank()')
         .has('.bank 0')
         .and_then('.org $C000'))

        self.assertEquals(1, len(self.game.bitpaks))
        # self.assertTrue('.bank 1' not in self.asm)
        self.assertTrue('.org $E000' not in self.asm)

    def test_palette_list_definition_from_00_to_04(self):
        (self.assert_asm_from(
            'palette = [0,1,2,3]')

         .has('.bank 1')
         .and_then('.org $E000')
         .and_then(
             'palette:\n'
             '  .db $00,$01,$02,$03')
         )

        self.assertEquals(1, len(self.game._vars))
        self.assertEquals([0, 1, 2, 3],
                          self.game.get_var('palette'))
        # self.assertTrue('.bank 0' not in self.asm)
        # self.assertTrue('.org $C000' not in self.asm)

    def test_palette_list_definition_from_00_to_0F(self):
        (self.assert_asm_from(
            'palette = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]')

         .has('.bank 1')
         .and_then('.org $E000')
         .and_then(
             'palette:\n'
             '  .db $00,$01,$02,$03,$04,$05,$06,$07,$08,$09,$0A,$0B,$0C,$0D,'
             '$0E,$0F')
         )
        self.assertEquals(1, len(self.game._vars))
        self.assertEquals(
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            self.game.get_var('palette'))
        self.assertTrue('.bank 0' not in self.asm)
        self.assertTrue('.org $C000' not in self.asm)

    def test_palette_list_definition_from_0F_to_00(self):
        (self.assert_asm_from(
            'palette = [15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0]')
         .has('.bank 1')
         .and_then('.org $E000')
         .and_then(
             'palette:\n'
             '  .db $0F,$0E,$0D,$0C,$0B,$0A,$09,$08,$07,$06,$05,$04,$03,$02,'
             '$01,$00')
         )
        self.assertEquals(1, len(self.game._vars))
        self.assertEquals(
            [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
            self.game.get_var('palette'))
        self.assertTrue('.bank 0' not in self.asm)
        self.assertTrue('.org $C000' not in self.asm)

    def test_palette_list_definition_from_00_to_1F(self):
        (self.assert_asm_from('palette = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,'
                              '15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,'
                              '30,31]')
         .has('.bank 1')
         .and_then('.org $E000')
         .and_then(
             'palette:\n'
             '  .db $00,$01,$02,$03,$04,$05,$06,$07,$08,$09,$0A,$0B,$0C,$0D,'
             '$0E,$0F\n'
             '  .db $10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$1A,$1B,$1C,$1D,'
             '$1E,$1F')
         )
        self.assertEquals(1, len(self.game._vars))
        self.assertEquals(range(32), self.game.get_var('palette'))
        # self.assertTrue('.bank 0' not in self.asm)
        self.assertTrue('.org $C000' not in self.asm)

    def test_define_sprite_with_x_128_y_64_and_tile_0(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'sprite = define_sprite(128, 64 ,0, 3)\n'
        )
            .has('.bank 1')
            .and_then(
                'sprite:\n'
                '  .db $40, $00, $03, $80')
        )

    def test_define_sprite_with_x_64_and_y_128_and_tile_1(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'sprite = define_sprite(64, 128, 1, 3)\n'
        )
            .has('.bank 1')
            .and_then(
                'sprite:\n'
                '  .db $80, $01, $03, $40')
        )

    def test_define_sprite_using_an_array(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
        )
            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_load_sprite_using_an_array(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 0)'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_plus_five_on_x_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 0)\n'

            'get_sprite(mario).x += 5'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0203')
            .and_then('CLC')
            .and_then('ADC #5')
            .and_then('STA $0203')
            .and_then('STA $020B')
            .and_then('CLC')
            .and_then('ADC #8')
            .and_then('STA $0207')
            .and_then('STA $020F')
            # TODO has not (CLC)
            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_plus_ten_on_x_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 1)\n'

            'get_sprite(mario).x += 10'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0204, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0207')
            .and_then('CLC')
            .and_then('ADC #10')
            .and_then('STA $0207')
            .and_then('STA $020F')
            .and_then('CLC')
            .and_then('ADC #8')
            .and_then('STA $020B')
            .and_then('STA $0213')

            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_plus_five_on_y_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 0)\n'

            'get_sprite(mario).y += 5'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0200')
            .and_then('CLC')
            .and_then('ADC #5')
            .and_then('STA $0200')
            .and_then('STA $0204')
            .and_then('CLC')
            .and_then('ADC #8')
            .and_then('STA $0208')
            .and_then('STA $020C')

            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_plus_10_on_y_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 1)\n'

            'get_sprite(mario).y += 10'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0204, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0204')
            .and_then('CLC')
            .and_then('ADC #10')
            .and_then('STA $0204')
            .and_then('STA $0208')
            .and_then('CLC')
            .and_then('ADC #8')
            .and_then('STA $020C')
            .and_then('STA $0210')

            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_minus_five_on_x_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 0)\n'

            'get_sprite(mario).x -= 5'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')
            .and_then('LDA $0207')
            .and_then('SEC')
            .and_then('SBC #5')
            .and_then('STA $020F')
            .and_then('STA $0207')
            .and_then('SEC')
            .and_then('SBC #8')
            .and_then('STA $020B')
            .and_then('STA $0203')
            # TODO has not (CLC)
            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_minus_ten_on_x_with_four_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 1)\n'

            'get_sprite(mario).x -= 10'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0204, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')
            .and_then('LDA $020B')
            .and_then('SEC')
            .and_then('SBC #10')
            .and_then('STA $0213')
            .and_then('STA $020B')
            .and_then('SEC')
            .and_then('SBC #8')
            .and_then('STA $020F')
            .and_then('STA $0207')
            # TODO has not (CLC)
            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_move_sprite_minus_five_on_x_with_eight_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [0,1,2,3,4,5,6,7], 0)\n'
            'load_sprite(mario, 0)\n'

            'get_sprite(mario).x -= 5'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #32')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0207')
            .and_then('SEC')
            .and_then('SBC #5')
            .and_then('STA $021F')
            .and_then('STA $0217')
            .and_then('STA $020F')
            .and_then('STA $0207')
            .and_then('SEC')
            .and_then('SBC #8')
            .and_then('STA $021B')
            .and_then('STA $0213')
            .and_then('STA $020B')
            .and_then('STA $0203')
            # TODO has not (CLC)
            .has('.bank 1')
            .and_then('mario:')
        )

    def test_move_sprite_minus_five_on_y_with_eight_tiles(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [0,1,2,3,4,5,6,7], 0)\n'
            'load_sprite(mario, 0)\n'

            'get_sprite(mario).x += 5'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #32')
            .and_then('BNE LoadSpritesIntoPPU')

            .and_then('LDA $0203')  # TODO $0207
            .and_then('CLC')
            .and_then('ADC #5')
            .and_then('STA $0203')
            .and_then('STA $020B')
            .and_then('STA $0213')
            .and_then('STA $021B')
            .and_then('CLC')
            .and_then('ADC #8')
            .and_then('STA $0207')
            .and_then('STA $020F')
            .and_then('STA $0217')
            .and_then('STA $021F')
            # TODO has not (CLC)
            .has('.bank 1')
            .and_then('mario:')
        )

    def test_load_sprite_using_an_array_in_slot_1(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'mario = define_sprite(128, 128, [50,51,52,53], 0)\n'
            'load_sprite(mario, 1)'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA mario, x')
            .and_then('STA $0204, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')

            .has('.bank 1')
            .and_then('mario:')
            .and_then('.db $80, $32, $00, $80')
            .and_then('.db $80, $33, $00, $88')
            .and_then('.db $88, $34, $00, $80')
            .and_then('.db $88, $35, $00, $88')
        )

    def test_load_sprite_twice_in_the_sequence(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'tinymario = define_sprite(108, 144, [50,51,52,53], 0)\n'
            'mario = define_sprite(128,128, [0, 1, 2, 3, 4, 5, 6, 7], 0)\n'

            'def reset():\n'
            '  load_sprite(tinymario, 0)\n'
            '  load_sprite(mario, 4)\n'
        )
            .has('.bank 0')
            .and_then('RESET:')
            .and_then('LoadSprites:')  # change to LoadMarioSprite
            .and_not_from_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA tinymario, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #16')
            .and_then('BNE LoadSpritesIntoPPU')
            .and_then('LoadSprites1:')  # change to #LoadTinyMarioSprite
            .and_then('LoadSpritesIntoPPU1:')
            .and_then('BNE LoadSpritesIntoPPU1')
            .and_then('InfiniteLoop:')

            .and_then('.bank 1')
            .and_then('.org $E000')
            .and_then('tinymario:')
            .and_then('mario:')
            .and_then('.org $FFFA')
            .and_then('.dw NMI')
            .and_then('.dw RESET')
        )

    def test_load_sprite(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'sprite = define_sprite(128, 64 ,0, 3)\n'

            'load_sprite(sprite, 0)'
        )
            .has('.bank 0')
            .and_then('LoadSprites:')
            .and_then('LDX #$00')
            .and_then('LoadSpritesIntoPPU:')
            .and_then('LDA sprite, x')
            .and_then('STA $0200, x')
            .and_then('INX')
            .and_then('CPX #4')  # TODO it should be 4
            .and_then('BNE LoadSpritesIntoPPU')
            .and_then('.bank 1')
            .and_then(
                'sprite:\n'
                '  .db $40, $00, $03, $80')
        )

    def test_flip_horizontal_sprite_zero(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).flip_horizontal()\n'
        )
            .has('.bank 0')
            .and_then('LDA $0202')
            .and_then('EOR #64')
            .and_then('STA $0202')
        )

    def test_flip_vertical_sprite_zero(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(0).flip_vertical()\n'
        )
            .has('.bank 0')
            .and_then('LDA $0202')
            .and_then('EOR #128')
            .and_then('STA $0202')
        )

    def test_flip_horizontal_sprite_one(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(1).flip_horizontal()\n'
        )
            .has('.bank 0')
            .and_then('LDA $0206')
            .and_then('EOR #64')
            .and_then('STA $0206')
        )

    def test_flip_vertical_sprite_one(self):
        (self.assert_asm_from(
            'from pynes.bitbag import *\n'

            'get_sprite(1).flip_vertical()\n'
        )
            .has('.bank 0')
            .and_then('LDA $0206')
            .and_then('EOR #128')
            .and_then('STA $0206')
        )

    def test_rs_with_x_and_y_with_size_1(self):
        code = (
            'from pynes.bitbag import *\n'
            'x = rs(1)\n'
            'y = rs(1)')
        game = compose(code)
        asm = game.to_asm()
        self.assertEquals(2, len(game._vars))
        self.assertEquals(1, game._vars['x'].size)
        self.assertEquals(1, game._vars['y'].size)
        self.assertTrue('.bank 0' not in asm)
        self.assertTrue('.org $C000' not in asm)
        # self.assertTrue('.bank 1' not in asm)
        self.assertTrue('.org $E000' not in asm)

        self.assertTrue('.rsset $0000' in asm)
        self.assertTrue('x .rs 1' in asm)
        self.assertTrue('y .rs 1' in asm)

    def test_rs_with_scroll(self):
        code = (
            'from pynes.bitbag import *\n'
            'scroll = rs(1)\n'
            'nametable = rs(1)\n'
            'columnLow = rs(1)\n'
            'columnHigh = rs(1)\n'
            'sourceLow = rs(1)\n'
            'sourceHigh = rs(1)\n'
            'columnNumber = rs(1)\n')
        game = compose(code)
        asm = game.to_asm()
        self.assertEquals(7, len(game._vars))
        self.assertEquals(1, game._vars['scroll'].size)
        self.assertEquals(1, game._vars['nametable'].size)
        self.assertEquals(1, game._vars['columnLow'].size)
        self.assertEquals(1, game._vars['columnHigh'].size)
        self.assertEquals(1, game._vars['sourceLow'].size)
        self.assertEquals(1, game._vars['sourceHigh'].size)
        self.assertEquals(1, game._vars['columnNumber'].size)
        self.assertTrue('.bank 0' not in asm)
        self.assertTrue('.org $C000' not in asm)
        # self.assertTrue('.bank 1' not in asm)
        self.assertTrue('.org $E000' not in asm)
        self.assertTrue('.rsset $0000' in asm)
        self.assertTrue('scroll .rs 1' in asm)
        self.assertTrue('nametable .rs 1' in asm)
        self.assertTrue('columnLow .rs 1' in asm)
        self.assertTrue('columnHigh .rs 1' in asm)
        self.assertTrue('sourceLow .rs 1' in asm)
        self.assertTrue('sourceHigh .rs 1' in asm)
        self.assertTrue('columnNumber .rs 1' in asm)

    def test_undefined_def_raises_nameerror(self):
        code = (
            'from pynes.bitbag import *\n'

            'undefined_def()\n'
        )

        with self.assertRaises(NameError) as nm:
            compose(code)

        self.assertEquals("name 'undefined_def' is not defined",
                          nm.exception.message)

    def test_wait_vblank_raises_typeerror_when_called_with_args(self):
        code = (
            'from pynes.bitbag import *\n'

            'wait_vblank(1)'
        )

        with self.assertRaises(TypeError) as te:
            compose(code)

        self.assertEquals(
            'wait_vblank() takes exactly 1 argument (2 given)',
            te.exception.message)

    def test_load_palette_raises_typeerror_when_called_without_args(self):
        code = (
            'from pynes.bitbag import *\n'

            'load_palette()'
        )

        with self.assertRaises(TypeError) as te:
            compose(code)

        self.assertEquals(
            'load_palette() takes exactly 2 arguments (1 given)',
            te.exception.message)

########NEW FILE########
__FILENAME__ = cpx_test
# -*- coding: utf-8 -*-
'''
CPX, Compare with X Test
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class CpxTest(unittest.TestCase):

    def test_cpx_imm(self):
        tokens = list(lexical('CPX #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe0, 0x10])

    def test_cpx_imm_with_decimal(self):
        tokens = list(lexical('CPX #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe0, 0x0a])

    def test_cpx_imm_with_binary(self):
        tokens = list(lexical('CPX #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe0, 0x04])

    def test_cpx_zp(self):
        tokens = list(lexical('CPX $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe4, 0x00])

    def test_cpx_abs(self):
        tokens = list(lexical('CPX $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xec, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = cpy_test
# -*- coding: utf-8 -*-
'''
CPY, Compare with Y Test

'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class CpyTest(unittest.TestCase):

    def test_cpy_imm(self):
        tokens = list(lexical('CPY #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc0, 0x10])

    def test_cpy_imm_with_decimal(self):
        tokens = list(lexical('CPY #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc0, 0x0a])

    def test_cpy_imm_with_binary(self):
        tokens = list(lexical('CPY #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc0, 0x04])

    def test_cpy_zp(self):
        tokens = list(lexical('CPY $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc4, 0x00])

    def test_cpy_abs(self):
        tokens = list(lexical('CPY $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xcc, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = dec_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class DecTest(unittest.TestCase):

    def test_dec_zp(self):
        tokens = list(lexical('DEC $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc6, 0x00])

    def test_dec_zpx(self):
        tokens = list(lexical('DEC $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xd6, 0x10])

    def test_dec_abs(self):
        tokens = list(lexical('DEC $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xce, 0x34, 0x12])

    def test_dec_absx(self):
        tokens = list(lexical('DEC $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xde, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = dex_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class DexTest(unittest.TestCase):

    def test_dex_sngl(self):
        tokens = list(lexical('DEX'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xca])

########NEW FILE########
__FILENAME__ = dey_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class DeyTest(unittest.TestCase):

    def test_dey_sngl(self):
        tokens = list(lexical('DEY'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x88])

########NEW FILE########
__FILENAME__ = directive_test
# -*- coding: utf-8 -*-

import unittest
from pynes.compiler import lexical, syntax, semantic

# TODO: from pynes.asm import get_var


class DirectiveTest(unittest.TestCase):

    def test_label(self):
        tokens = list(lexical('label:'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_LABEL', tokens[0]['type'])
        # ast = syntax(tokens)
        # self.assertEquals(1 , len(ast))

    def test_inesprg(self):
        tokens = list(lexical('.inesprg 1'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_ARGUMENT', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast, True)
        # self.assertEquals(1, get_var('inesprg'))
        self.assertEquals(code[4], 1)

    def test_ineschr(self):
        tokens = list(lexical('.ineschr 1'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_ARGUMENT', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast, True)
        # self.assertEquals(1, get_var('ineschr'))
        self.assertEquals(code[5], 1)

    def test_inesmap(self):
        tokens = list(lexical('.inesmap 1'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_ARGUMENT', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast, True)
        # self.assertEquals(1, get_var('inesmap'))
        self.assertEquals(code[6], 1)

    def test_inesmir(self):
        tokens = list(lexical('.inesmir 1'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_ARGUMENT', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast, True)
        # self.assertEquals(1, get_var('inesmir'))
        self.assertEquals(code[7], 1)

    def test_bank_0(self):
        tokens = list(lexical('.bank 0'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_ARGUMENT', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        # code = semantic(ast)

    def test_org_0000(self):
        tokens = list(lexical('.org $0000'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        # code = semantic(ast)
        # self.assertEquals(0x0000, get_pc())

    def test_org_c000(self):
        tokens = list(lexical('.org $C000'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        # code = semantic(ast)
        # self.assertEquals(0xc000, get_pc())

    def test_org_fffa(self):
        tokens = list(lexical('.org $FFFA'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        # code = semantic(ast)
        # self.assertEquals(0xfffa, get_pc())

    def test_db_1(self):
        code = ('.db $0F,$01,$02,$03,$04,$05,$06,$07,' # One-liner string
                    '$08,$09,$0A,$0B,$0C,$0D,$0E,$0F')
        tokens = list(lexical(code))
        self.assertEquals(32, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        # self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertIsNotNone(code)
        expected = [
            0x0f, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F
        ]
        self.assertEquals(expected, code)

    def test_db_2(self):
        code = ('.db $0F,$30,$31,$32,$33,$35,$36,$37,' # One-liner string
                    '$38,$39,$3A,$3B,$3C,$3D,$3E,$0F')
        tokens = list(lexical(code))
        self.assertEquals(32, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        # self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertIsNotNone(code)
        expected = [0x0f, 0x30, 0x31, 0x32, 0x33, 0x35, 0x36, 0x37, 0x38,
                    0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x0F]
        self.assertEquals(expected, code)

    def test_db_3(self):
        tokens = list(lexical('.db $80, $00, $03, $80'))
        self.assertEquals(8, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        # self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertIsNotNone(code)
        expected = [0x80, 0x0, 0x03, 0x80]
        self.assertEquals(expected, code)

    def test_db_4(self):
        code = '''.db $80, $00, $03, $80
        .db $01, $02, $03, $04
        '''
        tokens = list(lexical(code))
        self.assertEquals(18, len(tokens))
        self.assertEquals('T_DIRECTIVE', tokens[0]['type'])
        # self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(2, len(ast))
        self.assertEquals('S_DIRECTIVE', ast[0]['type'])
        code = semantic(ast)
        self.assertIsNotNone(code)
        expected = [0x80, 0x0, 0x03, 0x80, 1, 2, 3, 4]
        self.assertEquals(expected, code)

########NEW FILE########
__FILENAME__ = eor_test
# -*- coding: utf-8 -*-
'''
EOR, Exclusive OR Test

This is one of the logical operations in the c6502.
'''
import unittest

from pynes.compiler import lexical, syntax, semantic


class EorTest(unittest.TestCase):

    '''Test logical EOR operation between $10 (Decimal 16) and the
    content of the Accumulator'''

    def test_eor_imm(self):
        tokens = list(lexical('EOR #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x49, 0x10])

    '''Test logical EOR operation between 10 (Decimal 10) and the
    content of the Accumulator'''

    def test_eor_imm_with_decimal(self):
        tokens = list(lexical('EOR #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x49, 0x0a])

    '''Test logical EOR operation between binary %00000100
    (Decimal 4) and the content of the Accumulator'''

    def test_eor_imm_with_binary(self):
        tokens = list(lexical('EOR #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x49, 0x04])

    '''Test logical EOR operation between the content of the
    Accumulator and the content of zero page $00'''

    def test_eor_zp(self):
        tokens = list(lexical('EOR $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x45, 0x00])

    def test_eor_zpx(self):
        tokens = list(lexical('EOR $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x55, 0x10])

    def test_eor_abs(self):
        tokens = list(lexical('EOR $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4D, 0x34, 0x12])

    def test_eor_absx(self):
        tokens = list(lexical('EOR $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x5D, 0x34, 0x12])

    def test_eor_absy(self):
        tokens = list(lexical('EOR $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x59, 0x34, 0x12])

    def test_eor_indx(self):
        tokens = list(lexical('EOR ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x41, 0x20])

    def test_eor_indy(self):
        tokens = list(lexical('EOR ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x51, 0x20])

########NEW FILE########
__FILENAME__ = guide_test
# -*- coding: utf-8 -*-
import unittest

from pynes.compiler import lexical, syntax

'''
Those tests are based on examples from:
http://nesdev.parodius.com/6502guid.txt
'''


class GuideTest(unittest.TestCase):

    def test_example_16_bit_subtraction_routine(self):
        ex_2 = '''
            SEC         ;clear the carry
            LDA $20     ;get the low byte of the first number
            SBC $22     ;add to it the low byte of the second
            STA $24     ;store in the low byte of the result
            LDA $21     ;get the high byte of the first number
            SBC $23     ;add to it the high byte of the second, plus carry
            STA $25     ;store in high byte of the result
            '''
        tokens = list(lexical(ex_2))
        self.assertEquals(21, len(tokens))
        ast = syntax(tokens)
        self.assertEquals(7, len(ast))

    def test_example_4_2(self):
        example_4_2 = '''
        ; Example 4-2.  Deleting an entry from an unordered list
        ;
        ; Delete the contents of $2F from a list whose starting
        ; address is in $30 and $31.  The first byte of the list
        ; is its length.
        ;

        deluel: LDY #$00     ; fetch element count
                LDA ($30),Y
                TAX          ; transfer length to X
                LDA $2F      ; item to delete
        nextel: INY          ; index to next element
                CMP ($30),Y  ; do entry and element match?
                BEQ delete   ; yes. delete element
                DEX          ; no. decrement element count
                BNE nextel   ; any more elements to compare?
                RTS          ; no. element not in list. done

        ; delete an element by moving the ones below it up one location

        delete: DEX          ; decrement element count
                BEQ deccnt   ; end of list?
                INY          ; no. move next element up
                LDA ($30),Y
                DEY
                STA ($30),Y
                INY
                JMP delete
        deccnt: LDA ($30,X)  ; update element count of list
                SBC #$01
                STA ($30,X)
                RTS
        '''
        tokens = list(lexical(example_4_2))
        self.assertEquals(96, len(tokens))

    def test_example_5_6(self):
        """
        example_5_6 = '''
        ; Example 5-6.  16-bit by 16-bit unsigned multiply
        ;
        ; Multiply $22 (low) and $23 (high) by $20 (low) and
        ; $21 (high) producing a 32-bit result in $24 (low) to $27 (high)
        ;

        mlt16:  LDA #$00     ; clear p2 and p3 of product
                STA $26
                STA $27
                LDX #$16     ; multiplier bit count = 16
        nxtbt:  LSR $21      ; shift two-byte multiplier right
                ROR $20
                BCC align    ; multiplier = 1?
                LDA $26      ; yes. fetch p2
                CLC
                ADC $22      ; and add m0 to it
                STA $26      ; store new p2
                LDA $27      ; fetch p3
                ADC $23      ; and add m1 to it
        align:  ROR A        ; rotate four-byte product right
                STA $27      ; store new p3
                ROR $26
                ROR $25
                ROR $24
                DEX          ; decrement bit count
                BNE nxtbt    ; loop until 16 bits are done
                RTS
        '''
        # TODO ROR A?
        # tokens = list(lexical(example_5_6))
        """

    def test_example_5_14(self):
        example_5_14 = '''
        ; Example 5-14.  Simple 16-bit square root.
        ;
        ; Returns the 8-bit square root in $20 of the
        ; 16-bit number in $20 (low) and $21 (high). The
        ; remainder is in location $21.

        sqrt16: LDY #$01     ; lsby of first odd number = 1
                STY $22
                DEY
                STY $23      ; msby of first odd number (sqrt = 0)
        again:  SEC
                LDA $20      ; save remainder in X register
                TAX          ; subtract odd lo from integer lo
                SBC $22
                STA $20
                LDA $21      ; subtract odd hi from integer hi
                SBC $23
                STA $21      ; is subtract result negative?
                BCC nomore   ; no. increment square root
                INY
                LDA $22      ; calculate next odd number
                ADC #$01
                STA $22
                BCC again
                INC $23
                JMP again
        nomore: STY $20      ; all done, store square root
                STX $21      ; and remainder
                RTS
        '''
        tokens = list(lexical(example_5_14))
        self.assertEquals(74, len(tokens))

        self.assertEquals('T_ENDLINE', tokens[0]['type'])
        self.assertEquals('T_ENDLINE', tokens[1]['type'])
        self.assertEquals('T_ENDLINE', tokens[2]['type'])
        self.assertEquals('T_ENDLINE', tokens[3]['type'])
        self.assertEquals('T_ENDLINE', tokens[4]['type'])
        self.assertEquals('T_ENDLINE', tokens[5]['type'])
        self.assertEquals('T_ENDLINE', tokens[6]['type'])

        self.assertEquals('T_LABEL', tokens[7]['type'])
        self.assertEquals('T_INSTRUCTION', tokens[8]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[9]['type'])
        self.assertEquals('T_ENDLINE', tokens[10]['type'])

        self.assertEquals('T_INSTRUCTION', tokens[11]['type'])
        self.assertEquals('T_ADDRESS', tokens[12]['type'])
        self.assertEquals('T_ENDLINE', tokens[13]['type'])

        self.assertEquals('T_INSTRUCTION', tokens[14]['type'])
        self.assertEquals('T_ENDLINE', tokens[15]['type'])

        self.assertEquals('T_INSTRUCTION', tokens[16]['type'])
        self.assertEquals('T_ADDRESS', tokens[17]['type'])
        self.assertEquals('T_ENDLINE', tokens[18]['type'])

########NEW FILE########
__FILENAME__ = image_test
# -*- coding: utf-8 -*-
import os

from PIL import Image
from pynes import image, sprite
from pynes.tests import SpriteTestCase


class ImageTest(SpriteTestCase):

    def __init__(self, testname):
        SpriteTestCase.__init__(self, testname)

    def setUp(self):
        self.mario1 = [
            [0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 3, 3, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 3, 2],
            [0, 3, 3, 2, 2, 3, 3, 2]
        ]

        self.mario2 = [
            [1, 1, 1, 0, 0, 0, 0, 0],
            [1, 1, 2, 0, 0, 0, 0, 0],
            [1, 2, 2, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 0, 0],
            [3, 2, 2, 2, 0, 0, 0, 0],
            [3, 3, 2, 2, 2, 2, 0, 0],
            [2, 2, 2, 2, 2, 2, 2, 0],
            [2, 2, 3, 2, 2, 2, 2, 0]
        ]

    def test_palette(self):
        palette = image.create_palette()
        self.assertEquals(64, len(palette))
        self.assertEquals((0x78, 0x80, 0x84), palette[0])
        self.assertEquals((0x00, 0x00, 0xfc), palette[1])
        self.assertEquals((0x00, 0x00, 0xc4), palette[2])

    '''Test if a portion of a image when fetched is equal
    to the same sprite'''

    def test_fetch_chr_0(self):
        pixels = Image.open('fixtures/mario.png').load()
        spr = image.fetch_chr(pixels, 0, 0)
        self.assertSpriteEquals(self.mario1, spr)

    '''Test if a portion of a image when fetched is equal
    to the same sprite'''

    def test_fetch_chr_1(self):
        pixels = Image.open('fixtures/mario.png').load()
        spr = image.fetch_chr(pixels, 1, 0)
        self.assertSpriteEquals(self.mario2, spr)

    '''Test the acquisition of a image file into a CHR'''

    def test_acquire_chr(self):
        img = Image.open('fixtures/mario.png')
        sprs, indexes = image.acquire_chr(img)
        self.assertEquals(8192, len(sprs))
        self.assertSpriteEquals(self.mario1, sprite.get_sprite(0, sprs))

    def test_import_chr(self):
        try:
            os.remove('/tmp/mario.chr')
        except:
            pass
        self.assertFileNotExists('/tmp/mario.chr')
        image.import_chr('fixtures/mario.png', '/tmp/mario.chr')
        self.assertFileExists('/tmp/mario.chr')
        self.assertCHRFileEquals(
            'fixtures/nerdynights/scrolling/mario.chr',
            '/tmp/mario.chr')
        os.remove('/tmp/mario.chr')

    def test_export_chr(self):
        try:
            os.remove('/tmp/mario.png')
        except:
            pass
        self.assertFileNotExists('/tmp/mario.png')
        image.export_chr(
            'fixtures/nerdynights/scrolling/mario.chr', '/tmp/mario.png')
        self.assertFileExists('/tmp/mario.png')
        self.assertPNGFileEquals('fixtures/mario.png', '/tmp/mario.png')

        img = Image.open('/tmp/mario.png')
        sprs, indexes = image.acquire_chr(img)
        self.assertIsNotNone(sprs)
        self.assertEquals(8192, len(sprs))
        self.assertSpriteEquals(self.mario1, sprite.get_sprite(0, sprs))
        self.assertSpriteEquals(self.mario2, sprite.get_sprite(1, sprs))

        os.remove('/tmp/mario.png')

    def test_export_namespace(self):
        try:
            os.remove('/tmp/level.png')
        except:
            pass

        self.assertFileNotExists('/tmp/level.png')
        image.export_nametable(
            'fixtures/nerdynights/scrolling/SMBlevel.bin',
            'fixtures/nerdynights/scrolling/mario.chr',
            '/tmp/level.png')
        self.assertFileExists('/tmp/level.png')

        img = Image.open('/tmp/level.png')
        sprs, indexes = image.acquire_chr(img, optimize_repeated=False)
        sprite.length(sprs)
        self.assertEquals(1024, sprite.length(sprs))
        return  # TODO why?!
        nt_file = open('fixtures/nerdynights/scrolling/SMBlevel.bin')
        nt = nt_file.read()
        nt_file.close()
        nts = [ord(n) for n in nt]
        mario = sprite.load_sprites('fixtures/nerdynights/scrolling/mario.chr')
        for i in range(32):
            for j in range(32):
                self.assertSpriteEquals(
                    sprite.get_sprite(nts[i * j] + 256, mario),
                    sprite.get_sprite(i * j, sprs)
                )
        os.remove('/tmp/level.png')

    def test_import_nametable(self):
        try:
            os.remove('/tmp/level.bin')
        except:
            pass

        self.assertFalse(os.path.exists('/tmp/level.bin'))

        image.import_nametable(
            'fixtures/level.png',
            'fixtures/nerdynights/scrolling/mario.chr',
            '/tmp/level.bin')

        expected = open(
            'fixtures/nerdynights/scrolling/SMBlevel.bin', 'rb').read()
        actual = open('/tmp/level.bin', 'rb').read()
        size = len(actual)
        self.assertEquals(expected[:size], actual[:size])
        # todo import entire namespace

    def test_read_nametable(self):
        # level = Image.open('fixtures/level.png')
        sprs = sprite.load_sprites('fixtures/nerdynights/scrolling/mario.chr')
        # nt = image.read_nametable(level, sprs)
        return
        expected = open(
            'fixtures/nerdynights/scrolling/SMBlevel.bin', 'rb').read()
        actual = open('/tmp/level.bin', 'rb').read()
        size = len(actual)
        self.assertEquals(expected[:size], actual[:size])
        return
        # sprs = image.convert_chr(img)
        self.assertEquals(8192, len(sprs))
        self.assertEquals(self.mario1, sprite.get_sprite(0, sprs))
        self.assertEquals(self.mario2, sprite.get_sprite(1, sprs))

    def test_acquire_pythonbrasil8(self):
        (nt, sprs) = image.acquire_nametable('fixtures/pythonbrasil8.png')
        # debug
        image.export_chr(sprs, '/tmp/pythonbrasil8_sprite.png')
        # debug
        image.export_nametable(nt, sprs, '/tmp/pythonbrasil8_nametable.png')
        from pynes import write_bin_code
        write_bin_code(nt, '/tmp/pythonbrasil8.bin')
        write_bin_code(sprs[0], '/tmp/pythonbrasil8.chr')

    def test_convert_to_nametable(self):
        return
        (nt, sprs) = image.convert_to_nametable('fixtures/level.png')
        # self.assertEquals(sprite.length(sprs), 15)

    def test_convert_to_nametable_pythonbrasil(self):
        return
        (nt, sprs) = image.convert_to_nametable('fixtures/pythonbrasil8.png')

    def test_convert_to_nametable_pythonbrasil2(self):
        return
        nt, sprs = image.convert_to_nametable('fixtures/pythonbrasil8.png')
        image.export_chr('sprite.chr', 'pythonbrasil8.png')
        image.export_nametable(
            'nametable.bin', 'sprite.chr', 'pythonbrasil8.png')
        import os
        os.rename('nametable.bin', 'pythonbrasil8.bin')
        image.export_nametable(
            'fixtures/nerdynights/scrolling/garoa.bin',
            'fixtures/nerdynights/scrolling/sprite.chr',
            'garoa.png')

########NEW FILE########
__FILENAME__ = inc_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class IncTest(unittest.TestCase):

    def test_inc_zp(self):
        tokens = list(lexical('INC $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe6, 0x00])

    def test_inc_zpx(self):
        tokens = list(lexical('INC $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf6, 0x10])

    def test_inc_abs(self):
        tokens = list(lexical('INC $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xee, 0x34, 0x12])

    def test_inc_absx(self):
        tokens = list(lexical('INC $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xfe, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = inx_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class InxTest(unittest.TestCase):

    def test_inx_sngl(self):
        tokens = list(lexical('INX'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe8])

########NEW FILE########
__FILENAME__ = iny_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class InyTest(unittest.TestCase):

    def test_iny_sngl(self):
        tokens = list(lexical('INY'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xc8])

########NEW FILE########
__FILENAME__ = jmp_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class JmpTest(unittest.TestCase):

    def test_jmp_abs(self):
        tokens = list(lexical('JMP $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4c, 0x34, 0x12])

# TODO: http://www.6502.buss.hk/6502-instruction-set/jmp says that there
# is a indirect

########NEW FILE########
__FILENAME__ = joypad_test
# TODO: coding

import unittest

from re import match

from pynes.game import Game, Joypad


class JoypadTest(unittest.TestCase):

    def test_joypad1(self):
        joypad_1 = Joypad(1, Game())
        self.assertFalse(joypad_1.is_used)
        self.assertEquals('', joypad_1.to_asm())

    def test_joypad2(self):
        joypad_2 = Joypad(2, Game())
        self.assertFalse(joypad_2.is_used)
        self.assertEquals('', joypad_2.to_asm())

    def test_joypad1_with_up_event(self):
        game = Game()
        joypad_1 = Joypad(1, game)
        game._asm_chunks['joypad1_up'] = '  LDA $0200\n'
        self.assertTrue(joypad_1.is_used)
        asm = joypad_1.to_asm()
        self.assertTrue('LDA $0200' in asm)
        self.assertTrue('JoyPad1A:' in asm)
        self.assertTrue('JoyPad1B:' in asm)
        self.assertTrue('JoyPad1Select:' in asm)
        self.assertTrue('JoyPad1Start:' in asm)
        self.assertTrue('JoyPad1Up:' in asm)
        self.assertTrue('JoyPad1Down:' in asm)
        self.assertTrue('JoyPad1Left:' in asm)
        self.assertTrue('JoyPad1Right:' in asm)
        self.assertTrue('JoyPad2' not in asm)

########NEW FILE########
__FILENAME__ = jsr_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class JsrTest(unittest.TestCase):

    def test_jsr_abs(self):
        tokens = list(lexical('JSR $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x20, 0x34, 0x12])

# TODO: http://www.6502.buss.hk/6502-instruction-set/jmp says that there
# is a indirect

########NEW FILE########
__FILENAME__ = lda_test
# -*- coding: utf-8 -*-
'''
LDA, Load Accumulator Test

This is one of the Memory Operations in the c6502
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class LdaTest(unittest.TestCase):

    def test_lda_imm(self):
        tokens = list(lexical('LDA #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa9, 0x10])

    def test_lda_imm_with_decimal(self):
        tokens = list(lexical('LDA #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa9, 0x0a])

    def test_lda_imm_with_binary(self):
        tokens = list(lexical('LDA #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa9, 0x04])

    def test_lda_zp(self):
        tokens = list(lexical('LDA $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa5, 0x00])

    def test_lda_zpx(self):
        tokens = list(lexical('LDA $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb5, 0x10])

    def test_lda_abs(self):
        tokens = list(lexical('LDA $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xad, 0x34, 0x12])

    def test_lda_absx(self):
        tokens = list(lexical('LDA $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xbd, 0x34, 0x12])

    def test_lda_absy(self):
        tokens = list(lexical('LDA $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb9, 0x34, 0x12])

    def test_lda_indx(self):
        tokens = list(lexical('LDA ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa1, 0x20])

    def test_lda_indy(self):
        tokens = list(lexical('LDA ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb1, 0x20])

########NEW FILE########
__FILENAME__ = ldx_test
# -*- coding: utf-8 -*-
'''
LDX, Load Register X

This is one of the memory operations on the 6502
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class LdxTest(unittest.TestCase):

    def test_ldx_imm(self):
        tokens = list(lexical('LDX #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa2, 0x10])

    def test_ldx_imm_with_decimal(self):
        tokens = list(lexical('LDX #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa2, 0x0a])

    def test_ldx_imm_with_binary(self):
        tokens = list(lexical('LDX #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa2, 0x04])

    def test_ldx_zp(self):
        tokens = list(lexical('LDX $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa6, 0x00])

    def test_ldx_zpy(self):
        tokens = list(lexical('LDX $10,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb6, 0x10])

    def test_ldx_abs(self):
        tokens = list(lexical('LDX $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xae, 0x34, 0x12])

    def test_ldx_absy(self):
        tokens = list(lexical('LDX $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xbe, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = ldy_test
# -*- coding: utf-8 -*-
'''
LDY, Load Register Y

This is one of the memory operations on the 6502
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class LdyTest(unittest.TestCase):

    def test_ldy_imm(self):
        tokens = list(lexical('LDY #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa0, 0x10])

    def test_ldy_imm_with_decimal(self):
        tokens = list(lexical('LDY #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa0, 0x0a])

    def test_ldy_imm_with_binary(self):
        tokens = list(lexical('LDY #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa0, 0x04])

    def test_ldy_zp(self):
        tokens = list(lexical('LDY $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa4, 0x00])

    def test_ldy_zpx(self):
        tokens = list(lexical('LDY $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xb4, 0x10])

    def test_ldy_abs(self):
        tokens = list(lexical('LDY $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xac, 0x34, 0x12])

    def test_ldy_absx(self):
        tokens = list(lexical('LDY $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xbc, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = lsr_test
# -*- coding: utf-8 -*-
'''
LSR, Logical Shift Right Test

This is an Bit Manipulation operation of the 6502
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class LsrTest(unittest.TestCase):

    def test_lsr_acc(self):
        tokens = list(lexical('LSR A'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ACCUMULATOR', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ACCUMULATOR', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4a])

    def test_lsr_imm(self):
        tokens = list(lexical('LSR #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4a, 0x10])

    def test_lsr_imm_with_decimal(self):
        tokens = list(lexical('LSR #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4a, 0x0a])

    def test_lsr_imm_with_binary(self):
        tokens = list(lexical('LSR #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4a, 0x04])

    def test_lsr_zp(self):
        tokens = list(lexical('LSR $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x46, 0x00])

    def test_lsr_zpx(self):
        tokens = list(lexical('LSR $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x56, 0x10])

    def test_lsr_abs(self):
        tokens = list(lexical('LSR $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x4e, 0x34, 0x12])

    def test_lsr_absx(self):
        tokens = list(lexical('LSR $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x5e, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = movingsprite_test
# -*- coding: utf-8 -*-
from pynes.tests import HexTestCase
from pynes.compiler import lexical, syntax, semantic, get_labels
from pynes.cartridge import Cartridge

# TODO: from pynes.asm import get_var


class MovingSpriteTest(HexTestCase):

    def __init__(self, testname):
        HexTestCase.__init__(self, testname)
        f = open('fixtures/movingsprite/movingsprite.asm')
        code = f.read()
        f.close()
        tokens = lexical(code)
        self.ast = syntax(tokens)

    def test_inesprg_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[0]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[0]['children'][0]['type'])
        self.assertEquals('.inesprg', self.ast[0]['children'][0]['value'])
        self.assertEquals(5, self.ast[0]['children'][0]['line'])
        self.assertEquals(3, self.ast[0]['children'][0]['column'])

    def test_ineschr_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[1]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[1]['children'][0]['type'])
        self.assertEquals('.ineschr', self.ast[1]['children'][0]['value'])
        self.assertEquals(6, self.ast[1]['children'][0]['line'])
        self.assertEquals(3, self.ast[1]['children'][0]['column'])

    def test_inesmap_0(self):
        self.assertEquals('S_DIRECTIVE', self.ast[2]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[2]['children'][0]['type'])
        self.assertEquals('.inesmap', self.ast[2]['children'][0]['value'])
        self.assertEquals(7, self.ast[2]['children'][0]['line'])
        self.assertEquals(3, self.ast[2]['children'][0]['column'])

    def test_inesmir_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[3]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[3]['children'][0]['type'])
        self.assertEquals('.inesmir', self.ast[3]['children'][0]['value'])
        self.assertEquals(8, self.ast[3]['children'][0]['line'])
        self.assertEquals(3, self.ast[3]['children'][0]['column'])

    def test_bank_0(self):
        self.assertEquals('S_DIRECTIVE', self.ast[4]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[4]['children'][0]['type'])
        self.assertEquals('.bank', self.ast[4]['children'][0]['value'])
        self.assertEquals(11, self.ast[4]['children'][0]['line'])
        self.assertEquals(3, self.ast[4]['children'][0]['column'])

    def test_org_c0000(self):
        self.assertEquals('S_DIRECTIVE', self.ast[5]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[5]['children'][0]['type'])
        self.assertEquals('.org', self.ast[5]['children'][0]['value'])
        self.assertEquals(12, self.ast[5]['children'][0]['line'])
        self.assertEquals(3, self.ast[5]['children'][0]['column'])

    def test_waitvblank_bit_2002(self):
        self.assertEquals('S_ABSOLUTE', self.ast[6]['type'])
        self.assertEquals(['WAITVBLANK'], self.ast[6]['labels'])
        self.assertEquals('T_INSTRUCTION', self.ast[6]['children'][0]['type'])
        self.assertEquals('BIT', self.ast[6]['children'][0]['value'])
        self.assertEquals(15, self.ast[6]['children'][0]['line'])
        self.assertEquals(3, self.ast[6]['children'][0]['column'])

    def test_bpl_waitvblank(self):
        self.assertEquals('S_RELATIVE', self.ast[7]['type'])
        self.assertFalse('labels' in self.ast[7])
        self.assertEquals('T_INSTRUCTION', self.ast[7]['children'][0]['type'])
        self.assertEquals('BPL', self.ast[7]['children'][0]['value'])
        self.assertEquals(16, self.ast[7]['children'][0]['line'])
        self.assertEquals(3, self.ast[7]['children'][0]['column'])

    def test_rts(self):
        self.assertEquals('S_IMPLIED', self.ast[8]['type'])
        self.assertFalse('labels' in self.ast[8])
        self.assertEquals('T_INSTRUCTION', self.ast[8]['children'][0]['type'])
        self.assertEquals('RTS', self.ast[8]['children'][0]['value'])
        self.assertEquals(17, self.ast[8]['children'][0]['line'])
        self.assertEquals(3, self.ast[8]['children'][0]['column'])

    def test_asm_compiler(self):
        cart = Cartridge()
        cart.path = 'fixtures/movingsprite/'

        opcodes = semantic(self.ast, True, cart=cart)

        self.assertIsNotNone(opcodes)
        bin = ''.join([chr(opcode) for opcode in opcodes])
        f = open('fixtures/movingsprite/movingsprite.nes', 'rb')
        content = f.read()
        f.close()
        self.assertHexEquals(content, bin)

    def test_get_labels(self):
        expected = {}
        expected['WAITVBLANK'] = 0xC000
        expected['palette'] = 0xE000
        expected['sprites'] = 0xE000 + 32
        actual = get_labels(self.ast)
        self.assertEquals(expected['WAITVBLANK'], actual['WAITVBLANK'])
        self.assertEquals(expected['palette'], actual['palette'])
        self.assertEquals(expected['sprites'], actual['sprites'])

########NEW FILE########
__FILENAME__ = movingsprite_translated_test

from pynes.tests import HexTestCase
from pynes.compiler import lexical, syntax, semantic
from pynes.cartridge import Cartridge

'''
from pynes.examples.movingsprite_translated import game

class MovingSpriteTranslatedTest(HexTestCase):

    def __init__(self, testname):
        super(MovingSpriteTranslatedTest, self).__init__(testname)
        code = game.press_start()
        self.code = code
        tokens = lexical(code)
        self.ast = syntax(tokens)

    def test_inesprg_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[0]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[0]['children'][0]['type'])
        self.assertEquals('.inesprg', self.ast[0]['children'][0]['value'])

    def test_ineschr_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[1]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[1]['children'][0]['type'])
        self.assertEquals('.ineschr', self.ast[1]['children'][0]['value'])

    def test_inesmap_0(self):
        self.assertEquals('S_DIRECTIVE', self.ast[2]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[2]['children'][0]['type'])
        self.assertEquals('.inesmap', self.ast[2]['children'][0]['value'])

    def test_inesmir_1(self):
        self.assertEquals('S_DIRECTIVE', self.ast[3]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[3]['children'][0]['type'])
        self.assertEquals('.inesmir', self.ast[3]['children'][0]['value'])

    def test_bank_0(self):
        self.assertEquals('S_DIRECTIVE', self.ast[4]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[4]['children'][0]['type'])
        self.assertEquals('.bank', self.ast[4]['children'][0]['value'])

    def test_org_c0000(self):
        self.assertEquals('S_DIRECTIVE', self.ast[5]['type'])
        self.assertEquals('T_DIRECTIVE', self.ast[5]['children'][0]['type'])
        self.assertEquals('.org', self.ast[5]['children'][0]['value'])

    def test_waitvblank_bit_2002(self):
        self.assertEquals('S_ABSOLUTE', self.ast[6]['type'])
        self.assertEquals(['WAITVBLANK'], self.ast[6]['labels'])
        self.assertEquals('T_INSTRUCTION', self.ast[6]['children'][0]['type'])
        self.assertEquals('BIT', self.ast[6]['children'][0]['value'])

    def test_bpl_waitvblank(self):
        self.assertEquals('S_RELATIVE', self.ast[7]['type'])
        self.assertFalse('labels' in self.ast[7])
        self.assertEquals('T_INSTRUCTION', self.ast[7]['children'][0]['type'])
        self.assertEquals('BPL', self.ast[7]['children'][0]['value'])

    def test_rts(self):
        self.assertEquals('S_IMPLIED', self.ast[8]['type'])
        self.assertFalse('labels' in self.ast[8])
        self.assertEquals('T_INSTRUCTION', self.ast[8]['children'][0]['type'])
        self.assertEquals('RTS', self.ast[8]['children'][0]['value'])


    def test_asm_compiler(self):
        cart = Cartridge()
        cart.path = 'fixtures/movingsprite/'

        opcodes = semantic(self.ast, True, cart=cart)

        self.assertIsNotNone(opcodes)
        bin = ''.join([chr(opcode) for opcode in opcodes])
        with open('fixtures/movingsprite/movingsprite.nes', 'rb') as f:
            content = f.read()
        #TOSO self.assertHexEquals(content,bin)
'''

########NEW FILE########
__FILENAME__ = nametable_test
# -*- coding: utf-8 -*-

import unittest

from pynes import nametable


class NametableTest(unittest.TestCase):

    def setUp(self):
        self.nt = nametable.load_nametable(
            'fixtures/nerdynights/scrolling/SMBlevel.bin')
        self.assertIsNotNone(self.nt)

    def test_length_nametable(self):
        length = nametable.length(self.nt)
        self.assertEquals(4, length)

    def test_get_nametable(self):
        return
        # length = nametable.get_nametable(1, self.nt)
        # self.assertEquals(4, length)

########NEW FILE########
__FILENAME__ = nop_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class NopTest(unittest.TestCase):

    def test_nop_sngl(self):
        tokens = list(lexical('NOP'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xea])

########NEW FILE########
__FILENAME__ = ora_test
# -*- coding: utf-8 -*-
'''
ORA, OR with Accumulator Test

This is an Logical operation of the 6502
'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class OraTest(unittest.TestCase):

    '''Test logical OR operation between $10 (Decimal 16) and the
    content of the Accumulator'''

    def test_ora_imm(self):
        tokens = list(lexical('ORA #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x09, 0x10])

    '''Test logical OR operation between #10 (Decimal 10) and the
    content of the Accumulator'''

    def test_ora_imm_with_decimal(self):
        tokens = list(lexical('ORA #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x09, 0x0a])

    '''Test logical OR operation between binary #%00000100
    (Decimal 4) and the content of the Accumulator'''

    def test_ora_imm_with_binary(self):
        tokens = list(lexical('ORA #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x09, 0x04])

    '''Test logical OR operation between the content of the
    Accumulator and the content of zero page $00'''

    def test_ora_zp(self):
        tokens = list(lexical('ORA $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x05, 0x00])

    def test_ora_zpx(self):
        tokens = list(lexical('ORA $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x15, 0x10])

    def test_ora_abs(self):
        tokens = list(lexical('ORA $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x0d, 0x34, 0x12])

    def test_ora_absx(self):
        tokens = list(lexical('ORA $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x1d, 0x34, 0x12])

    def test_ora_absy(self):
        tokens = list(lexical('ORA $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x19, 0x34, 0x12])

    def test_ora_indx(self):
        tokens = list(lexical('ORA ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x01, 0x20])

    def test_ora_indy(self):
        tokens = list(lexical('ORA ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x11, 0x20])

########NEW FILE########
__FILENAME__ = pha_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class PhaTest(unittest.TestCase):

    def test_pha_sngl(self):
        tokens = list(lexical('PHA'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x48])

########NEW FILE########
__FILENAME__ = php_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class PhpTest(unittest.TestCase):

    def test_php_sngl(self):
        tokens = list(lexical('PHP'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x08])

########NEW FILE########
__FILENAME__ = pla_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class PlaTest(unittest.TestCase):

    def test_pla_sngl(self):
        tokens = list(lexical('PLA'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x68])

########NEW FILE########
__FILENAME__ = plp_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class PlpTest(unittest.TestCase):

    def test_plp_sngl(self):
        tokens = list(lexical('PLP'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x28])

########NEW FILE########
__FILENAME__ = ppu_test
import unittest

from pynes.game import PPU


class PPUTest(unittest.TestCase):

    def setUp(self):
        self.ppu = PPU()

    def tearDown(self):
        self.ppu = None

    def test_ppu_toogle_nmi(self):
        self.assertEquals(0b00000000, self.ppu.ctrl)
        self.ppu.nmi_enable = True
        self.assertEquals(0b10000000, self.ppu.ctrl)
        self.assertEquals(True, self.ppu.nmi_enable)
        self.ppu.nmi_enable = False
        self.assertEquals(0b00000000, self.ppu.ctrl)
        self.assertEquals(False, self.ppu.nmi_enable)

    def test_ppu_toogle_sprite_table(self):
        return
        self.assertEquals(0b00000000, self.ppu.ctrl)
        self.ppu.sprite_pattern_table = 1
        self.assertEquals(0b00001000, self.ppu.ctrl)
        self.ppu.sprite_pattern_table = 0
        self.assertEquals(0b00000000, self.ppu.ctrl)

    def test_ppu_toogle_background_table(self):
        return
        self.assertEquals(0b00000000, self.ppu.ctrl)
        self.ppu.background_pattern_table = 1
        self.assertEquals(0b00010000, self.ppu.ctrl)
        self.ppu.background_pattern_table = 0
        self.assertEquals(0b00000000, self.ppu.ctrl)

    def test_ppu_toogle_sprite(self):
        self.assertEquals(0b00000000, self.ppu.mask)
        self.ppu.sprite_enable = True
        self.assertEquals(0b00010000, self.ppu.mask)
        self.assertEquals(True, self.ppu.sprite_enable)
        self.ppu.sprite_enable = False
        self.assertEquals(0b00000000, self.ppu.mask)
        self.assertEquals(False, self.ppu.sprite_enable)

    def test_ppu_toogle_background(self):
        self.assertEquals(0b00000000, self.ppu.mask)
        self.ppu.background_enable = True
        self.assertEquals(0b00001000, self.ppu.mask)
        self.assertEquals(True, self.ppu.background_enable)
        self.ppu.background_enable = False
        self.assertEquals(0b00000000, self.ppu.mask)
        self.assertEquals(False, self.ppu.background_enable)

    def test_ppu_toogle_background2(self):
        self.assertEquals(0b00000000, self.ppu.ctrl)
        self.assertEquals(0b00000000, self.ppu.mask)
        self.ppu.nmi_enable = True
        self.ppu.sprite_enable = True
        self.assertEquals(0b10000000, self.ppu.ctrl)
        self.assertEquals(True, self.ppu.nmi_enable)
        self.assertEquals(0b00010000, self.ppu.mask)
        self.assertEquals(True, self.ppu.sprite_enable)

########NEW FILE########
__FILENAME__ = rol_test
# -*- coding: utf-8 -*-
'''
ROL, Rotate Left Test

This is an Bit Manipulation of the 6502.

'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class RolTest(unittest.TestCase):

    def test_rol_imm(self):
        tokens = list(lexical('ROL #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2a, 0x10])

    def test_rol_imm_with_decimal(self):
        tokens = list(lexical('ROL #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2a, 0x0a])

    def test_rol_imm_with_binary(self):
        tokens = list(lexical('ROL #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2a, 0x04])

    def test_rol_zp(self):
        tokens = list(lexical('ROL $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x26, 0x00])

    def test_rol_zpx(self):
        tokens = list(lexical('ROL $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x36, 0x10])

    def test_rol_abs(self):
        tokens = list(lexical('ROL $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x2e, 0x34, 0x12])

    def test_rol_absx(self):
        tokens = list(lexical('ROL $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x3e, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = ror_test
# -*- coding: utf-8 -*-
'''
ROR, Rotate Right Test

This is an Bit Manipulation of the 6502.

'''

import unittest

from pynes.compiler import lexical, syntax, semantic


class RorTest(unittest.TestCase):

    def test_ror_imm(self):
        tokens = list(lexical('ROR #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x6a, 0x10])

    def test_ror_imm_with_decimal(self):
        tokens = list(lexical('ROR #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x6a, 0x0a])

    def test_ror_imm_with_binary(self):
        tokens = list(lexical('ROR #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x6a, 0x04])

    def test_ror_zp(self):
        tokens = list(lexical('ROR $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x66, 0x00])

    def test_ror_zpx(self):
        tokens = list(lexical('ROR $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x76, 0x10])

    def test_ror_abs(self):
        tokens = list(lexical('ROR $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x6e, 0x34, 0x12])

    def test_ror_absx(self):
        tokens = list(lexical('ROR $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x7e, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = rti_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class RtiTest(unittest.TestCase):

    def test_rti_sngl(self):
        tokens = list(lexical('RTI'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x40])

########NEW FILE########
__FILENAME__ = rts_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class RtsTest(unittest.TestCase):

    def test_rts_sngl(self):
        tokens = list(lexical('RTS'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x60])

########NEW FILE########
__FILENAME__ = sbc_test
# -*- coding: utf-8 -*-
'''
SBC, Subtract with Carry Test

This is an arithmetic instruction of the 6502.
'''
import unittest

from pynes.compiler import lexical, syntax, semantic


class SbcTest(unittest.TestCase):

    def test_sbc_imm(self):
        tokens = list(lexical('SBC #$10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_HEX_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe9, 0x10])

    def test_sbc_imm_with_decimal(self):
        tokens = list(lexical('SBC #10'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_DECIMAL_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe9, 0x0a])

    def test_sbc_imm_with_binary(self):
        tokens = list(lexical('SBC #%00000100'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_BINARY_NUMBER', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMMEDIATE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe9, 0x04])

    def test_sbc_zp(self):
        tokens = list(lexical('SBC $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe5, 0x00])

    def test_sbc_zpx(self):
        tokens = list(lexical('SBC $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf5, 0x10])

    def test_sbc_abs(self):
        tokens = list(lexical('SBC $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xed, 0x34, 0x12])

    def test_sbc_absx(self):
        tokens = list(lexical('SBC $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xfd, 0x34, 0x12])

    def test_sbc_absy(self):
        tokens = list(lexical('SBC $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf9, 0x34, 0x12])

    def test_sbc_indx(self):
        tokens = list(lexical('SBC ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xe1, 0x20])

    def test_sbc_indy(self):
        tokens = list(lexical('SBC ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf1, 0x20])

########NEW FILE########
__FILENAME__ = scrolling_test
# -*- coding: utf-8 -*-

import unittest

import pynes

from pynes.tests import HexTestCase
from pynes.compiler import lexical, syntax, semantic
from pynes.cartridge import Cartridge


class ScrollingTest(HexTestCase):

    def __init__(self, testname):
        HexTestCase.__init__(self, testname)

    def assertAsmResults(self, source_file, bin_file):
        path = 'fixtures/nerdynights/scrolling/'
        f = open(path + source_file)
        code = f.read()
        f.close()
        tokens = lexical(code)
        ast = syntax(tokens)

        cart = Cartridge()
        cart.path = 'fixtures/nerdynights/scrolling/'

        opcodes = semantic(ast, True, cart=cart)

        self.assertIsNotNone(opcodes)
        bin = ''.join([chr(opcode) for opcode in opcodes])
        f = open(path + bin_file, 'rb')
        content = f.read()
        f.close()
        self.assertHexEquals(content, bin)

    def test_asm_compiler_scrolling_1(self):
        self.assertAsmResults('scrolling1.asm', 'scrolling1.nes')

    def test_asm_compiler_scrolling_2(self):
        self.assertAsmResults('scrolling2.asm', 'scrolling2.nes')

    def test_asm_compiler_scrolling_3(self):
        self.assertAsmResults('scrolling3.asm', 'scrolling3.nes')

    def test_asm_compiler_scrolling_4(self):
        self.assertAsmResults('scrolling4.asm', 'scrolling4.nes')

########NEW FILE########
__FILENAME__ = sec_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class SecTest(unittest.TestCase):

    def test_sec_sngl(self):
        tokens = list(lexical('SEC'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x38])

########NEW FILE########
__FILENAME__ = sed_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class SedTest(unittest.TestCase):

    def test_sed_sngl(self):
        tokens = list(lexical('SED'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xf8])

########NEW FILE########
__FILENAME__ = sei_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class SeiTest(unittest.TestCase):

    def test_sei_sngl(self):
        tokens = list(lexical('SEI'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x78])

########NEW FILE########
__FILENAME__ = spriteset_test
import unittest


from pynes.sprite import SpriteSet


class SpriteTest(unittest.TestCase):

    def __init__(self, testcase_name):
        unittest.TestCase.__init__(self, testcase_name)
        f = open('fixtures/nerdynights/scrolling/mario.chr', 'rb')
        content = f.read()
        self.bin = [ord(c) for c in content]

        self.mario1 = [
            [0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 3, 3, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 3, 2],
            [0, 3, 3, 2, 2, 3, 3, 2]
        ]

        self.mario2 = [
            [1, 1, 1, 0, 0, 0, 0, 0],
            [1, 1, 2, 0, 0, 0, 0, 0],
            [1, 2, 2, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 0, 0],
            [3, 2, 2, 2, 0, 0, 0, 0],
            [3, 3, 2, 2, 2, 2, 0, 0],
            [2, 2, 2, 2, 2, 2, 2, 0],
            [2, 2, 3, 2, 2, 2, 2, 0]
        ]

    def test_spriteset(self):
        sprites = SpriteSet('fixtures/nerdynights/scrolling/mario.chr')
        self.assertEquals(self.bin, sprites.sprs)
        self.assertEquals(self.mario1, sprites.get(0))
        self.assertEquals(self.mario2, sprites.get(1))

        self.assertEquals(0, sprites.has_sprite(self.mario1))
        self.assertEquals(1, sprites.has_sprite(self.mario2))

########NEW FILE########
__FILENAME__ = sprite_test
# -*- coding: utf-8 -*-

import unittest

from pynes import sprite


class SpriteTest(unittest.TestCase):

    def __init__(self, testcase_name):
        unittest.TestCase.__init__(self, testcase_name)
        f = open('fixtures/nerdynights/scrolling/mario.chr', 'rb')
        content = f.read()
        self.bin = [ord(c) for c in content]

        self.mario1 = [
            [0, 0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 1, 1, 1, 1, 1],
            [0, 0, 0, 3, 3, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 2, 2],
            [0, 0, 3, 2, 2, 3, 3, 2],
            [0, 3, 3, 2, 2, 3, 3, 2]
        ]

        self.mario2 = [
            [1, 1, 1, 0, 0, 0, 0, 0],
            [1, 1, 2, 0, 0, 0, 0, 0],
            [1, 2, 2, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 0, 0],
            [3, 2, 2, 2, 0, 0, 0, 0],
            [3, 3, 2, 2, 2, 2, 0, 0],
            [2, 2, 2, 2, 2, 2, 2, 0],
            [2, 2, 3, 2, 2, 2, 2, 0]
        ]

        self.blank = [
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0]
        ]

    def test_load_sprites(self):
        sprites = sprite.load_sprites(
            'fixtures/nerdynights/scrolling/mario.chr')
        self.assertEquals(self.bin, sprites)

    def test_decode_first_sprite(self):
        channelA = self.bin[0:8]
        channelB = self.bin[8:16]
        s1 = sprite.decode_sprite(channelA, channelB)
        self.assertEquals(self.mario1, s1)

    def test_decode_second_sprite(self):
        channelA = self.bin[16:24]
        channelB = self.bin[24:32]

        s2 = sprite.decode_sprite(channelA, channelB)
        self.assertEquals(self.mario2, s2)

    def test_get_first_sprite(self):
        s1 = sprite.get_sprite(0, self.bin)
        self.assertEquals(self.mario1, s1)

    def test_get_second_sprite(self):
        s2 = sprite.get_sprite(1, self.bin)
        self.assertEquals(self.mario2, s2)

    def test_sprite_length(self):
        length = sprite.length(self.bin)
        self.assertEquals(512, length)

    def test_encode_first_sprite(self):
        encoded = sprite.encode_sprite(self.mario1)
        expected = self.bin[0:16]
        self.assertEquals(expected, encoded)

    def test_encode_second_sprite(self):
        encoded = sprite.encode_sprite(self.mario2)
        expected = self.bin[16:32]
        self.assertEquals(expected, encoded)

    def test_put_first_sprite(self):
        expected = [
            [0, 1, 2, 3, 0, 1, 2, 3],
            [1, 0, 1, 2, 3, 0, 1, 2],
            [2, 1, 0, 1, 2, 3, 0, 1],
            [3, 2, 1, 0, 1, 2, 3, 0],
            [0, 3, 2, 1, 0, 1, 2, 3],
            [1, 0, 3, 2, 1, 0, 1, 2],
            [2, 1, 0, 3, 2, 1, 0, 1],
            [3, 2, 1, 0, 3, 2, 1, 0]
        ]
        sprite.put_sprite(0, self.bin, expected)
        s1 = sprite.get_sprite(0, self.bin)
        self.assertEquals(expected, s1)

    def test_put_second_sprite(self):
        expected = [
            [0, 1, 2, 3, 0, 1, 2, 3],
            [1, 0, 1, 2, 3, 0, 1, 2],
            [2, 1, 0, 1, 2, 3, 0, 1],
            [3, 2, 1, 0, 1, 2, 3, 0],
            [0, 3, 2, 1, 0, 1, 2, 3],
            [1, 0, 3, 2, 1, 0, 1, 2],
            [2, 1, 0, 3, 2, 1, 0, 1],
            [3, 2, 1, 0, 3, 2, 1, 0]
        ]
        sprite.put_sprite(1, self.bin, expected)
        s1 = sprite.get_sprite(1, self.bin)
        self.assertEquals(expected, s1)

    def test_find_sprite_1(self):
        index = sprite.find_sprite(self.bin, self.mario1)
        self.assertEquals(0, index)

    def test_find_sprite_2(self):
        index = sprite.find_sprite(self.bin, self.mario2)
        self.assertEquals(1, index)

    def test_find_sprite_3(self):
        index = sprite.find_sprite(self.bin, self.blank, 256)
        self.assertEquals(292 - 256, index)

########NEW FILE########
__FILENAME__ = sta_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class StaTest(unittest.TestCase):

    def test_sta_zp(self):
        tokens = list(lexical('STA $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x85, 0x00])

    def test_sta_zpx(self):
        tokens = list(lexical('STA $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x95, 0x10])

    def test_sta_abs(self):
        tokens = list(lexical('STA $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x8D, 0x34, 0x12])

    def test_sta_absx(self):
        tokens = list(lexical('STA $1234,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x9D, 0x34, 0x12])

    def test_sta_absy(self):
        tokens = list(lexical('STA $1234,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x99, 0x34, 0x12])

    def test_sta_indx(self):
        tokens = list(lexical('STA ($20,X)'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('$20', tokens[2]['value'])
        self.assertEquals('T_SEPARATOR', tokens[3]['type'])
        self.assertEquals('T_REGISTER', tokens[4]['type'])
        self.assertEquals('T_CLOSE', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x81, 0x20])

    def test_sta_indy(self):
        tokens = list(lexical('STA ($20),Y'))
        self.assertEquals(6, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_OPEN', tokens[1]['type'])
        self.assertEquals('T_ADDRESS', tokens[2]['type'])
        self.assertEquals('T_CLOSE', tokens[3]['type'])
        self.assertEquals('T_SEPARATOR', tokens[4]['type'])
        self.assertEquals('T_REGISTER', tokens[5]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_INDIRECT_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x91, 0x20])

########NEW FILE########
__FILENAME__ = stx_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class StxTest(unittest.TestCase):

    def test_stx_zp(self):
        tokens = list(lexical('STX $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x86, 0x00])

    def test_stx_zpy(self):
        tokens = list(lexical('STX $10,Y'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_Y', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x96, 0x10])

    def test_stx_abs(self):
        tokens = list(lexical('STX $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x8e, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = sty_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class StyTest(unittest.TestCase):

    def test_sty_zp(self):
        tokens = list(lexical('STY $00'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x84, 0x00])

    def test_sty_zpx(self):
        tokens = list(lexical('STY $10,X'))
        self.assertEquals(4, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('T_SEPARATOR', tokens[2]['type'])
        self.assertEquals('T_REGISTER', tokens[3]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ZEROPAGE_X', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x94, 0x10])

    def test_sty_abs(self):
        tokens = list(lexical('STY $1234'))
        self.assertEquals(2, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        self.assertEquals('T_ADDRESS', tokens[1]['type'])
        self.assertEquals('$1234', tokens[1]['value'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_ABSOLUTE', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x8c, 0x34, 0x12])

########NEW FILE########
__FILENAME__ = tax_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class TaxTest(unittest.TestCase):

    def test_tax_sngl(self):
        tokens = list(lexical('TAX'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xaa])

########NEW FILE########
__FILENAME__ = tay_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class TayTest(unittest.TestCase):

    def test_tay_sngl(self):
        tokens = list(lexical('TAY'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xa8])

########NEW FILE########
__FILENAME__ = tsx_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class TsxTest(unittest.TestCase):

    def test_tsx_sngl(self):
        tokens = list(lexical('TSX'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0xba])

########NEW FILE########
__FILENAME__ = txa_test
# -*- coding: utf-8 -*-

import unittest

from pynes.compiler import lexical, syntax, semantic


class TxaTest(unittest.TestCase):

    def test_txa_sngl(self):
        tokens = list(lexical('TXA'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x8a])

########NEW FILE########
__FILENAME__ = tya_test
# -*- coding: utf-8 -*-
import unittest

from pynes.compiler import lexical, syntax, semantic


class TyaTest(unittest.TestCase):

    def test_tya_sngl(self):
        tokens = list(lexical('TYA'))
        self.assertEquals(1, len(tokens))
        self.assertEquals('T_INSTRUCTION', tokens[0]['type'])
        ast = syntax(tokens)
        self.assertEquals(1, len(ast))
        self.assertEquals('S_IMPLIED', ast[0]['type'])
        code = semantic(ast)
        self.assertEquals(code, [0x98])

########NEW FILE########
