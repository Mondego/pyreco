__FILENAME__ = affineCipher
# Affine Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import sys, pyperclip, cryptomath, random
SYMBOLS = """ !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~""" # note the space at the front


def main():
    myMessage = """"A computer would deserve to be called intelligent if it could deceive a human into believing that it was human." -Alan Turing"""
    myKey = 2023
    myMode = 'encrypt' # set to 'encrypt' or 'decrypt'

    if myMode == 'encrypt':
        translated = encryptMessage(myKey, myMessage)
    elif myMode == 'decrypt':
        translated = decryptMessage(myKey, myMessage)
    print('Key: %s' % (myKey))
    print('%sed text:' % (myMode.title()))
    print(translated)
    pyperclip.copy(translated)
    print('Full %sed text copied to clipboard.' % (myMode))


def getKeyParts(key):
    keyA = key // len(SYMBOLS)
    keyB = key % len(SYMBOLS)
    return (keyA, keyB)


def checkKeys(keyA, keyB, mode):
    if keyA == 1 and mode == 'encrypt':
        sys.exit('The affine cipher becomes incredibly weak when key A is set to 1. Choose a different key.')
    if keyB == 0 and mode == 'encrypt':
        sys.exit('The affine cipher becomes incredibly weak when key B is set to 0. Choose a different key.')
    if keyA < 0 or keyB < 0 or keyB > len(SYMBOLS) - 1:
        sys.exit('Key A must be greater than 0 and Key B must be between 0 and %s.' % (len(SYMBOLS) - 1))
    if cryptomath.gcd(keyA, len(SYMBOLS)) != 1:
        sys.exit('Key A (%s) and the symbol set size (%s) are not relatively prime. Choose a different key.' % (keyA, len(SYMBOLS)))


def encryptMessage(key, message):
    keyA, keyB = getKeyParts(key)
    checkKeys(keyA, keyB, 'encrypt')
    ciphertext = ''
    for symbol in message:
        if symbol in SYMBOLS:
            # encrypt this symbol
            symIndex = SYMBOLS.find(symbol)
            ciphertext += SYMBOLS[(symIndex * keyA + keyB) % len(SYMBOLS)]
        else:
            ciphertext += symbol # just append this symbol unencrypted
    return ciphertext


def decryptMessage(key, message):
    keyA, keyB = getKeyParts(key)
    checkKeys(keyA, keyB, 'decrypt')
    plaintext = ''
    modInverseOfKeyA = cryptomath.findModInverse(keyA, len(SYMBOLS))

    for symbol in message:
        if symbol in SYMBOLS:
            # decrypt this symbol
            symIndex = SYMBOLS.find(symbol)
            plaintext += SYMBOLS[(symIndex - keyB) * modInverseOfKeyA % len(SYMBOLS)]
        else:
            plaintext += symbol # just append this symbol undecrypted
    return plaintext


def getRandomKey():
    while True:
        keyA = random.randint(2, len(SYMBOLS))
        keyB = random.randint(2, len(SYMBOLS))
        if cryptomath.gcd(keyA, len(SYMBOLS)) == 1:
            return keyA * len(SYMBOLS) + keyB


# If affineCipher.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = affineHacker
# Affine Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip, affineCipher, detectEnglish, cryptomath

SILENT_MODE = False

def main():
    # You might want to copy & paste this text from the source code at
    # http://invpy.com/affineHacker.py
    myMessage = """U&'<3dJ^Gjx'-3^MS'Sj0jxuj'G3'%j'<mMMjS'g{GjMMg9j{G'g"'gG'<3^MS'Sj<jguj'm'P^dm{'g{G3'%jMgjug{9'GPmG'gG'-m0'P^dm{LU'5&Mm{'_^xg{9"""

    hackedMessage = hackAffine(myMessage)

    if hackedMessage != None:
        # The plaintext is displayed on the screen. For the convenience of
        # the user, we copy the text of the code to the clipboard.
        print('Copying hacked message to clipboard:')
        print(hackedMessage)
        pyperclip.copy(hackedMessage)
    else:
        print('Failed to hack encryption.')


def hackAffine(message):
    print('Hacking...')

    # Python programs can be stopped at any time by pressing Ctrl-C (on
    # Windows) or Ctrl-D (on Mac and Linux)
    print('(Press Ctrl-C or Ctrl-D to quit at any time.)')

    # brute-force by looping through every possible key
    for key in range(len(affineCipher.SYMBOLS) ** 2):
        keyA = affineCipher.getKeyParts(key)[0]
        if cryptomath.gcd(keyA, len(affineCipher.SYMBOLS)) != 1:
            continue

        decryptedText = affineCipher.decryptMessage(key, message)
        if not SILENT_MODE:
            print('Tried Key %s... (%s)' % (key, decryptedText[:40]))

        if detectEnglish.isEnglish(decryptedText):
            # Check with the user if the decrypted key has been found.
            print()
            print('Possible encryption hack:')
            print('Key: %s' % (key))
            print('Decrypted message: ' + decryptedText[:200])
            print()
            print('Enter D for done, or just press Enter to continue hacking:')
            response = input('> ')

            if response.strip().upper().startswith('D'):
                return decryptedText
    return None


# If affineHacker.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = affineKeyTest
# This program proves that the keyspace of the affine cipher is limited
# to len(SYMBOLS) ^ 2.

import affineCipher, cryptomath

message = 'Make things as simple as possible, but not simpler.'
for keyA in range(2, 100):
    key = keyA * len(affineCipher.SYMBOLS) + 1

    if cryptomath.gcd(keyA, len(affineCipher.SYMBOLS)) == 1:
        print(keyA, affineCipher.encryptMessage(key, message))
########NEW FILE########
__FILENAME__ = buggy
import random
number1 = random.randint(1, 10)
number2 = random.randint(1, 10)
print('What is ' + str(number1) + ' + ' + str(number2) + '?')
answer = input('> ')
if answer == number1 + number2:
    print('Correct!')
else:
    print('Nope! The answer is ' + str(number1 + number2))
########NEW FILE########
__FILENAME__ = caesarCipher
# Caesar Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip

# the string to be encrypted/decrypted
message = 'This is my secret message.'

# the encryption/decryption key
key = 13

# tells the program to encrypt or decrypt
mode = 'encrypt' # set to 'encrypt' or 'decrypt'

# every possible symbol that can be encrypted
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# stores the encrypted/decrypted form of the message
translated = ''

# capitalize the string in message
message = message.upper()

# run the encryption/decryption code on each symbol in the message string
for symbol in message:
    if symbol in LETTERS:
        # get the encrypted (or decrypted) number for this symbol
        num = LETTERS.find(symbol) # get the number of the symbol
        if mode == 'encrypt':
            num = num + key
        elif mode == 'decrypt':
            num = num - key

        # handle the wrap-around if num is larger than the length of
        # LETTERS or less than 0
        if num >= len(LETTERS):
            num = num - len(LETTERS)
        elif num < 0:
            num = num + len(LETTERS)

        # add encrypted/decrypted number's symbol at the end of translated
        translated = translated + LETTERS[num]

    else:
        # just add the symbol without encrypting/decrypting
        translated = translated + symbol

# print the encrypted/decrypted string to the screen
print(translated)

# copy the encrypted/decrypted string to the clipboard
pyperclip.copy(translated)
########NEW FILE########
__FILENAME__ = caesarCipher2
# Caesar Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip

# the string to be encrypted/decrypted
message = 'This is my secret message.'

# the encryption/decryption key
key = 13

# tells the program to encrypt or decrypt
mode = 'encrypt' # set to 'encrypt' or 'decrypt'

# every possible symbol that can be encrypted
LETTERS = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'

# stores the encrypted/decrypted form of the message
translated = ''

# capitalize the string in message
#message = message.upper()

# run the encryption/decryption code on each symbol in the message string
for symbol in message:
    if symbol in LETTERS:
        # get the encrypted (or decrypted) number for this symbol
        num = LETTERS.find(symbol) # get the number of the symbol
        if mode == 'encrypt':
            num = num + key
        elif mode == 'decrypt':
            num = num - key

        # handle the wrap-around if num is larger than the length of
        # LETTERS or less than 0
        if num >= len(LETTERS):
            num = num - len(LETTERS)
        elif num < 0:
            num = num + len(LETTERS)

        # add encrypted/decrypted number's symbol at the end of translated
        translated = translated + LETTERS[num]

    else:
        # just add the symbol without encrypting/decrypting
        translated = translated + symbol

# print the encrypted/decrypted string to the screen
print(translated)

# copy the encrypted/decrypted string to the clipboard
pyperclip.copy(translated)
########NEW FILE########
__FILENAME__ = caesarHacker
# Caesar Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

message = 'GUVF VF ZL FRPERG ZRFFNTR.'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# loop through every possible key
for key in range(len(LETTERS)):

    # It is important to set translated to the blank string so that the
    # previous iteration's value for translated is cleared.
    translated = ''

    # The rest of the program is the same as the original Caesar program:

    # run the encryption/decryption code on each symbol in the message
    for symbol in message:
        if symbol in LETTERS:
            num = LETTERS.find(symbol) # get the number of the symbol
            num = num - key

            # handle the wrap-around if num is 26 or larger or less than 0
            if num < 0:
                num = num + len(LETTERS)

            # add number's symbol at the end of translated
            translated = translated + LETTERS[num]

        else:
            # just add the symbol without encrypting/decrypting
            translated = translated + symbol

    # display the current key being tested, along with its decryption
    print('Key #%s: %s' % (key, translated))
########NEW FILE########
__FILENAME__ = codebreaker_unit_tests
import unittest, subprocess, pyperclip, hashlib, os, sys, io, random, shutil

# You can download pyperclip from:
# http://coffeeghost.net/src/pyperclip.py

# To install Pylint, download the three following files:
# http://pypi.python.org/packages/source/l/logilab-common/logilab-common-0.58.1.tar.gz#md5=77298ab2d8bb8b4af9219791e7cee8ce
# http://pypi.python.org/packages/source/l/logilab-astng/logilab-astng-0.24.0.tar.gz#md5=295bdb2165657ad4b973b3fae1c95f12
# http://pypi.python.org/packages/source/p/pylint/pylint-0.25.2.tar.gz#md5=d878d7688a4f5290dc5b53a836872400
#
# These are the pylint, logilab-astng, and logilab-common modules.
# Install them by running "python setup.py install" (using the Python32 python.exe or some other Python 3 interpreter) from inside the unzipped folders of each of the three modules.
#
# The pylint module needed to be run with "python setup.py install --no-compile" to work (it had some "encoding could not be found" error)
#
# I created a run_tests.bat batch file with this for content:
# @c:\Python32\python.exe c:\Python32\Lib\site-packages\pylint\lint.py --rcfile=pylint.conf %1 %2 %3 %4 %5 %6 %7 %8 %9
#
# This way I could run "run_pylint.bat foo.py" to run pylint on a source code file.
# Be sure to download the pylint.conf config file and have it in the same folderas codebreaker_unit_tests.py


FOX_MESSAGE = "The quick brown fox jumped over the yellow lazy dog.".upper()
ENGLISH_SENTENCES = """I promised her a delicious dinner.
Tony made him some coffee.
That singer granted him his wish.
Those guards offer her some money.
That barber read the children a story.
That pilot told her the shortest way.
They give him a book.
That barber brings her some perfume.
That teacher pays him this salary.
Those librarians left her a ticket.
I told them a joke.
They write her a letter.
Those news announcers saved her a seat.
I read the children a story.
They promise her a delicious dinner.
Ginger tells them many lies.
John showed them a photograph.
I left her a ticket.
I read the children a story.
I teach them English.
I asked him a question.
They gave him a book.
Into the circuitry speculates her therapy.
That news announcer gives him a magazine.
They ordered her a new dress.
They sold him a ticket.
A folded master influences the content apathy.
They have him drive.
Does every drum offer a driven foot?
Can the convict secure the gulf?
They called him a taxi.
How can a roof disappear?
Dick found the book interesting.
When can the subsidiary officer unite the gesture?
They find the box empty.
The remedy originates outside the guide!
Those cashiers heard the girl crying.
They tried to pieces of the underlying Unix Haters mailing list for the older Arpanet; stuff at the disk and whimpers, Gee, are cascading over your recent versions of several dimensions, and little toy machines a generally suggested that that sexual encounters my knowledge of Line.
Rob how to take over to lanning the extra little feature and, the are real time for free space and just those too typical of them. Not something else it.
And so maybe maybe I substitute this a small publishing. Here rarely log in hardware and on the top, of Unix trade shows you think to be much, about how to be loaded, version of acid and have could sided with to. If I When we can be some of a very well, sort; of whom Not is series I wanted who, was not a Null The basic. Thomas or something else could figure give the above would. Annoyed at all the point the end message to control for beta and users log in Unix and retraction, Since only be mov strstr strstr clr strstr mov strstr be: prepared for that packets can to get At one of.
In years, when the various useless. Hmmm; that's right out that Solaris drove them and it works? Aaaiiiiiigghhhhhhh!
Unix internals to simply not written and Bsd on your mailboxes; mail; delivery still waiting for some utilities used punished. This option was an encryption is intolerable on making Life most recently Received have cat process and I've just gone.
To say we do you are native Macintosh any zero. The difference between failures every copy of U so it would have anything which brings the morbidly curious asymmetry that, bring having to do have to another It Already almost useless gibberish to body that's not to put up some when telnetting to wait! Well; deserved day unless you pull the apparently to a server situation evokes a Grand Exalted DNS resolution to happen to me us; here refer to track when that it to use the problem but lofty, political ideals (and now I'll have gotten it seems entirely and portable assembler that either stdout: and a result really a function prototypes must accept any use rehash and converts it appears that are most of any design).
I know! Well reasonable people we can't get some brief has to. It's bitching about sendmail happily hacking with fudge Join the best so you're to assume that I have other than point to recover or even IBM terminal? Just another flame to search for at the executable: after direction. If (you have some fields may have real deadling it's unix box of the and C construct the power maybe not the Smtp mail envelope: was Always must have to bounce in the output: that acts like Tcp gateway machine I read it gives you a couple of The suggestions but some weasle finds its Unix time it from the stdio library then winding up in Or strictly with me back through the file failed to have a complete and it's your cshrc).
With television while finishing production: of the for improving Financial freedom At the sponsors or cordless phone Number: Tel. Now, is A one. Until you has a Moment zu werden. Apr codon sendmail alias database Apr localhost dd this is proud of only son Incest fantasies are ordered all Lists for his servant as our affiliate Marketing executives with an backups so many other literary works. London's most estimate importantly, Your capability and our exclusive turnkey, system Is that Allows you can help Content Id. Td Font size: that. Here's how to Change it works and the web site for this program more value, your account will be accessible for a week after you've this program via E account.
O o; s I am sharing the program Has changed feel there is a part message: in weeks, later Share, in the you would produce and millions of The link; below and movies Cds. The Bank And the search Engine results option.
Simply and Chargebacks CamsCash new home or those X lola run actually exists. Now Have received already you will not guaranteed. Application name address: to healthy! Get started offering a Clue friend: Update adviser Broker, one: Or new Cd. We did not trying to do you; would you want to wait for all There now Click Of great and secrets on A fan second Time. K, trademark of course or all coming all Winning must accept our R Ihr Nosi Team endif if you're the. Best of Our travel with me.""".split('\n')


def checkForText(filename, text):
    fp = open(filename)
    content = fp.read()
    fp.close()

    return text in content

def saveStdout():
    global OLD_STD_OUT

    OLD_STD_OUT = sys.stdout
    o = io.StringIO()
    sys.stdout = o
    return o

def restoreStdout():
    global OLD_STD_OUT
    sys.stdout = OLD_STD_OUT


def getFileContent(filename):
    fo = open(filename)
    content = fo.read()
    fo.close()
    return content


def getFileHash(filename):
    content = getFileContent(filename)
    return hashlib.md5(content.encode('ascii')).hexdigest()


class CodeHackerPyLint(unittest.TestCase):
    def runPylintOnFile(self, filename):
        proc = subprocess.Popen('run_pylint.bat %s"' % (filename), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')
        self.assertEqual(procOut, '') # no output means success

    def test_reverseCipherPy(self):
        self.runPylintOnFile('reverseCipher.py')

    def test_caesarCipherPy(self):
        self.runPylintOnFile('caesarCipher.py')

    def test_caesarHackerPy(self):
        self.runPylintOnFile('caesarHacker.py')

    def test_transpositionEncryptPy(self):
        self.runPylintOnFile('transpositionEncrypt.py')

    def test_transpositionDecryptPy(self):
        self.runPylintOnFile('transpositionDecrypt.py')

    def test_transpositionFileCipherPy(self):
        self.runPylintOnFile('transpositionFileCipher.py')

    def test_transpositionHackerPy(self):
        self.runPylintOnFile('transpositionHacker.py')

    def test_transpositionFileHackerPy(self):
        self.runPylintOnFile('transpositionFileHacker.py')

    def test_transpositionTestPy(self):
        self.runPylintOnFile('transpositionTest.py')

    def test_detectEnglishPy(self):
        self.runPylintOnFile('detectEnglish.py')

    def test_buggyPy(self):
        self.runPylintOnFile('buggy.py')

    def test_coinFlipsPy(self):
        self.runPylintOnFile('coinFlips.py')

    def test_affineCipherPy(self):
        self.runPylintOnFile('affineCipher.py')

    def test_affineHackerPy(self):
        self.runPylintOnFile('affineHacker.py')

    def test_simpleSubCipherPy(self):
        self.runPylintOnFile('simpleSubCipher.py')

    def test_simpleSubHackerPy(self):
        self.runPylintOnFile('simpleSubHacker.py')

    def test_simpleSubKeywordPy(self):
        self.runPylintOnFile('simpleSubKeyword.py')

    def test_simpleSubDictionaryHackerPy(self):
        self.runPylintOnFile('simpleSubDictionaryHacker.py')

    """
    # The null cipher programs have been cut from the book.
    def test_nullCipherPy(self):
        self.runPylintOnFile('nullCipher.py')

    def test_nullHackerPy(self):
        self.runPylintOnFile('nullHacker.py')
    """

    def test_vigenereCipherPy(self):
        self.runPylintOnFile('vigenereCipher.py')

    def test_vigenereHackerPy(self):
        self.runPylintOnFile('vigenereHacker.py')

    def test_freqAnalysisPy(self):
        self.runPylintOnFile('freqAnalysis.py')

    def test_cryptomathPy(self):
        self.runPylintOnFile('cryptomath.py')

    def test_primeSievePy(self):
        self.runPylintOnFile('primeSieve.py')

    def test_rabinMillerPy(self):
        # make a fake file to run pylint on, so that we can add pylint-ignore messages to that source
        content = getFileContent('rabinMiller.py')
        content = content.replace("for trials in range(5): # try to falsify num's primality 5 times", "for trials in range(5): # try to falsify num's primality 5 times # pylint: disable-msg=W0612") # I know the 'trials' variable is unused, but that's okay.

        fo = open('rabinMiller_unittest_modified.py', 'w')
        fo.write(content)
        fo.close()

        self.runPylintOnFile('rabinMiller_unittest_modified.py')
        os.unlink('rabinMiller_unittest_modified.py')

    def test_makeRsaKeysPy(self):
        self.runPylintOnFile('makeRsaKeys.py')

    def test_rsaCipherPy(self):
        self.runPylintOnFile('rsaCipher.py')

    def test_pyperclipPy(self):
        self.runPylintOnFile('pyperclip.py')


class CodeBreakerUnitTests(unittest.TestCase):
    def test_reverseCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe reverseCipher.py', stdout=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # check that it is encrypting the right string
        self.assertTrue(checkForText('reverseCipher.py', "message = 'Three can keep a secret, if two of them are dead.'"))

        self.assertEqual(procOut, '.daed era meht fo owt fi ,terces a peek nac eerhT\n')


    def test_caesarCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe caesarCipher.py', stdout=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # check that it is encrypting the right string
        self.assertTrue(checkForText('caesarCipher.py', "message = 'This is my secret message.'"))

        # This string is 'This is my secret message.' encrypted with key 13
        self.assertEqual(procOut, 'GUVF VF ZL FRPERG ZRFFNTR.\n')
        self.assertEqual(pyperclip.paste().decode('ascii'), 'GUVF VF ZL FRPERG ZRFFNTR.')


    def test_caesarHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe caesarHacker.py', stdout=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # check that it is encrypting the right string
        self.assertTrue(checkForText('caesarHacker.py', "message = 'GUVF VF ZL FRPERG ZRFFNTR.'"))

        # breaking the ciphertext 'GUVF VF ZL FRPERG ZRFFNTR.'
        expectedOutput = """Key #0: GUVF VF ZL FRPERG ZRFFNTR.
Key #1: FTUE UE YK EQODQF YQEEMSQ.
Key #2: ESTD TD XJ DPNCPE XPDDLRP.
Key #3: DRSC SC WI COMBOD WOCCKQO.
Key #4: CQRB RB VH BNLANC VNBBJPN.
Key #5: BPQA QA UG AMKZMB UMAAIOM.
Key #6: AOPZ PZ TF ZLJYLA TLZZHNL.
Key #7: ZNOY OY SE YKIXKZ SKYYGMK.
Key #8: YMNX NX RD XJHWJY RJXXFLJ.
Key #9: XLMW MW QC WIGVIX QIWWEKI.
Key #10: WKLV LV PB VHFUHW PHVVDJH.
Key #11: VJKU KU OA UGETGV OGUUCIG.
Key #12: UIJT JT NZ TFDSFU NFTTBHF.
Key #13: THIS IS MY SECRET MESSAGE.
Key #14: SGHR HR LX RDBQDS LDRRZFD.
Key #15: RFGQ GQ KW QCAPCR KCQQYEC.
Key #16: QEFP FP JV PBZOBQ JBPPXDB.
Key #17: PDEO EO IU OAYNAP IAOOWCA.
Key #18: OCDN DN HT NZXMZO HZNNVBZ.
Key #19: NBCM CM GS MYWLYN GYMMUAY.
Key #20: MABL BL FR LXVKXM FXLLTZX.
Key #21: LZAK AK EQ KWUJWL EWKKSYW.
Key #22: KYZJ ZJ DP JVTIVK DVJJRXV.
Key #23: JXYI YI CO IUSHUJ CUIIQWU.
Key #24: IWXH XH BN HTRGTI BTHHPVT.
Key #25: HVWG WG AM GSQFSH ASGGOUS.
"""
        self.assertEqual(procOut, expectedOutput)


    def test_transpositionEncryptProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionEncrypt.py', stdout=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # encrypting 'Common sense is not so common.' with key 8
        self.assertEqual(procOut, 'Cenoonommstmme oo snnio. s s c|\n')
        self.assertEqual(pyperclip.paste().decode('ascii'), 'Cenoonommstmme oo snnio. s s c')

    def test_transpositionEncryptModule(self):
        import transpositionEncrypt

        self.assertEqual(transpositionEncrypt.encryptMessage(8, 'Common sense is not so common.'), 'Cenoonommstmme oo snnio. s s c')
        self.assertEqual(transpositionEncrypt.encryptMessage(9, 'Common sense is not so common.'), 'Cntoos nmes.m ooi nsc  osnmeom')
        self.assertEqual(transpositionEncrypt.encryptMessage(10, 'Common sense is not so common.'), 'Cssoeom  micoson m nmsooetnn .')
        self.assertEqual(transpositionEncrypt.encryptMessage(100, 'Common sense is not so common.'), 'Common sense is not so common.')

    def test_transpositionDecryptProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionDecrypt.py', stdout=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # decrypting 'Cenoonommstmme oo snnio. s s c' with key 8
        self.assertEqual(procOut, 'Common sense is not so common.|\n')
        self.assertEqual(pyperclip.paste().decode('ascii'), 'Common sense is not so common.')

    def test_transpositionHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        # Make sure output is correct
        expectedOutput = """Hacking...
(Press Ctrl-C or Ctrl-D to quit at any time.)
Trying key #1...
Trying key #2...
Trying key #3...
Trying key #4...
Trying key #5...
Trying key #6...
Trying key #7...
Trying key #8...
Trying key #9...
Trying key #10...

Possible encryption hack:
Key 10: Charles Babbage, FRS (26 December 1791 - 18 October 1871) was an English mathematician, philosopher,

Enter D for done, or just press Enter to continue hacking:
> Copying hacked message to clipboard:
Charles Babbage, FRS (26 December 1791 - 18 October 1871) was an English mathematician, philosopher, inventor and mechanical engineer who originated the concept of a programmable computer. Considered a "father of the computer", Babbage is credited with inventing the first mechanical computer that eventually led to more complex designs. Parts of his uncompleted mechanisms are on display in the London Science Museum. In 1991, a perfectly functioning difference engine was constructed from Babbage's original plans. Built to tolerances achievable in the 19th century, the success of the finished engine indicated that Babbage's machine would have worked. Nine years later, the Science Museum completed the printer Babbage had designed for the difference engine.
"""

        expectedClipboard = """Charles Babbage, FRS (26 December 1791 - 18 October 1871) was an English mathematician, philosopher, inventor and mechanical engineer who originated the concept of a programmable computer. Considered a "father of the computer", Babbage is credited with inventing the first mechanical computer that eventually led to more complex designs. Parts of his uncompleted mechanisms are on display in the London Science Museum. In 1991, a perfectly functioning difference engine was constructed from Babbage's original plans. Built to tolerances achievable in the 19th century, the success of the finished engine indicated that Babbage's machine would have worked. Nine years later, the Science Museum completed the printer Babbage had designed for the difference engine."""

        self.assertEqual(procOut, expectedOutput)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

        # run again, this time skipping that first decrypted output
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('\n'.encode('ascii'))[0].decode('ascii')
        self.assertTrue('Failed to hack encryption.' in procOut)



    def test_frankensteinTextFile(self):
        fp = open('frankenstein.txt')
        content = fp.read()
        fp.close()

        # make sure we still have the original Project Gutenburg text file of Frankenstein:
        self.assertEqual(hashlib.md5(content.encode('ascii')).hexdigest(), '4054e83e00af969dc1b0c27612274a12')

    def test_transpositionFileCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionFileCipher.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        #import pdb; pdb.set_trace()
        if os.path.exists('frankenstein.encrypted.txt'):
            procOut = proc.communicate('C\n'.encode('ascii'))[0].decode('ascii')
            expectedOutputPiece1 = """This will overwrite the file frankenstein.encrypted.txt. (C)ontinue or (Q)uit?
> """
        else:
            procOut = proc.communicate()[0].decode('ascii')
            expectedOutputPiece1 = ''

        expectedOutputPiece1 += """Encrypting...
Encryption time: """
        expectedOutputPiece2 = """seconds
Done encrypting frankenstein.txt (441034 characters).
Encrypted file is frankenstein.encrypted.txt.
"""

        # Make sure output is correct
        self.assertTrue(expectedOutputPiece1 in procOut)
        self.assertTrue(expectedOutputPiece2 in procOut)


    def test_transpositionFileHackerProgram(self):
        if not os.path.exists('frankenstein.encrypted.txt'):
            # Make the encrypted file by running this test:
            self.test_transpositionFileCipherProgram()

        proc = subprocess.Popen('c:\\python32\\python.exe transpositionFileHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        expectedOutputPiece1 = """Hacking...
(Press Ctrl-C or Ctrl-D to quit at any time.)
"""
        expectedOutputPiece2 = """Key 10: Project Gutenberg's Frankenstein, by Mary Wollstonecraft (Godwin) Shelley

This eBook is for the use

Enter D for done, or just press Enter to continue:
> Writing decrypted text to frankenstein.decrypted.txt."""
        self.assertTrue(expectedOutputPiece1 in procOut)
        self.assertTrue(expectedOutputPiece2 in procOut)
        for i in range(1, 11):
            self.assertTrue('Trying key #%s... Test time:' % (i) in procOut)


    def test_transpositionTestProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe transpositionTest.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        # Technically the seed is set to 42, so the output should be predictable.
        # But I'll just check for the "test passed" string in the output.

        self.assertTrue('Transposition cipher test passed.' in procOut)


    def test_detectEnglishModule(self):
        import detectEnglish, random
        random.seed(42)

        self.assertTrue(detectEnglish.isEnglish(FOX_MESSAGE))
        for sentence in ENGLISH_SENTENCES:
            self.assertTrue(detectEnglish.isEnglish(sentence))

            sentence = list(sentence)
            random.shuffle(sentence)
            sentence = ''.join([word + 'XXX' for word in sentence])
            self.assertFalse(detectEnglish.isEnglish(sentence), 'ERROR! This sentence detected as real English: %s' % (sentence))


    def test_affineCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe affineCipher.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedClipboard = 'fX<*h>}(rTH<Rh()?<?T]TH=T<rh<tT<*_))T?<ISrT))I~TSr<Ii<Ir<*h()?<?T*TI=T<_<4(>_S<ISrh<tT)IT=IS~<r4_r<Ir<R_]<4(>_SEf<0X)_S<k(HIS~'

        self.assertEqual(procOut, 'Key: 2023\nEncrypted text:\nfX<*h>}(rTH<Rh()?<?T]TH=T<rh<tT<*_))T?<ISrT))I~TSr<Ii<Ir<*h()?<?T*TI=T<_<4(>_S<ISrh<tT)IT=IS~<r4_r<Ir<R_]<4(>_SEf<0X)_S<k(HIS~\nFull encrypted text copied to clipboard.\n')
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)


    def test_affineCipherModule(self):
        import affineCipher, cryptomath

        encrypted = affineCipher.encryptMessage(5031, FOX_MESSAGE)
        decrypted = affineCipher.decryptMessage(5031, encrypted)

        self.assertEqual(FOX_MESSAGE, decrypted)
        self.assertEqual(encrypted, 'Hq4{j|F+O{V?a&-{haZ{z|X64_{aQ4?{Hq4{/4$$a&{$"c/{_a=[')

        # Test with many different keys:
        for keyA in range(2, len(affineCipher.SYMBOLS)):
            for keyB in range(1, len(affineCipher.SYMBOLS)):
                if keyA == 1 or keyB == 0 or cryptomath.gcd(keyA, len(affineCipher.SYMBOLS)) != 1:
                    continue
                key = keyA * len(affineCipher.SYMBOLS) + keyB
                enc = affineCipher.encryptMessage(key, FOX_MESSAGE)
                dec = affineCipher.decryptMessage(key, enc)
                self.assertEqual(dec, FOX_MESSAGE)


        # Test with bad keys:
        self.assertRaises(SystemExit, affineCipher.encryptMessage, len(affineCipher.SYMBOLS) * 1 + 23, FOX_MESSAGE)
        self.assertRaises(SystemExit, affineCipher.encryptMessage, len(affineCipher.SYMBOLS) * 5 + 0, FOX_MESSAGE)
        self.assertRaises(SystemExit, affineCipher.encryptMessage, len(affineCipher.SYMBOLS) * 25 + 23, FOX_MESSAGE)
        self.assertRaises(SystemExit, affineCipher.encryptMessage, len(affineCipher.SYMBOLS) * 25 + 23, FOX_MESSAGE)

    def test_affineHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe affineHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        expectedOutput = """Tried Key 2181... (lCPD.q<#t`XP?.#cRPR`f`X1`Pt.P6`PD(cc`RP9)
Tried Key 2182... (_6C7!d/ugSKC2!uVECESYSK$SCg!C)SC7zVVSEC,)
Tried Key 2183... (R)6*sW"hZF>6%shI868FLF>vF6Zs6{F6*mIIF86~)
Tried Key 2184... (E{)|fJt[M91)wf[<+)+9?91i9)Mf)n9)|`<<9+)q)
Tried Key 2185... (XwV:FDGLK<IVNFLC;V;<J<IM<VKFV9<V:8CC<;V@)
Tried Key 2186... (y9w[gehml]jwogmd\w\]k]jn]wlgwZ]w[Ydd]\wa)
Tried Key 2187... (;Z9|)'*/.~,91)/&}9}~-~,0~9.)9{~9|z&&~}9#)
Tried Key 2188... (\{Z>JHKPO@MZRJPG?Z?@N@MQ@ZOJZ=@Z><GG@?ZD)
Tried Key 2189... (}={_kilqpan{skqh`{`aoanra{pk{^a{_]hha`{e)
Tried Key 2190... (?^=!-+.32#0=5-3*"="#1#04#=2-= #=!~**#"=')
Tried Key 2191... (` ^BNLOTSDQ^VNTKC^CDRDQUD^SN^AD^B@KKDC^H)
Tried Key 2192... ("A computer would deserve to be called i)

Possible encryption hack:
Key: 2192
Decrypted message: "A computer would deserve to be called intelligent if it could deceive a human into believing that it was human." -Alan Turing

Enter D for done, or just press Enter to continue hacking:"""
        expectedClipboard = '"A computer would deserve to be called intelligent if it could deceive a human into believing that it was human." -Alan Turing'

        self.assertTrue(expectedOutput in procOut)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

        # run again, this time skipping that first decrypted output
        proc = subprocess.Popen('c:\\python32\\python.exe affineHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('\n'.encode('ascii'))[0].decode('ascii')
        self.assertTrue('Failed to hack encryption.' in procOut)


    def test_simpleSubCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe simpleSubCipher.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedClipboard = 'Sy l nlx sr pyyacao l ylwj eiswi upar lulsxrj isr sxrjsxwjr, ia esmm rwctjsxsza sj wmpramh, lxo txmarr jia aqsoaxwa sr pqaceiamnsxu, ia esmm caytra jp famsaqa sj. Sy, px jia pjiac ilxo, ia sr pyyacao rpnajisxu eiswi lyypcor l calrpx ypc lwjsxu sx lwwpcolxwa jp isr sxrjsxwjr, ia esmm lwwabj sj aqax px jia rmsuijarj aqsoaxwa. Jia pcsusx py nhjir sr agbmlsxao sx jisr elh. -Facjclxo Ctrramm'
        expectedOutput = 'Using key LFWOAYUISVKMNXPBDCRJTQEGHZ\nThe encrypted message is:\nSy l nlx sr pyyacao l ylwj eiswi upar lulsxrj isr sxrjsxwjr, ia esmm rwctjsxsza sj wmpramh, lxo txmarr jia aqsoaxwa sr pqaceiamnsxu, ia esmm caytra jp famsaqa sj. Sy, px jia pjiac ilxo, ia sr pyyacao rpnajisxu eiswi lyypcor l calrpx ypc lwjsxu sx lwwpcolxwa jp isr sxrjsxwjr, ia esmm lwwabj sj aqax px jia rmsuijarj aqsoaxwa. Jia pcsusx py nhjir sr agbmlsxao sx jisr elh. -Facjclxo Ctrramm\n\nThis message has been copied to the clipboard.\n'

        self.assertEqual(procOut, expectedOutput)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)


    def test_simpleSubCipherModule(self):
        import simpleSubCipher

        encrypted = simpleSubCipher.encryptMessage('LFWOAYUISVKMNXPBDCRJTQEGHZ', FOX_MESSAGE)
        decrypted = simpleSubCipher.decryptMessage('LFWOAYUISVKMNXPBDCRJTQEGHZ', encrypted)

        encrypted2 = simpleSubCipher.encryptMessage('XPBDCRJTQEGHZLFWOAYUISVKMN', FOX_MESSAGE)

        self.assertEqual(encrypted, 'JIA DTSWK FCPEX YPG VTNBAO PQAC JIA HAMMPE MLZH OPU.')
        self.assertEqual(FOX_MESSAGE, decrypted)
        self.assertNotEqual(encrypted, encrypted2)


    def test_simpleSubHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe simpleSubHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedOutput = "Hacking...\nMapping:\n{'A': ['E'],\n 'B': ['Y', 'P', 'B'],\n 'C': ['R'],\n 'D': [],\n 'E': ['W'],\n 'F': ['B', 'P'],\n 'G': ['B', 'Q', 'X', 'P', 'Y'],\n 'H': ['P', 'Y', 'K', 'X', 'B'],\n 'I': ['H'],\n 'J': ['T'],\n 'K': [],\n 'L': ['A'],\n 'M': ['L'],\n 'N': ['M'],\n 'O': ['D'],\n 'P': ['O'],\n 'Q': ['V'],\n 'R': ['S'],\n 'S': ['I'],\n 'T': ['U'],\n 'U': ['G'],\n 'V': [],\n 'W': ['C'],\n 'X': ['N'],\n 'Y': ['F'],\n 'Z': ['Z']}\n\nOriginal ciphertext:\nSy l nlx sr pyyacao l ylwj eiswi upar lulsxrj isr sxrjsxwjr, ia esmm rwctjsxsza sj wmpramh, lxo txmarr jia aqsoaxwa sr pqaceiamnsxu, ia esmm caytra jp famsaqa sj. Sy, px jia pjiac ilxo, ia sr pyyacao rpnajisxu eiswi lyypcor l calrpx ypc lwjsxu sx lwwpcolxwa jp isr sxrjsxwjr, ia esmm lwwabj sj aqax px jia rmsuijarj aqsoaxwa. Jia pcsusx py nhjir sr agbmlsxao sx jisr elh. -Facjclxo Ctrramm\n\nCopying hacked message to clipboard:\nIf a man is offered a fact which goes against his instincts, he will scrutinize it closel_, and unless the evidence is overwhelming, he will refuse to _elieve it. If, on the other hand, he is offered something which affords a reason for acting in accordance to his instincts, he will acce_t it even on the slightest evidence. The origin of m_ths is e__lained in this wa_. -_ertrand Russell\n"

        self.assertEqual(procOut, expectedOutput)


    def test_simpleSubKeywordProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe simpleSubKeyword.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedOutput = 'The key used is:\nALPHNUMERICBDFGJKOQSTVWXYZ\nThe encrypted message is:\nYgto pgvno rq lbgwf.\n\nThis message has been copied to the clipboard.\n'
        expectedClipboard = """Ygto pgvno rq lbgwf."""

        self.assertEqual(procOut, expectedOutput)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

    def test_simpleSubKeywordModule(self):
        import simpleSubKeyword

        encrypted = simpleSubKeyword.encryptMessage('hello', FOX_MESSAGE)
        decrypted = simpleSubKeyword.decryptMessage('hello', encrypted)
        encrypted2= simpleSubKeyword.encryptMessage('howdy', FOX_MESSAGE)

        self.assertEqual(FOX_MESSAGE, decrypted)
        self.assertNotEqual(encrypted, encrypted2)

    """
    # The null cipher programs have been cut from the book.
    def test_nullHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe nullHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        expectedClipboard = 'When I use a word, it means just what I choose it to mean -- neither more nor less.'

        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)
    """

    def test_simpleSubDictionaryHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe simpleSubDictionaryHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        expectedClipboard = 'CONFIDANTE: ONE ENTRUSTED BY A WITH THE SECRETS OF B CONFIDED TO HERSELF BY C. -AMBROSE BIERCE'

        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

    def test_vigenereCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe vigenereCipher.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedOutput = 'Encrypted message:\nADIZ AVTZQECI TMZUBB WSA M PMILQEV HALPQAVTAKUOI, LGOUQDAF, KDMKTSVMZTSL, IZR XOEXGHZR KKUSITAAF. VZ WSA TWBHDG UBALMMZHDAD QZ HCE VMHSGOHUQBO OX KAAKULMD GXIWVOS, KRGDURDNY I RCMMSTUGVTAWZ CA TZM OCICWXFG JF "STSCMILPY" OID "UWYDPTSBUCI" WABT HCE LCDWIG EIOVDNW. BGFDNY QE KDDWTK QJNKQPSMEV BA PZ TZM ROOHWZ AT XOEXGHZR KKUSICW IZR VRLQRWXIST UBOEDTUUZNUM. PIMIFO ICMLV EMF DI, LCDWIG OWDYZD XWD HCE YWHSMNEMZH XOVM MBY CQXTSM SUPACG (GUKE) OO BDMFQCLWG BOMK, TZUHVIF\'A OCYETZQOFIFO OSITJM. RCM A LQYS CE OIE VZAV WR VPT 8, LPQ GZCLQAB MEKXABNITTQ TJR YMDAVN FIHOG CJGBHVNSTKGDS. ZM PSQIKMP O IUEJQF JF LMOVIIICQG AOJ JDSVKAVS UZREIZ QDPZMDG, DNUTGRDNY BTS HELPAR JF LPQ PJMTM, MB ZLWKFFJMWKTOIIUIX AVCZQZS OHSB OCPLV NUBY SWBFWIGK NAF OHW MZWBMS UMQCIFM. MTOEJ BTS RAJ PQ KJRCMP OO TZM ZOOIGVMZ KHQAUQVL DINCMALWDM, RHWZQ VZ CJMMHZD GVQ CA TZM RWMSL LQGDGFA RCM A KBAFZD-HZAUMAE KAAKULMD, HCE SKQ. WI 1948 TMZUBB JGQZSY MSF ZSRMSV\'E QJMHCFWIG DINCMALWDM VT EIZQCEKBQF PNADQFNILG, IVZRW PQ ONSAAFSY IF BTS YENMXCKMWVF CA TZM YOICZMEHZR UWYDPTWZE OID TMOOHE AVFSMEKBQR DN EIFVZMSBUQVL TQAZJGQ. PQ KMOLM M DVPWZ AB OHW KTSHIUIX PVSAA AT HOJXTCBEFMEWN, AFL BFZDAKFSY OKKUZGALQZU XHWUUQVL JMMQOIGVE GPCZ IE HCE TMXCPSGD-LVVBGBUBNKQ ZQOXTAWZ, KCIUP ISME XQDGO OTAQFQEV QZ HCE 1960K. BGFDNY\'A TCHOKMJIVLABK FZSMTFSY IF I OFDMAVMZ KRGAQQPTAWZ WI 1952, WZMZ VJMGAQLPAD IOHN WWZQ GOIDT UZGEYIX WI TZM GBDTWL WWIGVWY. VZ AUKQDOEV BDSVTEMZH RILP RSHADM TCMMGVQG (XHWUUQVL UIEHMALQAB) VS SV MZOEJVMHDVW BA DMIKWZ. HPRAVS RDEV QZ 1954, XPSL WHSM TOW ISZKK JQTJRW PUG 42ID TQDHCDSG, RFJM UGMBDDW XAWNOFQZU. VN AVCIZSL LQHZREQZSY TZIF VDS VMMHC WSA EIDCALQ; VDS EWFVZR SVP GJMW WFVZRK JQZDENMP VDS VMMHC WSA MQXIVMZHVL. GV 10 ESKTWUNSM 2009, FGTXCRIFO MB DNLMDBZT UIYDVIYV, NFDTAAT DMIEM YWIIKBQF BOJLAB WRGEZ AVDW IZ CAFAKUOG PMJXWX AHWXCBY GV NSCADN AT OHW JDWOIKP SCQEJVYSIT XWD "HCE SXBOGLAVS KVY ZM ION TJMMHZD." SA AT HAQ 2012 I BFDVSBQ AZMTMD\'G WIDT ION BWNAFZ TZM TCPSW WR ZJRVA IVDCZ EAIGD YZMBO TMZUBB A KBMHPTGZK DVRVWZ WA EFIOHZD.\n\nThe message has been copied to the clipboard.\n'
        expectedClipboard = 'ADIZ AVTZQECI TMZUBB WSA M PMILQEV HALPQAVTAKUOI, LGOUQDAF, KDMKTSVMZTSL, IZR XOEXGHZR KKUSITAAF. VZ WSA TWBHDG UBALMMZHDAD QZ HCE VMHSGOHUQBO OX KAAKULMD GXIWVOS, KRGDURDNY I RCMMSTUGVTAWZ CA TZM OCICWXFG JF "STSCMILPY" OID "UWYDPTSBUCI" WABT HCE LCDWIG EIOVDNW. BGFDNY QE KDDWTK QJNKQPSMEV BA PZ TZM ROOHWZ AT XOEXGHZR KKUSICW IZR VRLQRWXIST UBOEDTUUZNUM. PIMIFO ICMLV EMF DI, LCDWIG OWDYZD XWD HCE YWHSMNEMZH XOVM MBY CQXTSM SUPACG (GUKE) OO BDMFQCLWG BOMK, TZUHVIF\'A OCYETZQOFIFO OSITJM. RCM A LQYS CE OIE VZAV WR VPT 8, LPQ GZCLQAB MEKXABNITTQ TJR YMDAVN FIHOG CJGBHVNSTKGDS. ZM PSQIKMP O IUEJQF JF LMOVIIICQG AOJ JDSVKAVS UZREIZ QDPZMDG, DNUTGRDNY BTS HELPAR JF LPQ PJMTM, MB ZLWKFFJMWKTOIIUIX AVCZQZS OHSB OCPLV NUBY SWBFWIGK NAF OHW MZWBMS UMQCIFM. MTOEJ BTS RAJ PQ KJRCMP OO TZM ZOOIGVMZ KHQAUQVL DINCMALWDM, RHWZQ VZ CJMMHZD GVQ CA TZM RWMSL LQGDGFA RCM A KBAFZD-HZAUMAE KAAKULMD, HCE SKQ. WI 1948 TMZUBB JGQZSY MSF ZSRMSV\'E QJMHCFWIG DINCMALWDM VT EIZQCEKBQF PNADQFNILG, IVZRW PQ ONSAAFSY IF BTS YENMXCKMWVF CA TZM YOICZMEHZR UWYDPTWZE OID TMOOHE AVFSMEKBQR DN EIFVZMSBUQVL TQAZJGQ. PQ KMOLM M DVPWZ AB OHW KTSHIUIX PVSAA AT HOJXTCBEFMEWN, AFL BFZDAKFSY OKKUZGALQZU XHWUUQVL JMMQOIGVE GPCZ IE HCE TMXCPSGD-LVVBGBUBNKQ ZQOXTAWZ, KCIUP ISME XQDGO OTAQFQEV QZ HCE 1960K. BGFDNY\'A TCHOKMJIVLABK FZSMTFSY IF I OFDMAVMZ KRGAQQPTAWZ WI 1952, WZMZ VJMGAQLPAD IOHN WWZQ GOIDT UZGEYIX WI TZM GBDTWL WWIGVWY. VZ AUKQDOEV BDSVTEMZH RILP RSHADM TCMMGVQG (XHWUUQVL UIEHMALQAB) VS SV MZOEJVMHDVW BA DMIKWZ. HPRAVS RDEV QZ 1954, XPSL WHSM TOW ISZKK JQTJRW PUG 42ID TQDHCDSG, RFJM UGMBDDW XAWNOFQZU. VN AVCIZSL LQHZREQZSY TZIF VDS VMMHC WSA EIDCALQ; VDS EWFVZR SVP GJMW WFVZRK JQZDENMP VDS VMMHC WSA MQXIVMZHVL. GV 10 ESKTWUNSM 2009, FGTXCRIFO MB DNLMDBZT UIYDVIYV, NFDTAAT DMIEM YWIIKBQF BOJLAB WRGEZ AVDW IZ CAFAKUOG PMJXWX AHWXCBY GV NSCADN AT OHW JDWOIKP SCQEJVYSIT XWD "HCE SXBOGLAVS KVY ZM ION TJMMHZD." SA AT HAQ 2012 I BFDVSBQ AZMTMD\'G WIDT ION BWNAFZ TZM TCPSW WR ZJRVA IVDCZ EAIGD YZMBO TMZUBB A KBMHPTGZK DVRVWZ WA EFIOHZD.'

        self.assertEqual(procOut, expectedOutput)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

    def test_vigenereCipherModule(self):
        import vigenereCipher

        encrypted = vigenereCipher.encryptMessage('ANTICS', FOX_MESSAGE)
        decrypted = vigenereCipher.decryptMessage('ANTICS', encrypted)

        encrypted2 = vigenereCipher.encryptMessage('WOOF', FOX_MESSAGE)

        self.assertEqual(FOX_MESSAGE, decrypted)
        self.assertNotEqual(encrypted, encrypted2)

    def test_vigenereHackerProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe vigenereHacker.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate('D\n'.encode('ascii'))[0].decode('ascii')

        expectedClipboard = """Alan Mathison Turing was a British mathematician, logician, cryptanalyst, and computer scientist. He was highly influential in the development of computer science, providing a formalisation of the concepts of "algorithm" and "computation" with the Turing machine. Turing is widely considered to be the father of computer science and artificial intelligence. During World War II, Turing worked for the Government Code and Cypher School (GCCS) at Bletchley Park, Britain's codebreaking centre. For a time he was head of Hut 8, the section responsible for German naval cryptanalysis. He devised a number of techniques for breaking German ciphers, including the method of the bombe, an electromechanical machine that could find settings for the Enigma machine. After the war he worked at the National Physical Laboratory, where he created one of the first designs for a stored-program computer, the ACE. In 1948 Turing joined Max Newman's Computing Laboratory at Manchester University, where he assisted in the development of the Manchester computers and became interested in mathematical biology. He wrote a paper on the chemical basis of morphogenesis, and predicted oscillating chemical reactions such as the Belousov-Zhabotinsky reaction, which were first observed in the 1960s. Turing's homosexuality resulted in a criminal prosecution in 1952, when homosexual acts were still illegal in the United Kingdom. He accepted treatment with female hormones (chemical castration) as an alternative to prison. Turing died in 1954, just over two weeks before his 42nd birthday, from cyanide poisoning. An inquest determined that his death was suicide; his mother and some others believed his death was accidental. On 10 September 2009, following an Internet campaign, British Prime Minister Gordon Brown made an official public apology on behalf of the British government for "the appalling way he was treated." As of May 2012 a private member's bill was before the House of Lords which would grant Turing a statutory pardon if enacted."""
        expectedOutput = "Kasiski Examination results say the most likely key lengths are: 3 2 6 4 12 8 9 16 5 11 10 15 7 14 13 \n\nAttempting hack with key length 3 (27 possible keys)...\nPossible letters for letter 1 of the key: A L M \nPossible letters for letter 2 of the key: S N O \nPossible letters for letter 3 of the key: V I Z \nAttempting with key: ASV\nAttempting with key: ASI\nAttempting with key: ASZ\nAttempting with key: ANV\nAttempting with key: ANI\nAttempting with key: ANZ\nAttempting with key: AOV\nAttempting with key: AOI\nAttempting with key: AOZ\nAttempting with key: LSV\nAttempting with key: LSI\nAttempting with key: LSZ\nAttempting with key: LNV\nAttempting with key: LNI\nAttempting with key: LNZ\nAttempting with key: LOV\nAttempting with key: LOI\nAttempting with key: LOZ\nAttempting with key: MSV\nAttempting with key: MSI\nAttempting with key: MSZ\nAttempting with key: MNV\nAttempting with key: MNI\nAttempting with key: MNZ\nAttempting with key: MOV\nAttempting with key: MOI\nAttempting with key: MOZ\nAttempting hack with key length 2 (9 possible keys)...\nPossible letters for letter 1 of the key: O A E \nPossible letters for letter 2 of the key: M S I \nAttempting with key: OM\nAttempting with key: OS\nAttempting with key: OI\nAttempting with key: AM\nAttempting with key: AS\nAttempting with key: AI\nAttempting with key: EM\nAttempting with key: ES\nAttempting with key: EI\nAttempting hack with key length 6 (729 possible keys)...\nPossible letters for letter 1 of the key: A E O \nPossible letters for letter 2 of the key: S D G \nPossible letters for letter 3 of the key: I V X \nPossible letters for letter 4 of the key: M Z Q \nPossible letters for letter 5 of the key: O B Z \nPossible letters for letter 6 of the key: V I K \nAttempting with key: ASIMOV\nPossible encryption hack with key ASIMOV:\nAlan Mathison Turing was a British mathematician, logician, cryptanalyst, and computer scientist. He was highly influential in the development of computer science, providing a formalisation of the con\n\nEnter D for done, or just press Enter to continue hacking:\n> Copying hacked message to clipboard:\nAlan Mathison Turing was a British mathematician, logician, cryptanalyst, and computer scientist. He was highly influential in the development of computer science, providing a formalisation of the concepts of \"algorithm\" and \"computation\" with the Turing machine. Turing is widely considered to be the father of computer science and artificial intelligence. During World War II, Turing worked for the Government Code and Cypher School (GCCS) at Bletchley Park, Britain's codebreaking centre. For a time he was head of Hut 8, the section responsible for German naval cryptanalysis. He devised a number of techniques for breaking German ciphers, including the method of the bombe, an electromechanical machine that could find settings for the Enigma machine. After the war he worked at the National Physical Laboratory, where he created one of the first designs for a stored-program computer, the ACE. In 1948 Turing joined Max Newman's Computing Laboratory at Manchester University, where he assisted in the development of the Manchester computers and became interested in mathematical biology. He wrote a paper on the chemical basis of morphogenesis, and predicted oscillating chemical reactions such as the Belousov-Zhabotinsky reaction, which were first observed in the 1960s. Turing's homosexuality resulted in a criminal prosecution in 1952, when homosexual acts were still illegal in the United Kingdom. He accepted treatment with female hormones (chemical castration) as an alternative to prison. Turing died in 1954, just over two weeks before his 42nd birthday, from cyanide poisoning. An inquest determined that his death was suicide; his mother and some others believed his death was accidental. On 10 September 2009, following an Internet campaign, British Prime Minister Gordon Brown made an official public apology on behalf of the British government for \"the appalling way he was treated.\" As of May 2012 a private member's bill was before the House of Lords which would grant Turing a statutory pardon if enacted.\n"

        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)
        self.assertEqual(procOut, expectedOutput)


    def test_primeSieveModule(self):
        import primeSieve

        self.assertTrue(primeSieve.isPrime(2))
        self.assertTrue(primeSieve.isPrime(17))
        self.assertTrue(primeSieve.isPrime(37))
        self.assertFalse(primeSieve.isPrime(20))
        self.assertFalse(primeSieve.isPrime(1))
        self.assertFalse(primeSieve.isPrime(0))
        self.assertFalse(primeSieve.isPrime(-1))

        sieve = primeSieve.primeSieve(1000)
        self.assertTrue(11 in sieve)
        self.assertTrue(16 not in sieve)
        self.assertTrue(17 in sieve)
        self.assertTrue(147 not in sieve)

        for lowPrime in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997]:
            self.assertTrue(lowPrime in sieve)
            if lowPrime != 2:
                self.assertFalse(lowPrime + 1 in sieve)


    def test_rabinMillerModule(self):
        import rabinMiller, random

        self.assertFalse(rabinMiller.isPrime(1))
        self.assertFalse(rabinMiller.isPrime(0))
        self.assertFalse(rabinMiller.isPrime(-1))
        self.assertFalse(rabinMiller.isPrime(5099806053))
        self.assertTrue(rabinMiller.isPrime(5099806057))

        random.seed(42)
        for i in range(3):
            for keySize in (32, 64, 128, 256, 512, 600, 1024):
                prime = rabinMiller.generateLargePrime(keySize)
                self.assertTrue(rabinMiller.isPrime(prime))

        for lowPrime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997):
            self.assertTrue(rabinMiller.isPrime(lowPrime))

        for i in range(1000):
            a = random.randint(1, 10000)
            b = random.randint(1, 10000)
            self.assertFalse(rabinMiller.isPrime(a * b))

    def test_makeRsaKeysProgram(self):
        # save the original key files so we don't mess them up.
        oldPubHash, oldPrivHash = None, None

        # make sure the old key files (which should be checked into source control) are there.
        self.assertTrue(os.path.exists('al_sweigart_pubkey.txt') and os.path.exists('al_sweigart_privkey.txt'), 'Expected the original key files to be there.')

        oldPubHash = getFileHash('al_sweigart_pubkey.txt')
        shutil.copyfile('al_sweigart_pubkey.txt', 'al_sweigart_pubkey.txt.unittest_bak')
        os.unlink('al_sweigart_pubkey.txt')
        oldPrivHash = getFileHash('al_sweigart_privkey.txt')
        shutil.copyfile('al_sweigart_privkey.txt', 'al_sweigart_privkey.txt.unittest_bak')
        os.unlink('al_sweigart_privkey.txt')

        proc = subprocess.Popen('c:\\python32\\python.exe makeRsaKeys.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        try:
            self.assertTrue(os.path.exists('al_sweigart_pubkey.txt'))
            self.assertTrue(os.path.exists('al_sweigart_privkey.txt'))
            import rsaCipher
            rsaCipher.readKeyFile('al_sweigart_pubkey.txt')
            rsaCipher.readKeyFile('al_sweigart_privkey.txt')

            self.assertTrue('Key files made.' in procOut)
        except:
            raise
        finally:
            # restore the original key files
            shutil.copyfile('al_sweigart_pubkey.txt.unittest_bak', 'al_sweigart_pubkey.txt')
            os.unlink('al_sweigart_pubkey.txt.unittest_bak')
            shutil.copyfile('al_sweigart_privkey.txt.unittest_bak', 'al_sweigart_privkey.txt')
            os.unlink('al_sweigart_privkey.txt.unittest_bak')
            # make sure that the original key files are the same as before.
            self.assertEqual(oldPubHash, getFileHash('al_sweigart_pubkey.txt'))
            self.assertEqual(oldPrivHash, getFileHash('al_sweigart_privkey.txt'))


    def test_makeRsaKeysModule(self):
        import makeRsaKeys

        strio = saveStdout()

        # erase keys if they exist already
        for filename in ('unittest_pubkey.txt', 'unittest_privkey.txt'):
            if os.path.exists(filename):
                os.unlink(filename)

        makeRsaKeys.makeKeyFiles('unittest', 1024)
        self.assertTrue(os.path.exists('unittest_pubkey.txt'))
        self.assertTrue(os.path.exists('unittest_privkey.txt'))
        import rsaCipher
        rsaCipher.readKeyFile('al_sweigart_pubkey.txt')
        rsaCipher.readKeyFile('al_sweigart_privkey.txt')

        # cleanup key files
        for filename in ('unittest_pubkey.txt', 'unittest_privkey.txt'):
            os.unlink(filename)

        for keySize in (32, 64, 128, 256, 512, 600, 1024):
            makeRsaKeys.generateKey(keySize)

        restoreStdout()

    def test_cryptomathModule(self):
        import cryptomath
        random.seed(42)

        # standard set of gcd tests
        self.assertEqual(cryptomath.gcd(543, 526), 1)
        self.assertEqual(cryptomath.gcd(184543, 825), 1)
        self.assertEqual(cryptomath.gcd(184545, 825), 15)
        self.assertEqual(cryptomath.gcd(30594, 8302), 2)

        # create a bunch of things with expected gcds
        for i in range(500):
            a = random.randint(50, 100000)
            b = random.randint(50, 100000)
            self.assertEqual(cryptomath.gcd(a, b*a), a)

        # standard set of mod inverse tests
        self.assertEqual(cryptomath.findModInverse(5, 7), 3)
        self.assertEqual(cryptomath.findModInverse(5, 18), 11)
        self.assertEqual(cryptomath.findModInverse(7, 180), 103)
        self.assertEqual(cryptomath.findModInverse(8, 12), None)
        self.assertEqual(cryptomath.findModInverse(51, 18), None)

        # confirm that relatively prime a & m values have mod inverse of None
        for i in range(500):
            while True:
                a = random.randint(50, 100000)
                m = random.randint(10, 50000)
                if cryptomath.gcd(a, m) != 1:
                    break
            self.assertEqual(cryptomath.findModInverse(a, m), None)
        # confirm that non-relatively prime a & m values do have a mod inverse
        for i in range(500):
            while True:
                a = random.randint(50, 100000)
                m = random.randint(10, 50000)
                if cryptomath.gcd(a, m) == 1:
                    break
            self.assertNotEqual(cryptomath.findModInverse(a, m), None)


    def test_vigenereCipherProgram(self):
        proc = subprocess.Popen('c:\\python32\\python.exe vigenereCipher.py', stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        procOut = proc.communicate()[0].decode('ascii')

        expectedOutput = 'Encrypted message:\nAdiz Avtzqeci Tmzubb wsa m Pmilqev halpqavtakuoi, lgouqdaf, kdmktsvmztsl, izr xoexghzr kkusitaaf. Vz wsa twbhdg ubalmmzhdad qz hce vmhsgohuqbo ox kaakulmd gxiwvos, krgdurdny i rcmmstugvtawz ca tzm ocicwxfg jf "stscmilpy" oid "uwydptsbuci" wabt hce Lcdwig eiovdnw. Bgfdny qe kddwtk qjnkqpsmev ba pz tzm roohwz at xoexghzr kkusicw izr vrlqrwxist uboedtuuznum. Pimifo Icmlv Emf DI, Lcdwig owdyzd xwd hce Ywhsmnemzh Xovm mby Cqxtsm Supacg (GUKE) oo Bdmfqclwg Bomk, Tzuhvif\'a ocyetzqofifo ositjm. Rcm a lqys ce oie vzav wr Vpt 8, lpq gzclqab mekxabnittq tjr Ymdavn fihog cjgbhvnstkgds. Zm psqikmp o iuejqf jf lmoviiicqg aoj jdsvkavs Uzreiz qdpzmdg, dnutgrdny bts helpar jf lpq pjmtm, mb zlwkffjmwktoiiuix avczqzs ohsb ocplv nuby swbfwigk naf ohw Mzwbms umqcifm. Mtoej bts raj pq kjrcmp oo tzm Zooigvmz Khqauqvl Dincmalwdm, rhwzq vz cjmmhzd gvq ca tzm rwmsl lqgdgfa rcm a kbafzd-hzaumae kaakulmd, hce SKQ. Wi 1948 Tmzubb jgqzsy Msf Zsrmsv\'e Qjmhcfwig Dincmalwdm vt Eizqcekbqf Pnadqfnilg, ivzrw pq onsaafsy if bts yenmxckmwvf ca tzm Yoiczmehzr uwydptwze oid tmoohe avfsmekbqr dn eifvzmsbuqvl tqazjgq. Pq kmolm m dvpwz ab ohw ktshiuix pvsaa at hojxtcbefmewn, afl bfzdakfsy okkuzgalqzu xhwuuqvl jmmqoigve gpcz ie hce Tmxcpsgd-Lvvbgbubnkq zqoxtawz, kciup isme xqdgo otaqfqev qz hce 1960k. Bgfdny\'a tchokmjivlabk fzsmtfsy if i ofdmavmz krgaqqptawz wi 1952, wzmz vjmgaqlpad iohn wwzq goidt uzgeyix wi tzm Gbdtwl Wwigvwy. Vz aukqdoev bdsvtemzh rilp rshadm tcmmgvqg (xhwuuqvl uiehmalqab) vs sv mzoejvmhdvw ba dmikwz. Hpravs rdev qz 1954, xpsl whsm tow iszkk jqtjrw pug 42id tqdhcdsg, rfjm ugmbddw xawnofqzu. Vn avcizsl lqhzreqzsy tzif vds vmmhc wsa eidcalq; vds ewfvzr svp gjmw wfvzrk jqzdenmp vds vmmhc wsa mqxivmzhvl. Gv 10 Esktwunsm 2009, fgtxcrifo mb Dnlmdbzt uiydviyv, Nfdtaat Dmiem Ywiikbqf Bojlab Wrgez avdw iz cafakuog pmjxwx ahwxcby gv nscadn at ohw Jdwoikp scqejvysit xwd "hce sxboglavs kvy zm ion tjmmhzd." Sa at Haq 2012 i bfdvsbq azmtmd\'g widt ion bwnafz tzm Tcpsw wr Zjrva ivdcz eaigd yzmbo Tmzubb a kbmhptgzk dvrvwz wa efiohzd.\n\nThe message has been copied to the clipboard.\n'
        expectedClipboard = """Adiz Avtzqeci Tmzubb wsa m Pmilqev halpqavtakuoi, lgouqdaf, kdmktsvmztsl, izr xoexghzr kkusitaaf. Vz wsa twbhdg ubalmmzhdad qz hce vmhsgohuqbo ox kaakulmd gxiwvos, krgdurdny i rcmmstugvtawz ca tzm ocicwxfg jf "stscmilpy" oid "uwydptsbuci" wabt hce Lcdwig eiovdnw. Bgfdny qe kddwtk qjnkqpsmev ba pz tzm roohwz at xoexghzr kkusicw izr vrlqrwxist uboedtuuznum. Pimifo Icmlv Emf DI, Lcdwig owdyzd xwd hce Ywhsmnemzh Xovm mby Cqxtsm Supacg (GUKE) oo Bdmfqclwg Bomk, Tzuhvif'a ocyetzqofifo ositjm. Rcm a lqys ce oie vzav wr Vpt 8, lpq gzclqab mekxabnittq tjr Ymdavn fihog cjgbhvnstkgds. Zm psqikmp o iuejqf jf lmoviiicqg aoj jdsvkavs Uzreiz qdpzmdg, dnutgrdny bts helpar jf lpq pjmtm, mb zlwkffjmwktoiiuix avczqzs ohsb ocplv nuby swbfwigk naf ohw Mzwbms umqcifm. Mtoej bts raj pq kjrcmp oo tzm Zooigvmz Khqauqvl Dincmalwdm, rhwzq vz cjmmhzd gvq ca tzm rwmsl lqgdgfa rcm a kbafzd-hzaumae kaakulmd, hce SKQ. Wi 1948 Tmzubb jgqzsy Msf Zsrmsv'e Qjmhcfwig Dincmalwdm vt Eizqcekbqf Pnadqfnilg, ivzrw pq onsaafsy if bts yenmxckmwvf ca tzm Yoiczmehzr uwydptwze oid tmoohe avfsmekbqr dn eifvzmsbuqvl tqazjgq. Pq kmolm m dvpwz ab ohw ktshiuix pvsaa at hojxtcbefmewn, afl bfzdakfsy okkuzgalqzu xhwuuqvl jmmqoigve gpcz ie hce Tmxcpsgd-Lvvbgbubnkq zqoxtawz, kciup isme xqdgo otaqfqev qz hce 1960k. Bgfdny'a tchokmjivlabk fzsmtfsy if i ofdmavmz krgaqqptawz wi 1952, wzmz vjmgaqlpad iohn wwzq goidt uzgeyix wi tzm Gbdtwl Wwigvwy. Vz aukqdoev bdsvtemzh rilp rshadm tcmmgvqg (xhwuuqvl uiehmalqab) vs sv mzoejvmhdvw ba dmikwz. Hpravs rdev qz 1954, xpsl whsm tow iszkk jqtjrw pug 42id tqdhcdsg, rfjm ugmbddw xawnofqzu. Vn avcizsl lqhzreqzsy tzif vds vmmhc wsa eidcalq; vds ewfvzr svp gjmw wfvzrk jqzdenmp vds vmmhc wsa mqxivmzhvl. Gv 10 Esktwunsm 2009, fgtxcrifo mb Dnlmdbzt uiydviyv, Nfdtaat Dmiem Ywiikbqf Bojlab Wrgez avdw iz cafakuog pmjxwx ahwxcby gv nscadn at ohw Jdwoikp scqejvysit xwd "hce sxboglavs kvy zm ion tjmmhzd." Sa at Haq 2012 i bfdvsbq azmtmd'g widt ion bwnafz tzm Tcpsw wr Zjrva ivdcz eaigd yzmbo Tmzubb a kbmhptgzk dvrvwz wa efiohzd."""

        self.assertEqual(procOut, expectedOutput)
        self.assertEqual(pyperclip.paste().decode('ascii'), expectedClipboard)

    """
    # The null cipher programs have been cut from the book.
    def test_nullCipherModule(self):
        import nullCipher
        encrypted = nullCipher.encryptMessage('5031', FOX_MESSAGE)
        decrypted = nullCipher.decryptMessage('5031', encrypted)
        self.assertEqual(FOX_MESSAGE, decrypted)
    """
if __name__ == '__main__':
    TEST_ALL = True

    if not TEST_ALL:
        customSuite = unittest.TestSuite()
        #customSuite.addTest(CodeHackerPyLint('test_rabinMillerPy'))
        customSuite.addTest(CodeBreakerUnitTests('test_simpleSubHackerProgram'))
        unittest.TextTestRunner().run(customSuite)
    elif TEST_ALL:
        unittest.main()

########NEW FILE########
__FILENAME__ = coinFlips
import random
print('I will flip a coin 1000 times. Guess how many times it will come up heads. (Press enter to begin)')
input('> ')
flips = 0
heads = 0
while flips < 1000:
    if random.randint(0, 1) == 1:
        heads = heads + 1
    flips = flips + 1

    if flips == 900:
        print('900 flips and there have been ' + str(heads) + ' heads.')
    if flips == 100:
        print('At 100 tosses, heads has come up ' + str(heads) + ' times so far.')
    if flips == 500:
        print('Half way done, and heads has come up ' + str(heads) + ' times.')

print()
print('Out of 1000 coin tosses, heads came up ' + str(heads) + ' times!')
print('Were you close?')
########NEW FILE########
__FILENAME__ = cryptomath
# Cryptomath Module
# http://inventwithpython.com/hacking (BSD Licensed)

def gcd(a, b):
    # Return the GCD of a and b using Euclid's Algorithm
    while a != 0:
        a, b = b % a, a
    return b


def findModInverse(a, m):
    # Returns the modular inverse of a % m, which is
    # the number x such that a*x % m = 1

    if gcd(a, m) != 1:
        return None # no mod inverse if a & m aren't relatively prime

    # Calculate using the Extended Euclidean Algorithm:
    u1, u2, u3 = 1, 0, a
    v1, v2, v3 = 0, 1, m
    while v3 != 0:
        q = u3 // v3 # // is the integer division operator
        v1, v2, v3, u1, u2, u3 = (u1 - q * v1), (u2 - q * v2), (u3 - q * v3), v1, v2, v3
    return u1 % m
########NEW FILE########
__FILENAME__ = detectEnglish
# Detect English module
# http://inventwithpython.com/hacking (BSD Licensed)

# To use, type this code:
#   import detectEnglish
#   detectEnglish.isEnglish(someString) # returns True or False
# (There must be a "dictionary.txt" file in this directory with all English
# words in it, one word per line. You can download this from
# http://invpy.com/dictionary.txt)
UPPERLETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LETTERS_AND_SPACE = UPPERLETTERS + UPPERLETTERS.lower() + ' \t\n'

def loadDictionary():
    dictionaryFile = open('dictionary.txt')
    englishWords = {}
    for word in dictionaryFile.read().split('\n'):
        englishWords[word] = None
    dictionaryFile.close()
    return englishWords

ENGLISH_WORDS = loadDictionary()


def getEnglishCount(message):
    message = message.upper()
    message = removeNonLetters(message)
    possibleWords = message.split()

    if possibleWords == []:
        return 0.0 # no words at all, so return 0.0

    matches = 0
    for word in possibleWords:
        if word in ENGLISH_WORDS:
            matches += 1
    return float(matches) / len(possibleWords)


def removeNonLetters(message):
    lettersOnly = []
    for symbol in message:
        if symbol in LETTERS_AND_SPACE:
            lettersOnly.append(symbol)
    return ''.join(lettersOnly)


def isEnglish(message, wordPercentage=20, letterPercentage=85):
    # By default, 20% of the words must exist in the dictionary file, and
    # 85% of all the characters in the message must be letters or spaces
    # (not punctuation or numbers).
    wordsMatch = getEnglishCount(message) * 100 >= wordPercentage
    numLetters = len(removeNonLetters(message))
    messageLettersPercentage = float(numLetters) / len(message) * 100
    lettersMatch = messageLettersPercentage >= letterPercentage
    return wordsMatch and lettersMatch
########NEW FILE########
__FILENAME__ = freqAnalysis
# Frequency Finder
# http://inventwithpython.com/hacking (BSD Licensed)



# frequency taken from http://en.wikipedia.org/wiki/Letter_frequency
englishLetterFreq = {'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97, 'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25, 'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36, 'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29, 'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15, 'Q': 0.10, 'Z': 0.07}
ETAOIN = 'ETAOINSHRDLCUMWFGYPBVKJXQZ'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'



def getLetterCount(message):
    # Returns a dictionary with keys of single letters and values of the
    # count of how many times they appear in the message parameter.
    letterCount = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 0, 'F': 0, 'G': 0, 'H': 0, 'I': 0, 'J': 0, 'K': 0, 'L': 0, 'M': 0, 'N': 0, 'O': 0, 'P': 0, 'Q': 0, 'R': 0, 'S': 0, 'T': 0, 'U': 0, 'V': 0, 'W': 0, 'X': 0, 'Y': 0, 'Z': 0}

    for letter in message.upper():
        if letter in LETTERS:
            letterCount[letter] += 1

    return letterCount


def getItemAtIndexZero(x):
    return x[0]


def getFrequencyOrder(message):
    # Returns a string of the alphabet letters arranged in order of most
    # frequently occurring in the message parameter.

    # first, get a dictionary of each letter and its frequency count
    letterToFreq = getLetterCount(message)

    # second, make a dictionary of each frequency count to each letter(s)
    # with that frequency
    freqToLetter = {}
    for letter in LETTERS:
        if letterToFreq[letter] not in freqToLetter:
            freqToLetter[letterToFreq[letter]] = [letter]
        else:
            freqToLetter[letterToFreq[letter]].append(letter)

    # third, put each list of letters in reverse "ETAOIN" order, and then
    # convert it to a string
    for freq in freqToLetter:
        freqToLetter[freq].sort(key=ETAOIN.find, reverse=True)
        freqToLetter[freq] = ''.join(freqToLetter[freq])

    # fourth, convert the freqToLetter dictionary to a list of tuple
    # pairs (key, value), then sort them
    freqPairs = list(freqToLetter.items())
    freqPairs.sort(key=getItemAtIndexZero, reverse=True)

    # fifth, now that the letters are ordered by frequency, extract all
    # the letters for the final string
    freqOrder = []
    for freqPair in freqPairs:
        freqOrder.append(freqPair[1])

    return ''.join(freqOrder)


def englishFreqMatchScore(message):
    # Return the number of matches that the string in the message
    # parameter has when its letter frequency is compared to English
    # letter frequency. A "match" is how many of its six most frequent
    # and six least frequent letters is among the six most frequent and
    # six least frequent letters for English.
    freqOrder = getFrequencyOrder(message)

    matchScore = 0
    # Find how many matches for the six most common letters there are.
    for commonLetter in ETAOIN[:6]:
        if commonLetter in freqOrder[:6]:
            matchScore += 1
    # Find how many matches for the six least common letters there are.
    for uncommonLetter in ETAOIN[-6:]:
        if uncommonLetter in freqOrder[-6:]:
            matchScore += 1

    return matchScore
########NEW FILE########
__FILENAME__ = freqFinder
# Frequency Finder
# http://inventwithpython.com/hacking (BSD Licensed)

# frequency taken from http://en.wikipedia.org/wiki/Letter_frequency
englishLetterFreq = {'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97, 'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25, 'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36, 'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29, 'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15, 'Q': 0.10, 'Z': 0.07}
englishTrigramFreq = {'THE': 3.51, 'AND': 1.59, 'ING': 1.15, 'HER': 0.82, 'HAT': 0.65, 'HIS': 0.60, 'THA': 0.59, 'ERE': 0.56, 'FOR': 0.56, 'ENT': 0.53, 'ION': 0.51, 'TER': 0.46, 'WAS': 0.46, 'YOU': 0.44, 'ITH': 0.43, 'VER': 0.43, 'ALL': 0.42, 'WIT': 0.40, 'THI': 0.39, 'TIO': 0.38}
englishFreqOrder = tuple('ETAOINSHRDLCUMWFGYPBVKJXQZ')
ETAOIN = ''.join(englishFreqOrder)
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

TRIGRAM_THRESHOLD = 2
TRIGRAM_MATCH_RANGE = 30


def getLetterCount(message):
    # Returns a dictionary with keys of single letters and values of the
    # count of how many times they appear in the message parameter.
    letterToCount = {}
    for letter in LETTERS:
        letterToCount[letter] = 0 # intialize each letter to 0

    for letter in message:
        if letter in LETTERS:
            letterToCount[letter] += 1

    return letterToCount


def getFrequencyOrder(message):
    # Returns a string of the alphabet letters arranged in order of most
    # frequently occurring in the message parameter.
    message = message.upper()

    # first, get a dictionary of each letter and its frequency count
    letterToFreq = getLetterCount(message)

    # second, make a dictionary of each frequency count to each letter(s)
    # with that frequency
    freqToLetter = {}
    for letter in LETTERS:
        freqToLetter[letterToFreq[letter]] = [] # start as a blank list

    for letter in LETTERS:
        freqToLetter[letterToFreq[letter]].append(letter)

    # third, put each list of letters in reverse "ETAOIN" order, and then
    # convert it to a string
    for freq in freqToLetter:
        freqToLetter[freq].sort(key=ETAOIN.find, reverse=True)
        freqToLetter[freq] = ''.join(freqToLetter[freq])

    # fourth, convert the freqToLetter dictionary to a list of tuple
    # pairs (key, value), then sort them
    freqPairs = list(freqToLetter.items())
    freqPairs.sort(key=lambda x: x[0], reverse=True)

    # fifth, now that the letters are ordered by frequency, extract all
    # the letters for the final string
    freqOrder = ''
    for freqPair in freqPairs:
        freqOrder += freqPair[1]

    return freqOrder


def englishFreqMatch(message):
    # Return the number of matches that the string in the message
    # parameter has when its letter frequency is compared to English
    # letter frequency. A "match" is how many of its six most frequent
    # and six least frequent letters is among the six most frequent and
    # six least frequent letters for English.
    freqOrder = getFrequencyOrder(message)

    matches = 0
    # Find how many matches for the six most common letters there are.
    for commonLetter in ETAOIN[:6]:
        if commonLetter in freqOrder[:6]:
            matches += 1
    # Find how many matches for the six least common letters there are.
    for uncommonLetter in ETAOIN[-6:]:
        if uncommonLetter in freqOrder[-6:]:
            matches += 1

    return matches


def englishTrigramMatch(message):
    # Return True if the string in the message parameter matches the
    # trigram frequency of English.

    # Remove the non-letter characters from message
    message = message.upper()
    lettersOnly = []
    for character in message:
        if character in LETTERS:
            lettersOnly.append(character)
    message = ''.join(lettersOnly)

    # Count the trigrams in message
    total = 0
    trigrams = {}
    for i in range(len(message) - 2):
        trigram = message[i:i+3]
        if trigram in trigrams:
            trigrams[trigram] += 1
        else:
            trigrams[trigram] = 1
        total += 1

    # Sort the trigrams by frequency
    topFreqs = list(trigrams.items())
    topFreqs.sort(key=lambda x: x[1], reverse=True)
    topFreqLetters = []
    for item in topFreqs:
        topFreqLetters.append(item[0])

    trigramFreqs = {}
    for trigram in trigrams:
        trigramFreqs[trigram] = trigrams[trigram] / total * 100

    matches = 0
    for commonTrig in englishTrigramFreq:
        if commonTrig in topFreqLetters[:TRIGRAM_MATCH_RANGE]:
            matches += 1

    return matches >= TRIGRAM_THRESHOLD
########NEW FILE########
__FILENAME__ = makeRsaKeys
# RSA Key Generator
# http://inventwithpython.com/hacking (BSD Licensed)

import random, sys, os, rabinMiller, cryptomath


def main():
    # create a public/private keypair with 1024 bit keys
    print('Making key files...')
    makeKeyFiles('al_sweigart', 1024)
    print('Key files made.')

def generateKey(keySize):
    # Creates a public/private key pair with keys that are keySize bits in
    # size. This function may take a while to run.

    # Step 1: Create two prime numbers, p and q. Calculate n = p * q.
    print('Generating p prime...')
    p = rabinMiller.generateLargePrime(keySize)
    print('Generating q prime...')
    q = rabinMiller.generateLargePrime(keySize)
    n = p * q

    # Step 2: Create a number e that is relatively prime to (p-1)*(q-1).
    print('Generating e that is relatively prime to (p-1)*(q-1)...')
    while True:
        # Keep trying random numbers for e until one is valid.
        e = random.randrange(2 ** (keySize - 1), 2 ** (keySize))
        if cryptomath.gcd(e, (p - 1) * (q - 1)) == 1:
            break

    # Step 3: Calculate d, the mod inverse of e.
    print('Calculating d that is mod inverse of e...')
    d = cryptomath.findModInverse(e, (p - 1) * (q - 1))

    publicKey = (n, e)
    privateKey = (n, d)

    print('Public key:', publicKey)
    print('Private key:', privateKey)

    return (publicKey, privateKey)


def makeKeyFiles(name, keySize):
    # Creates two files 'x_pubkey.txt' and 'x_privkey.txt' (where x is the
    # value in name) with the the n,e and d,e integers written in them,
    # delimited by a comma.

    # Our safety check will prevent us from overwriting our old key files:
    if os.path.exists('%s_pubkey.txt' % (name)) or os.path.exists('%s_privkey.txt' % (name)):
        sys.exit('WARNING: The file %s_pubkey.txt or %s_privkey.txt already exists! Use a different name or delete these files and re-run this program.' % (name, name))

    publicKey, privateKey = generateKey(keySize)

    print()
    print('The public key is a %s and a %s digit number.' % (len(str(publicKey[0])), len(str(publicKey[1]))))
    print('Writing public key to file %s_pubkey.txt...' % (name))
    fo = open('%s_pubkey.txt' % (name), 'w')
    fo.write('%s,%s,%s' % (keySize, publicKey[0], publicKey[1]))
    fo.close()

    print()
    print('The private key is a %s and a %s digit number.' % (len(str(publicKey[0])), len(str(publicKey[1]))))
    print('Writing private key to file %s_privkey.txt...' % (name))
    fo = open('%s_privkey.txt' % (name), 'w')
    fo.write('%s,%s,%s' % (keySize, privateKey[0], privateKey[1]))
    fo.close()


# If makeRsaKeys.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = makeWordPatterns
# Makes the wordPatterns.py File
# http://inventwithpython.com/hacking (BSD Licensed)

# Creates wordPatterns.py based on the words in our dictionary
# text file, dictionary.txt. (Download this file from
# http://invpy.com/dictionary.txt)

import pprint


def getWordPattern(word):
    # Returns a string of the pattern form of the given word.
    # e.g. '0.1.2.3.4.1.2.3.5.6' for 'DUSTBUSTER'
    word = word.upper()
    nextNum = 0
    letterNums = {}
    wordPattern = []

    for letter in word:
        if letter not in letterNums:
            letterNums[letter] = str(nextNum)
            nextNum += 1
        wordPattern.append(letterNums[letter])
    return '.'.join(wordPattern)


def main():
    allPatterns = {}

    fo = open('dictionary.txt')
    wordList = fo.read().split('\n')
    fo.close()

    for word in wordList:
        # Get the pattern for each string in wordList.
        pattern = getWordPattern(word)

        if pattern not in allPatterns:
            allPatterns[pattern] = [word]
        else:
            allPatterns[pattern].append(word)

    # This is code that writes code. The wordPatterns.py file contains
    # one very, very large assignment statement.
    fo = open('wordPatterns.py', 'w')
    fo.write('allPatterns = ')
    fo.write(pprint.pformat(allPatterns))
    fo.close()


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = nullCipher
# Null Cipher
# http://inventwithpython.com/hacking (BSD Licensed)
import random, pyperclip

myMessage = """When I use a word, it means just what I choose it to mean -- neither more nor less."""
myKey = '302'
mode = 'encrypt' # set to 'encrypt' or 'decrypt'


def main():
    if mode == 'encrypt':
        translated = encryptMessage(myKey, myMessage)
    elif mode == 'decrypt':
        translated = decryptMessage(myKey, myMessage)

    print('%sed message: ' % (mode.title()) + translated)
    print('The message has been copied to the clipboard.')
    pyperclip.copy(translated)


def encryptMessage(key, message):
    # The expression int(key[keyIndex]) will be used to decide how many
    # nulls should be inserted. For example, if key is the value '570'
    # and keyIndex is 0, then 5 null characters will be inserted into
    # the ciphertext.
    keyIndex = 0

    ciphertext = '' # will contain the encrypted string
    for symbol in list(message) + [None]:
        for dummy in range(int(key[keyIndex])):
            # Add a null.
            ciphertext += random.choice(myMessage)

        if symbol == None:
            break # the None value marks the end

        # Increment keyIndex so that on the next iteration, we use a
        # number of nulls specified by the next character in key.
        keyIndex += 1
        if keyIndex == len(key):
            # keyIndex is past the end, so reset it back to 0.
            keyIndex = 0

        # Add the real symbol after adding the nulls.
        ciphertext += symbol
    return ciphertext


def decryptMessage(key, message):
    # The value inside messageIndex will refer to the index we are
    # currently looking at in message.
    messageIndex = 0
    keyIndex = 0

    plaintext = '' # will contain the decrypted string

    while True:
        # The expression int(key[keyIndex]) will give us the int value of
        # how many nulls to skip over. We will increment the value in
        # messageIndex by this amount.
        messageIndex += int(key[keyIndex])

        if messageIndex >= len(message):
            # When messageIndex is past the last index, we are done.
            break

        # Increment keyIndex so that on the next iteration, we
        # use a number of nulls specified by the next character in key.
        keyIndex += 1
        if keyIndex == len(key):
            keyIndex = 0

        # Append the symbol at messageIndex to the plaintext variable.
        plaintext += message[messageIndex]
        messageIndex += 1

    return plaintext


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = nullHacker
# Null Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import nullCipher, pyperclip, detectEnglish, itertools

# There are two settings our hacking program needs to limit the range of
# the possible keys it checks.
# MAX_KEY_NUMBER is the range of numbers it checks for each number in the
# key. A MAX_KEY_NUMBER value of 9 means it will check 0 through 9.
# MAX_KEY_DIGITS is the largest amount of numbers in the key. A value of 5
# means that the key could be something like '1 2 3 4 5' or '1 1 1 1 1' or
# '1 2 3 4', but not '1 2 3 4 5 6'
# If these numbers are too large, then hacking the code will take a long
# time. If these numbers are too small, then the hacking program won't be
# able to hack the encryption.

MAX_KEY_NUMBER = 9
MAX_KEY_DIGITS = 5

SILENT_MODE = False

# This can be copy/pasted from http://invpy.com/nullHacker.py
myMessage = """sn Wht eetan mnIeu  uedswsae aiaeh  wh ohh rdrh,  h ihotote muoeh  annesets jtwunetst - e-rwhe am jt   Inoo c,nh   oossssace oai o t oWth.no   miiteaton r  -s -ou  nwse. nito hwiieroe s imoiorot e o nsesorer  anletesmt s.ah"""


def main():
    # Calculate the number of keys that the current MAX_KEY_DIGITS and
    # MAX_KEY_NUMBER values will cause the hacker program to go through.
    possibleKeys = 0 # start the number of keys at 0.
    for i in range(1, MAX_KEY_DIGITS + 1):
        # To find the total number of possible keys, add the total number
        # of keys for 1-digit keys, 2-digit keys, and so on up to
        # MAX_KEY_DIGITS-digit keys.
        # To find the number of keys with i digits in them, multiply the
        # range of numbers (that is, MAX_KEY_NUMBER) by itself i times.
        # That is, we find MAX_KEY_NUMBER to the ith power.
        possibleKeys += MAX_KEY_NUMBER ** i

    # After exiting the loop, the value in possibleKeys is the total number
    # of keys for MAX_KEY_NUMBER and MAX_KEY_RANGE.
    print('Max key number: %s' % MAX_KEY_NUMBER)
    print('Max key length: %s' % MAX_KEY_DIGITS)
    print('Possible keys to try: %s' % (possibleKeys))
    print()

    # Python programs can be stopped at any time by pressing Ctrl-C (on
    # Windows) or Ctrl-D (on Mac and Linux)
    print('(Press Ctrl-C or Ctrl-D to quit at any time.)')
    print('Hacking...')

    brokenMessage = hackNull(myMessage)

    if brokenMessage != None:
        print('Copying broken message to clipboard:')
        print(brokenMessage)
        pyperclip.copy(brokenMessage)
    else:
        print('Failed to hack encryption.')


def hackNull(ciphertext):
    # The program needs to try keys of length 1 (such as '5'), of length 2
    # (such as '5 3'), and so on up to length MAX_KEY_DIGITS.
    for keyLength in range(1, MAX_KEY_DIGITS + 1):
        for keyParts in itertools.product(range(MAX_KEY_NUMBER + 1), repeat=keyLength):
            key = []
            for digit in keyParts:
                key.append(str(digit))
            key = ''.join(key)

            decryptedText = nullCipher.decryptMessage(key, ciphertext)

            if not SILENT_MODE:
                print('Key %s: %s' % (key, decryptedText[:40]))

            if detectEnglish.isEnglish(decryptedText):
                print()
                print('Possible encryption hack:')
                print('Key: %s' % (key))
                print('Decrypted message: ' + decryptedText[:200])
                print()
                print('Enter D for done, or just press Enter to continue hacking:')
                response = input('> ')

                if response.strip().upper().startswith('D'):
                    return decryptedText
    return None # failed to hack encryption


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = primeSieve
# Prime Number Sieve
# http://inventwithpython.com/hacking (BSD Licensed)

import math


def isPrime(num):
    # Returns True if num is a prime number, otherwise False.

    # Note: Generally, isPrime() is slower than primeSieve().

    # all numbers less than 2 are not prime
    if num < 2:
        return False

    # see if num is divisible by any number up to the square root of num
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return False
    return True


def primeSieve(sieveSize):
    # Returns a list of prime numbers calculated using
    # the Sieve of Eratosthenes algorithm.

    sieve = [True] * sieveSize
    sieve[0] = False # zero and one are not prime numbers
    sieve[1] = False

    # create the sieve
    for i in range(2, int(math.sqrt(sieveSize)) + 1):
        pointer = i * 2
        while pointer < sieveSize:
            sieve[pointer] = False
            pointer += i

    # compile the list of primes
    primes = []
    for i in range(sieveSize):
        if sieve[i] == True:
            primes.append(i)

    return primes

########NEW FILE########
__FILENAME__ = pyperclip
# Pyperclip v1.4

# A cross-platform clipboard module for Python. (only handles plain text for now)
# By Al Sweigart al@coffeeghost.net

# Usage:
#   import pyperclip
#   pyperclip.copy('The text to be copied to the clipboard.')
#   spam = pyperclip.paste()

# On Mac, this module makes use of the pbcopy and pbpaste commands, which should come with the os.
# On Linux, this module makes use of the xclip command, which should come with the os. Otherwise run "sudo apt-get install xclip"


# Copyright (c) 2010, Albert Sweigart
# All rights reserved.
#
# BSD-style license:
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the pyperclip nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY Albert Sweigart "AS IS" AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Albert Sweigart BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Change Log:
# 1.2 Use the platform module to help determine OS.
# 1.3 Changed ctypes.windll.user32.OpenClipboard(None) to ctypes.windll.user32.OpenClipboard(0), after some people ran into some TypeError

import platform, os

def winGetClipboard():
    ctypes.windll.user32.OpenClipboard(0)
    pcontents = ctypes.windll.user32.GetClipboardData(1) # 1 is CF_TEXT
    data = ctypes.c_char_p(pcontents).value
    #ctypes.windll.kernel32.GlobalUnlock(pcontents)
    ctypes.windll.user32.CloseClipboard()
    return data

def winSetClipboard(text):
    text = str(text)
    GMEM_DDESHARE = 0x2000
    ctypes.windll.user32.OpenClipboard(0)
    ctypes.windll.user32.EmptyClipboard()
    try:
        # works on Python 2 (bytes() only takes one argument)
        hCd = ctypes.windll.kernel32.GlobalAlloc(GMEM_DDESHARE, len(bytes(text))+1)
    except TypeError:
        # works on Python 3 (bytes() requires an encoding)
        hCd = ctypes.windll.kernel32.GlobalAlloc(GMEM_DDESHARE, len(bytes(text, 'ascii'))+1)
    pchData = ctypes.windll.kernel32.GlobalLock(hCd)
    try:
        # works on Python 2 (bytes() only takes one argument)
        ctypes.cdll.msvcrt.strcpy(ctypes.c_char_p(pchData), bytes(text))
    except TypeError:
        # works on Python 3 (bytes() requires an encoding)
        ctypes.cdll.msvcrt.strcpy(ctypes.c_char_p(pchData), bytes(text, 'ascii'))
    ctypes.windll.kernel32.GlobalUnlock(hCd)
    ctypes.windll.user32.SetClipboardData(1, hCd)
    ctypes.windll.user32.CloseClipboard()

def macSetClipboard(text):
    text = str(text)
    outf = os.popen('pbcopy', 'w')
    outf.write(text)
    outf.close()

def macGetClipboard():
    outf = os.popen('pbpaste', 'r')
    content = outf.read()
    outf.close()
    return content

def gtkGetClipboard():
    return gtk.Clipboard().wait_for_text()

def gtkSetClipboard(text):
    global cb
    text = str(text)
    cb = gtk.Clipboard()
    cb.set_text(text)
    cb.store()

def qtGetClipboard():
    return str(cb.text())

def qtSetClipboard(text):
    text = str(text)
    cb.setText(text)

def xclipSetClipboard(text):
    text = str(text)
    outf = os.popen('xclip -selection c', 'w')
    outf.write(text)
    outf.close()

def xclipGetClipboard():
    outf = os.popen('xclip -selection c -o', 'r')
    content = outf.read()
    outf.close()
    return content

def xselSetClipboard(text):
    text = str(text)
    outf = os.popen('xsel -i', 'w')
    outf.write(text)
    outf.close()

def xselGetClipboard():
    outf = os.popen('xsel -o', 'r')
    content = outf.read()
    outf.close()
    return content


if os.name == 'nt' or platform.system() == 'Windows':
    import ctypes
    getcb = winGetClipboard
    setcb = winSetClipboard
elif os.name == 'mac' or platform.system() == 'Darwin':
    getcb = macGetClipboard
    setcb = macSetClipboard
elif os.name == 'posix' or platform.system() == 'Linux':
    xclipExists = os.system('which xclip') == 0
    if xclipExists:
        getcb = xclipGetClipboard
        setcb = xclipSetClipboard
    else:
        xselExists = os.system('which xsel') == 0
        if xselExists:
            getcb = xselGetClipboard
            setcb = xselSetClipboard
        try:
            import gtk
            getcb = gtkGetClipboard
            setcb = gtkSetClipboard
        except Exception:
            try:
                import PyQt4.QtCore
                import PyQt4.QtGui
                app = PyQt4.QApplication([])
                cb = PyQt4.QtGui.QApplication.clipboard()
                getcb = qtGetClipboard
                setcb = qtSetClipboard
            except:
                raise Exception('Pyperclip requires the gtk or PyQt4 module installed, or the xclip command.')
copy = setcb
paste = getcb
########NEW FILE########
__FILENAME__ = rabinMiller
# Primality Testing with the Rabin-Miller Algorithm
# http://inventwithpython.com/hacking (BSD Licensed)

import random


def rabinMiller(num):
    # Returns True if num is a prime number.

    s = num - 1
    t = 0
    while s % 2 == 0:
        # keep halving s while it is even (and use t
        # to count how many times we halve s)
        s = s // 2
        t += 1

    for trials in range(5): # try to falsify num's primality 5 times
        a = random.randrange(2, num - 1)
        v = pow(a, s, num)
        if v != 1: # this test does not apply if v is 1.
            i = 0
            while v != (num - 1):
                if i == t - 1:
                    return False
                else:
                    i = i + 1
                    v = (v ** 2) % num
    return True


def isPrime(num):
    # Return True if num is a prime number. This function does a quicker
    # prime number check before calling rabinMiller().

    if (num < 2):
        return False # 0, 1, and negative numbers are not prime

    # About 1/3 of the time we can quickly determine if num is not prime
    # by dividing by the first few dozen prime numbers. This is quicker
    # than rabinMiller(), but unlike rabinMiller() is not guaranteed to
    # prove that a number is prime.
    lowPrimes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997]

    if num in lowPrimes:
        return True

    # See if any of the low prime numbers can divide num
    for prime in lowPrimes:
        if (num % prime == 0):
            return False

    # If all else fails, call rabinMiller() to determine if num is a prime.
    return rabinMiller(num)


def generateLargePrime(keysize=1024):
    # Return a random prime number of keysize bits in size.
    while True:
        num = random.randrange(2**(keysize-1), 2**(keysize))
        if isPrime(num):
            return num
########NEW FILE########
__FILENAME__ = reverseCipher
# Reverse Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

message = 'Three can keep a secret, if two of them are dead.'
translated = ''

i = len(message) - 1
while i >= 0:
    translated = translated + message[i]
    i = i - 1

print(translated)
########NEW FILE########
__FILENAME__ = rsaCipher
# RSA Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import sys

# IMPORTANT: The block size MUST be less than or equal to the key size!
# (Note: The block size is in bytes, the key size is in bits. There
# are 8 bits in 1 byte.)
DEFAULT_BLOCK_SIZE = 128 # 128 bytes
BYTE_SIZE = 256 # One byte has 256 different values.

def main():
    # Runs a test that encrypts a message to a file or decrypts a message
    # from a file.
    filename = 'encrypted_file.txt' # the file to write to/read from
    mode = 'encrypt' # set to 'encrypt' or 'decrypt'

    if mode == 'encrypt':
        message = '''"Journalists belong in the gutter because that is where the ruling classes throw their guilty secrets." -Gerald Priestland "The Founding Fathers gave the free press the protection it must have to bare the secrets of government and inform the people." -Hugo Black'''
        pubKeyFilename = 'al_sweigart_pubkey.txt'
        print('Encrypting and writing to %s...' % (filename))
        encryptedText = encryptAndWriteToFile(filename, pubKeyFilename, message)

        print('Encrypted text:')
        print(encryptedText)

    elif mode == 'decrypt':
        privKeyFilename = 'al_sweigart_privkey.txt'
        print('Reading from %s and decrypting...' % (filename))
        decryptedText = readFromFileAndDecrypt(filename, privKeyFilename)

        print('Decrypted text:')
        print(decryptedText)


def getBlocksFromText(message, blockSize=DEFAULT_BLOCK_SIZE):
    # Converts a string message to a list of block integers. Each integer
    # represents 128 (or whatever blockSize is set to) string characters.

    messageBytes = message.encode('ascii') # convert the string to bytes

    blockInts = []
    for blockStart in range(0, len(messageBytes), blockSize):
        # Calculate the block integer for this block of text
        blockInt = 0
        for i in range(blockStart, min(blockStart + blockSize, len(messageBytes))):
            blockInt += messageBytes[i] * (BYTE_SIZE ** (i % blockSize))
        blockInts.append(blockInt)
    return blockInts


def getTextFromBlocks(blockInts, messageLength, blockSize=DEFAULT_BLOCK_SIZE):
    # Converts a list of block integers to the original message string.
    # The original message length is needed to properly convert the last
    # block integer.
    message = []
    for blockInt in blockInts:
        blockMessage = []
        for i in range(blockSize - 1, -1, -1):
            if len(message) + i < messageLength:
                # Decode the message string for the 128 (or whatever
                # blockSize is set to) characters from this block integer.
                asciiNumber = blockInt // (BYTE_SIZE ** i)
                blockInt = blockInt % (BYTE_SIZE ** i)
                blockMessage.insert(0, chr(asciiNumber))
        message.extend(blockMessage)
    return ''.join(message)


def encryptMessage(message, key, blockSize=DEFAULT_BLOCK_SIZE):
    # Converts the message string into a list of block integers, and then
    # encrypts each block integer. Pass the PUBLIC key to encrypt.
    encryptedBlocks = []
    n, e = key

    for block in getBlocksFromText(message, blockSize):
        # ciphertext = plaintext ^ e mod n
        encryptedBlocks.append(pow(block, e, n))
    return encryptedBlocks


def decryptMessage(encryptedBlocks, messageLength, key, blockSize=DEFAULT_BLOCK_SIZE):
    # Decrypts a list of encrypted block ints into the original message
    # string. The original message length is required to properly decrypt
    # the last block. Be sure to pass the PRIVATE key to decrypt.
    decryptedBlocks = []
    n, d = key
    for block in encryptedBlocks:
        # plaintext = ciphertext ^ d mod n
        decryptedBlocks.append(pow(block, d, n))
    return getTextFromBlocks(decryptedBlocks, messageLength, blockSize)


def readKeyFile(keyFilename):
    # Given the filename of a file that contains a public or private key,
    # return the key as a (n,e) or (n,d) tuple value.
    fo = open(keyFilename)
    content = fo.read()
    fo.close()
    keySize, n, EorD = content.split(',')
    return (int(keySize), int(n), int(EorD))


def encryptAndWriteToFile(messageFilename, keyFilename, message, blockSize=DEFAULT_BLOCK_SIZE):
    # Using a key from a key file, encrypt the message and save it to a
    # file. Returns the encrypted message string.
    keySize, n, e = readKeyFile(keyFilename)

    # Check that key size is greater than block size.
    if keySize < blockSize * 8: # * 8 to convert bytes to bits
        sys.exit('ERROR: Block size is %s bits and key size is %s bits. The RSA cipher requires the block size to be equal to or less than the key size. Either increase the block size or use different keys.' % (blockSize * 8, keySize))


    # Encrypt the message
    encryptedBlocks = encryptMessage(message, (n, e), blockSize)

    # Convert the large int values to one string value.
    for i in range(len(encryptedBlocks)):
        encryptedBlocks[i] = str(encryptedBlocks[i])
    encryptedContent = ','.join(encryptedBlocks)

    # Write out the encrypted string to the output file.
    encryptedContent = '%s_%s_%s' % (len(message), blockSize, encryptedContent)
    fo = open(messageFilename, 'w')
    fo.write(encryptedContent)
    fo.close()
    # Also return the encrypted string.
    return encryptedContent


def readFromFileAndDecrypt(messageFilename, keyFilename):
    # Using a key from a key file, read an encrypted message from a file
    # and then decrypt it. Returns the decrypted message string.
    keySize, n, d = readKeyFile(keyFilename)


    # Read in the message length and the encrypted message from the file.
    fo = open(messageFilename)
    content = fo.read()
    messageLength, blockSize, encryptedMessage = content.split('_')
    messageLength = int(messageLength)
    blockSize = int(blockSize)

    # Check that key size is greater than block size.
    if keySize < blockSize * 8: # * 8 to convert bytes to bits
        sys.exit('ERROR: Block size is %s bits and key size is %s bits. The RSA cipher requires the block size to be equal to or less than the key size. Did you specify the correct key file and encrypted file?' % (blockSize * 8, keySize))

    # Convert the encrypted message into large int values.
    encryptedBlocks = []
    for block in encryptedMessage.split(','):
        encryptedBlocks.append(int(block))

    # Decrypt the large int values.
    return decryptMessage(encryptedBlocks, messageLength, (n, d), blockSize)


# If rsaCipher.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = simpleSubCipher
# Simple Substitution Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip, sys, random


LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def main():
    myMessage = 'If a man is offered a fact which goes against his instincts, he will scrutinize it closely, and unless the evidence is overwhelming, he will refuse to believe it. If, on the other hand, he is offered something which affords a reason for acting in accordance to his instincts, he will accept it even on the slightest evidence. The origin of myths is explained in this way. -Bertrand Russell'
    myKey = 'LFWOAYUISVKMNXPBDCRJTQEGHZ'
    myMode = 'encrypt' # set to 'encrypt' or 'decrypt'

    checkValidKey(myKey)

    if myMode == 'encrypt':
        translated = encryptMessage(myKey, myMessage)
    elif myMode == 'decrypt':
        translated = decryptMessage(myKey, myMessage)
    print('Using key %s' % (myKey))
    print('The %sed message is:' % (myMode))
    print(translated)
    pyperclip.copy(translated)
    print()
    print('This message has been copied to the clipboard.')


def checkValidKey(key):
    keyList = list(key)
    lettersList = list(LETTERS)
    keyList.sort()
    lettersList.sort()
    if keyList != lettersList:
        sys.exit('There is an error in the key or symbol set.')


def encryptMessage(key, message):
    return translateMessage(key, message, 'encrypt')


def decryptMessage(key, message):
    return translateMessage(key, message, 'decrypt')


def translateMessage(key, message, mode):
    translated = ''
    charsA = LETTERS
    charsB = key
    if mode == 'decrypt':
        # For decrypting, we can use the same code as encrypting. We
        # just need to swap where the key and LETTERS strings are used.
        charsA, charsB = charsB, charsA

    # loop through each symbol in the message
    for symbol in message:
        if symbol.upper() in charsA:
            # encrypt/decrypt the symbol
            symIndex = charsA.find(symbol.upper())
            if symbol.isupper():
                translated += charsB[symIndex].upper()
            else:
                translated += charsB[symIndex].lower()
        else:
            # symbol is not in LETTERS, just add it
            translated += symbol

    return translated


def getRandomKey():
    key = list(LETTERS)
    random.shuffle(key)
    return ''.join(key)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = simpleSubDictionaryHacker
# Simple Substitution Dictionary Hacker, http://inventwithpython.com/hacking (BSD Licensed)
import pyperclip, simpleSubKeyword, detectEnglish

SILENT_MODE = False

def main():
    myMessage = r"""SJITDOPIQR: JIR RIQMUNQRO AY P WDQC QCR NRSMRQN JT A SJITDORO QJ CRMNRGT AY S. -PHAMJNR ADRMSR"""

    brokenCiphertext = hackSimpleSubDictionary(myMessage)

    if brokenCiphertext == None:
        # hackSimpleSubDictionary() will return the None value if it was unable to hack the encryption.
        print('Hacking failed. Unable to hack this ciphertext.')
    else:
        # The plaintext is displayed on the screen. For the convenience of the user, we copy the text of the code to the clipboard.
        print('Copying broken ciphertext to clipboard:')
        print(brokenCiphertext)
        pyperclip.copy(brokenCiphertext)


def hackSimpleSubDictionary(message):
    print('Hacking with %s possible dictionary words...' % (len(detectEnglish.ENGLISH_WORDS) * 3))

    # Python programs can be stopped at any time by pressing Ctrl-C (on Windows) or Ctrl-D (on Mac and Linux)
    print('(Press Ctrl-C or Ctrl-D to quit at any time.)')

    tryNum = 1

    # brute-force by looping through every possible key
    for key in detectEnglish.ENGLISH_WORDS:
        if tryNum % 100 == 0 and not SILENT_MODE:
            print('%s keys tried. (%s)' % (tryNum, key))

        decryptedText = simpleSubKeyword.decryptMessage(key, message)

        if detectEnglish.getEnglishCount(decryptedText) > 0.20:
            # Check with the user to see if the decrypted key has been found.
            print()
            print('Possible encryption hack:')
            print('Key: ' + str(key))
            print('Decrypted message: ' + decryptedText[:100])
            print()
            print('Enter D for done, or just press Enter to continue hacking:')
            response = input('> ')

            if response.upper().startswith('D'):
                return decryptedText

        tryNum += 1
    return None

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = simpleSubHacker
# Simple Substitution Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import os, re, copy, pprint, pyperclip, simpleSubCipher, makeWordPatterns

if not os.path.exists('wordPatterns.py'):
    makeWordPatterns.main() # create the wordPatterns.py file
import wordPatterns

LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
nonLettersOrSpacePattern = re.compile('[^A-Z\s]')

def main():
    message = 'Sy l nlx sr pyyacao l ylwj eiswi upar lulsxrj isr sxrjsxwjr, ia esmm rwctjsxsza sj wmpramh, lxo txmarr jia aqsoaxwa sr pqaceiamnsxu, ia esmm caytra jp famsaqa sj. Sy, px jia pjiac ilxo, ia sr pyyacao rpnajisxu eiswi lyypcor l calrpx ypc lwjsxu sx lwwpcolxwa jp isr sxrjsxwjr, ia esmm lwwabj sj aqax px jia rmsuijarj aqsoaxwa. Jia pcsusx py nhjir sr agbmlsxao sx jisr elh. -Facjclxo Ctrramm'

    # Determine the possible valid ciphertext translations.
    print('Hacking...')
    letterMapping = hackSimpleSub(message)

    # Display the results to the user.
    print('Mapping:')
    pprint.pprint(letterMapping)
    print()
    print('Original ciphertext:')
    print(message)
    print()
    print('Copying hacked message to clipboard:')
    hackedMessage = decryptWithCipherletterMapping(message, letterMapping)
    pyperclip.copy(hackedMessage)
    print(hackedMessage)


def getBlankCipherletterMapping():
    # Returns a dictionary value that is a blank cipherletter mapping.
    return {'A': [], 'B': [], 'C': [], 'D': [], 'E': [], 'F': [], 'G': [], 'H': [], 'I': [], 'J': [], 'K': [], 'L': [], 'M': [], 'N': [], 'O': [], 'P': [], 'Q': [], 'R': [], 'S': [], 'T': [], 'U': [], 'V': [], 'W': [], 'X': [], 'Y': [], 'Z': []}


def addLettersToMapping(letterMapping, cipherword, candidate):
    # The letterMapping parameter is a "cipherletter mapping" dictionary
    # value that the return value of this function starts as a copy of.
    # The cipherword parameter is a string value of the ciphertext word.
    # The candidate parameter is a possible English word that the
    # cipherword could decrypt to.

    # This function adds the letters of the candidate as potential
    # decryption letters for the cipherletters in the cipherletter
    # mapping.

    letterMapping = copy.deepcopy(letterMapping)
    for i in range(len(cipherword)):
        if candidate[i] not in letterMapping[cipherword[i]]:
            letterMapping[cipherword[i]].append(candidate[i])
    return letterMapping


def intersectMappings(mapA, mapB):
    # To intersect two maps, create a blank map, and then add only the
    # potential decryption letters if they exist in BOTH maps.
    intersectedMapping = getBlankCipherletterMapping()
    for letter in LETTERS:

        # An empty list means "any letter is possible". In this case just
        # copy the other map entirely.
        if mapA[letter] == []:
            intersectedMapping[letter] = copy.deepcopy(mapB[letter])
        elif mapB[letter] == []:
            intersectedMapping[letter] = copy.deepcopy(mapA[letter])
        else:
            # If a letter in mapA[letter] exists in mapB[letter], add
            # that letter to intersectedMapping[letter].
            for mappedLetter in mapA[letter]:
                if mappedLetter in mapB[letter]:
                    intersectedMapping[letter].append(mappedLetter)

    return intersectedMapping


def removeSolvedLettersFromMapping(letterMapping):
    # Cipher letters in the mapping that map to only one letter are
    # "solved" and can be removed from the other letters.
    # For example, if 'A' maps to potential letters ['M', 'N'], and 'B'
    # maps to ['N'], then we know that 'B' must map to 'N', so we can
    # remove 'N' from the list of what 'A' could map to. So 'A' then maps
    # to ['M']. Note that now that 'A' maps to only one letter, we can
    # remove 'M' from the list of letters for every other
    # letter. (This is why there is a loop that keeps reducing the map.)
    letterMapping = copy.deepcopy(letterMapping)
    loopAgain = True
    while loopAgain:
        # First assume that we will not loop again:
        loopAgain = False

        # solvedLetters will be a list of uppercase letters that have one
        # and only one possible mapping in letterMapping
        solvedLetters = []
        for cipherletter in LETTERS:
            if len(letterMapping[cipherletter]) == 1:
                solvedLetters.append(letterMapping[cipherletter][0])

        # If a letter is solved, than it cannot possibly be a potential
        # decryption letter for a different ciphertext letter, so we
        # should remove it from those other lists.
        for cipherletter in LETTERS:
            for s in solvedLetters:
                if len(letterMapping[cipherletter]) != 1 and s in letterMapping[cipherletter]:
                    letterMapping[cipherletter].remove(s)
                    if len(letterMapping[cipherletter]) == 1:
                        # A new letter is now solved, so loop again.
                        loopAgain = True
    return letterMapping


def hackSimpleSub(message):
    intersectedMap = getBlankCipherletterMapping()
    cipherwordList = nonLettersOrSpacePattern.sub('', message.upper()).split()
    for cipherword in cipherwordList:
        # Get a new cipherletter mapping for each ciphertext word.
        newMap = getBlankCipherletterMapping()

        wordPattern = makeWordPatterns.getWordPattern(cipherword)
        if wordPattern not in wordPatterns.allPatterns:
            continue # This word was not in our dictionary, so continue.

        # Add the letters of each candidate to the mapping.
        for candidate in wordPatterns.allPatterns[wordPattern]:
            newMap = addLettersToMapping(newMap, cipherword, candidate)

        # Intersect the new mapping with the existing intersected mapping.
        intersectedMap = intersectMappings(intersectedMap, newMap)

    # Remove any solved letters from the other lists.
    return removeSolvedLettersFromMapping(intersectedMap)


def decryptWithCipherletterMapping(ciphertext, letterMapping):
    # Return a string of the ciphertext decrypted with the letter mapping,
    # with any ambiguous decrypted letters replaced with an _ underscore.

    # First create a simple sub key from the letterMapping mapping.
    key = ['x'] * len(LETTERS)
    for cipherletter in LETTERS:
        if len(letterMapping[cipherletter]) == 1:
            # If there's only one letter, add it to the key.
            keyIndex = LETTERS.find(letterMapping[cipherletter][0])
            key[keyIndex] = cipherletter
        else:
            ciphertext = ciphertext.replace(cipherletter.lower(), '_')
            ciphertext = ciphertext.replace(cipherletter.upper(), '_')
    key = ''.join(key)

    # With the key we've created, decrypt the ciphertext.
    return simpleSubCipher.decryptMessage(key, ciphertext)


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = simpleSubKeyword
# Simple Substitution Keyword Cipher
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip, simpleSubCipher

def main():
    myMessage = r"""Your cover is blown."""
    myKey = 'alphanumeric'
    myMode = 'encrypt' # set to 'encrypt' or 'decrypt'


    print('The key used is:')
    print(makeSimpleSubKey(myKey))

    if myMode == 'encrypt':
        translated = encryptMessage(myKey, myMessage)
    elif myMode == 'decrypt':
        translated = decryptMessage(myKey, myMessage)

    print('The %sed message is:' % (myMode))
    print(translated)

    pyperclip.copy(translated)
    print()
    print('This message has been copied to the clipboard.')


def encryptMessage(key, message):
    key = makeSimpleSubKey(key)
    return simpleSubCipher.encryptMessage(key, message)


def decryptMessage(key, message):
    key = makeSimpleSubKey(key)
    return simpleSubCipher.decryptMessage(key, message)


def makeSimpleSubKey(keyword):
    # create the key from the keyword
    newKey = ''
    keyword = keyword.upper()
    keyAlphabet = list(simpleSubCipher.LETTERS)
    for i in range(len(keyword)):
        if keyword[i] not in newKey:
            newKey += keyword[i]
            keyAlphabet.remove(keyword[i])
    key = newKey + ''.join(keyAlphabet)
    return key


if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = transpositionDecrypt
# Transposition Cipher Decryption
# http://inventwithpython.com/hacking (BSD Licensed)

import math, pyperclip

def main():
    myMessage = 'Cenoonommstmme oo snnio. s s c'
    myKey = 8

    plaintext = decryptMessage(myKey, myMessage)

    # Print with a | (called "pipe" character) after it in case
    # there are spaces at the end of the decrypted message.
    print(plaintext + '|')

    pyperclip.copy(plaintext)


def decryptMessage(key, message):
    # The transposition decrypt function will simulate the "columns" and
    # "rows" of the grid that the plaintext is written on by using a list
    # of strings. First, we need to calculate a few values.

    # The number of "columns" in our transposition grid:
    numOfColumns = math.ceil(len(message) / key)
    # The number of "rows" in our grid will need:
    numOfRows = key
    # The number of "shaded boxes" in the last "column" of the grid:
    numOfShadedBoxes = (numOfColumns * numOfRows) - len(message)

    # Each string in plaintext represents a column in the grid.
    plaintext = [''] * numOfColumns

    # The col and row variables point to where in the grid the next
    # character in the encrypted message will go.
    col = 0
    row = 0

    for symbol in message:
        plaintext[col] += symbol
        col += 1 # point to next column

        # If there are no more columns OR we're at a shaded box, go back to
        # the first column and the next row.
        if (col == numOfColumns) or (col == numOfColumns - 1 and row >= numOfRows - numOfShadedBoxes):
            col = 0
            row += 1

    return ''.join(plaintext)


# If transpositionDecrypt.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = transpositionEncrypt
# Transposition Cipher Encryption
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip

def main():
    myMessage = 'Common sense is not so common.'
    myKey = 8

    ciphertext = encryptMessage(myKey, myMessage)

    # Print the encrypted string in ciphertext to the screen, with
    # a | (called "pipe" character) after it in case there are spaces at
    # the end of the encrypted message.
    print(ciphertext + '|')

    # Copy the encrypted string in ciphertext to the clipboard.
    pyperclip.copy(ciphertext)


def encryptMessage(key, message):
    # Each string in ciphertext represents a column in the grid.
    ciphertext = [''] * key

    # Loop through each column in ciphertext.
    for col in range(key):
        pointer = col

        # Keep looping until pointer goes past the length of the message.
        while pointer < len(message):
            # Place the character at pointer in message at the end of the
            # current column in the ciphertext list.
            ciphertext[col] += message[pointer]

            # move pointer over
            pointer += key

    # Convert the ciphertext list into a single string value and return it.
    return ''.join(ciphertext)


# If transpositionEncrypt.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = transpositionFileCipher
# Transposition Cipher Encrypt/Decrypt File
# http://inventwithpython.com/hacking (BSD Licensed)

import time, os, sys, transpositionEncrypt, transpositionDecrypt

def main():
    inputFilename = 'frankenstein.txt'
    # BE CAREFUL! If a file with the outputFilename name already exists,
    # this program will overwrite that file.
    outputFilename = 'frankenstein.encrypted.txt'
    myKey = 10
    myMode = 'encrypt' # set to 'encrypt' or 'decrypt'

    # If the input file does not exist, then the program terminates early.
    if not os.path.exists(inputFilename):
        print('The file %s does not exist. Quitting...' % (inputFilename))
        sys.exit()

    # If the output file already exists, give the user a chance to quit.
    if os.path.exists(outputFilename):
        print('This will overwrite the file %s. (C)ontinue or (Q)uit?' % (outputFilename))
        response = input('> ')
        if not response.lower().startswith('c'):
            sys.exit()

    # Read in the message from the input file
    fileObj = open(inputFilename)
    content = fileObj.read()
    fileObj.close()

    print('%sing...' % (myMode.title()))

    # Measure how long the encryption/decryption takes.
    startTime = time.time()
    if myMode == 'encrypt':
        translated = transpositionEncrypt.encryptMessage(myKey, content)
    elif myMode == 'decrypt':
        translated = transpositionDecrypt.decryptMessage(myKey, content)
    totalTime = round(time.time() - startTime, 2)
    print('%sion time: %s seconds' % (myMode.title(), totalTime))

    # Write out the translated message to the output file.
    outputFileObj = open(outputFilename, 'w')
    outputFileObj.write(translated)
    outputFileObj.close()

    print('Done %sing %s (%s characters).' % (myMode, inputFilename, len(content)))
    print('%sed file is %s.' % (myMode.title(), outputFilename))


# If transpositionCipherFile.py is run (instead of imported as a module)
# call the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = transpositionFileHacker
# Transposition File Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import sys, time, os, sys, transpositionDecrypt, detectEnglish

inputFilename = 'frankenstein.encrypted.txt'
outputFilename = 'frankenstein.decrypted.txt'

def main():
    if not os.path.exists(inputFilename):
        print('The file %s does not exist. Quitting.' % (inputFilename))
        sys.exit()

    inputFile = open(inputFilename)
    content = inputFile.read()
    inputFile.close()

    brokenMessage = hackTransposition(content)

    if brokenMessage != None:
        print('Writing decrypted text to %s.' % (outputFilename))

        outputFile = open(outputFilename, 'w')
        outputFile.write(brokenMessage)
        outputFile.close()
    else:
        print('Failed to hack encryption.')


# The hackTransposition() function's code was copy/pasted from
# transpositionHacker.py and had some modifications made.
def hackTransposition(message):
    print('Hacking...')
    # Python programs can be stopped at any time by pressing Ctrl-C (on
    # Windows) or Ctrl-D (on Mac and Linux)
    print('(Press Ctrl-C or Ctrl-D to quit at any time.)')

    for key in range(1, len(message)):
        print('Trying key #%s... ' % (key), end='')
        sys.stdout.flush()

        # We want to track the amount of time it takes to test a single key,
        # so we record the time in startTime.
        startTime = time.time()

        decryptedText = transpositionDecrypt.decryptMessage(key, message)
        englishPercentage = round(detectEnglish.getEnglishCount(decryptedText) * 100, 2)

        totalTime = round(time.time() - startTime, 3)
        print('Test time: %s seconds, ' % (totalTime), end='')
        sys.stdout.flush() # flush printed text to the screen

        print('Percent English: %s%%' % (englishPercentage))
        if englishPercentage > 20:
            print()
            print('Key ' + str(key) + ': ' + decryptedText[:100])
            print()
            print('Enter D for done, or just press Enter to continue:')
            response = input('> ')
            if response.strip().upper().startswith('D'):
                return decryptedText
    return None


# If transpositionFileHacker.py is run (instead of imported as a module)
# call the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = transpositionHacker
# Transposition Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip, detectEnglish, transpositionDecrypt

def main():
    # You might want to copy & paste this text from the source code at
    # http://invpy.com/transpositionHacker.py
    myMessage = """Cb b rssti aieih rooaopbrtnsceee er es no npfgcwu  plri ch nitaalr eiuengiteehb(e1  hilincegeoamn fubehgtarndcstudmd nM eu eacBoltaeteeoinebcdkyremdteghn.aa2r81a condari fmps" tad   l t oisn sit u1rnd stara nvhn fsedbh ee,n  e necrg6  8nmisv l nc muiftegiitm tutmg cm shSs9fcie ebintcaets h  aihda cctrhe ele 1O7 aaoem waoaatdahretnhechaopnooeapece9etfncdbgsoeb uuteitgna.rteoh add e,D7c1Etnpneehtn beete" evecoal lsfmcrl iu1cifgo ai. sl1rchdnheev sh meBd ies e9t)nh,htcnoecplrrh ,ide hmtlme. pheaLem,toeinfgn t e9yce da' eN eMp a ffn Fc1o ge eohg dere.eec s nfap yox hla yon. lnrnsreaBoa t,e eitsw il ulpbdofgBRe bwlmprraio po  droB wtinue r Pieno nc ayieeto'lulcih sfnc  ownaSserbereiaSm-eaiah, nnrttgcC  maciiritvledastinideI  nn rms iehn tsigaBmuoetcetias rn"""

    hackedMessage = hackTransposition(myMessage)

    if hackedMessage == None:
        print('Failed to hack encryption.')
    else:
        print('Copying hacked message to clipboard:')
        print(hackedMessage)
        pyperclip.copy(hackedMessage)


def hackTransposition(message):
    print('Hacking...')

    # Python programs can be stopped at any time by pressing Ctrl-C (on
    # Windows) or Ctrl-D (on Mac and Linux)
    print('(Press Ctrl-C or Ctrl-D to quit at any time.)')

    # brute-force by looping through every possible key
    for key in range(1, len(message)):
        print('Trying key #%s...' % (key))

        decryptedText = transpositionDecrypt.decryptMessage(key, message)

        if detectEnglish.isEnglish(decryptedText):
            # Check with user to see if the decrypted key has been found.
            print()
            print('Possible encryption hack:')
            print('Key %s: %s' % (key, decryptedText[:100]))
            print()
            print('Enter D for done, or just press Enter to continue hacking:')
            response = input('> ')

            if response.strip().upper().startswith('D'):
                return decryptedText

    return None

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = transpositionTest
# Transposition Cipher Test
# http://inventwithpython.com/hacking (BSD Licensed)

import random, sys, transpositionEncrypt, transpositionDecrypt

def main():
    random.seed(42) # set the random "seed" to a static value

    for i in range(20): # run 20 tests
        # Generate random messages to test.

        # The message will have a random length:
        message = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' * random.randint(4, 40)

        # Convert the message string to a list to shuffle it.
        message = list(message)
        random.shuffle(message)
        message = ''.join(message) # convert list to string

        print('Test #%s: "%s..."' % (i+1, message[:50]))

        # Check all possible keys for each message.
        for key in range(1, len(message)):
            encrypted = transpositionEncrypt.encryptMessage(key, message)
            decrypted = transpositionDecrypt.decryptMessage(key, encrypted)

            # If the decryption doesn't match the original message, display
            # an error message and quit.
            if message != decrypted:
                print('Mismatch with key %s and message %s.' % (key, message))
                print(decrypted)
                sys.exit()

    print('Transposition cipher test passed.')


# If transpositionTest.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = vigenereCipher
# Vigenere Cipher (Polyalphabetic Substitution Cipher)
# http://inventwithpython.com/hacking (BSD Licensed)

import pyperclip

LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

def main():
    # This text can be copy/pasted from http://invpy.com/vigenereCipher.py
    myMessage = """Alan Mathison Turing was a British mathematician, logician, cryptanalyst, and computer scientist. He was highly influential in the development of computer science, providing a formalisation of the concepts of "algorithm" and "computation" with the Turing machine. Turing is widely considered to be the father of computer science and artificial intelligence. During World War II, Turing worked for the Government Code and Cypher School (GCCS) at Bletchley Park, Britain's codebreaking centre. For a time he was head of Hut 8, the section responsible for German naval cryptanalysis. He devised a number of techniques for breaking German ciphers, including the method of the bombe, an electromechanical machine that could find settings for the Enigma machine. After the war he worked at the National Physical Laboratory, where he created one of the first designs for a stored-program computer, the ACE. In 1948 Turing joined Max Newman's Computing Laboratory at Manchester University, where he assisted in the development of the Manchester computers and became interested in mathematical biology. He wrote a paper on the chemical basis of morphogenesis, and predicted oscillating chemical reactions such as the Belousov-Zhabotinsky reaction, which were first observed in the 1960s. Turing's homosexuality resulted in a criminal prosecution in 1952, when homosexual acts were still illegal in the United Kingdom. He accepted treatment with female hormones (chemical castration) as an alternative to prison. Turing died in 1954, just over two weeks before his 42nd birthday, from cyanide poisoning. An inquest determined that his death was suicide; his mother and some others believed his death was accidental. On 10 September 2009, following an Internet campaign, British Prime Minister Gordon Brown made an official public apology on behalf of the British government for "the appalling way he was treated." As of May 2012 a private member's bill was before the House of Lords which would grant Turing a statutory pardon if enacted."""
    myKey = 'ASIMOV'
    myMode = 'encrypt' # set to 'encrypt' or 'decrypt'

    if myMode == 'encrypt':
        translated = encryptMessage(myKey, myMessage)
    elif myMode == 'decrypt':
        translated = decryptMessage(myKey, myMessage)

    print('%sed message:' % (myMode.title()))
    print(translated)
    pyperclip.copy(translated)
    print()
    print('The message has been copied to the clipboard.')


def encryptMessage(key, message):
    return translateMessage(key, message, 'encrypt')


def decryptMessage(key, message):
    return translateMessage(key, message, 'decrypt')


def translateMessage(key, message, mode):
    translated = [] # stores the encrypted/decrypted message string

    keyIndex = 0
    key = key.upper()

    for symbol in message: # loop through each character in message
        num = LETTERS.find(symbol.upper())
        if num != -1: # -1 means symbol.upper() was not found in LETTERS
            if mode == 'encrypt':
                num += LETTERS.find(key[keyIndex]) # add if encrypting
            elif mode == 'decrypt':
                num -= LETTERS.find(key[keyIndex]) # subtract if decrypting

            num %= len(LETTERS) # handle the potential wrap-around

            # add the encrypted/decrypted symbol to the end of translated.
            if symbol.isupper():
                translated.append(LETTERS[num])
            elif symbol.islower():
                translated.append(LETTERS[num].lower())

            keyIndex += 1 # move to the next letter in the key
            if keyIndex == len(key):
                keyIndex = 0
        else:
            # The symbol was not in LETTERS, so add it to translated as is.
            translated.append(symbol)

    return ''.join(translated)


# If vigenereCipher.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = vigenereDictionaryHacker
# Vigenere Cipher Dictionary Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import detectEnglish, vigenereCipher, pyperclip

def main():
    ciphertext = """Tzx isnz eccjxkg nfq lol mys bbqq I lxcz."""
    hackedMessage = hackVigenere(ciphertext)

    if hackedMessage != None:
        print('Copying hacked message to clipboard:')
        print(hackedMessage)
        pyperclip.copy(hackedMessage)
    else:
        print('Failed to hack encryption.')


def hackVigenere(ciphertext):
    fo = open('dictionary.txt')
    words = fo.readlines()
    fo.close()

    for word in words:
        word = word.strip() # remove the newline at the end
        decryptedText = vigenereCipher.decryptMessage(word, ciphertext)
        if detectEnglish.isEnglish(decryptedText, wordPercentage=40):
            # Check with user to see if the decrypted key has been found.
            print()
            print('Possible encryption break:')
            print('Key ' + str(word) + ': ' + decryptedText[:100])
            print()
            print('Enter D for done, or just press Enter to continue breaking:')
            response = input('> ')

            if response.upper().startswith('D'):
                return decryptedText

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = vigenereHacker
# Vigenere Cipher Hacker
# http://inventwithpython.com/hacking (BSD Licensed)

import itertools, re
import vigenereCipher, pyperclip, freqAnalysis, detectEnglish

LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
SILENT_MODE = False # if set to True, program doesn't print attempts
NUM_MOST_FREQ_LETTERS = 4 # attempts this many letters per subkey
MAX_KEY_LENGTH = 16 # will not attempt keys longer than this
NONLETTERS_PATTERN = re.compile('[^A-Z]')


def main():
    # Instead of typing this ciphertext out, you can copy & paste it
    # from http://invpy.com/vigenereHacker.py
    ciphertext = """Adiz Avtzqeci Tmzubb wsa m Pmilqev halpqavtakuoi, lgouqdaf, kdmktsvmztsl, izr xoexghzr kkusitaaf. Vz wsa twbhdg ubalmmzhdad qz hce vmhsgohuqbo ox kaakulmd gxiwvos, krgdurdny i rcmmstugvtawz ca tzm ocicwxfg jf "stscmilpy" oid "uwydptsbuci" wabt hce Lcdwig eiovdnw. Bgfdny qe kddwtk qjnkqpsmev ba pz tzm roohwz at xoexghzr kkusicw izr vrlqrwxist uboedtuuznum. Pimifo Icmlv Emf DI, Lcdwig owdyzd xwd hce Ywhsmnemzh Xovm mby Cqxtsm Supacg (GUKE) oo Bdmfqclwg Bomk, Tzuhvif'a ocyetzqofifo ositjm. Rcm a lqys ce oie vzav wr Vpt 8, lpq gzclqab mekxabnittq tjr Ymdavn fihog cjgbhvnstkgds. Zm psqikmp o iuejqf jf lmoviiicqg aoj jdsvkavs Uzreiz qdpzmdg, dnutgrdny bts helpar jf lpq pjmtm, mb zlwkffjmwktoiiuix avczqzs ohsb ocplv nuby swbfwigk naf ohw Mzwbms umqcifm. Mtoej bts raj pq kjrcmp oo tzm Zooigvmz Khqauqvl Dincmalwdm, rhwzq vz cjmmhzd gvq ca tzm rwmsl lqgdgfa rcm a kbafzd-hzaumae kaakulmd, hce SKQ. Wi 1948 Tmzubb jgqzsy Msf Zsrmsv'e Qjmhcfwig Dincmalwdm vt Eizqcekbqf Pnadqfnilg, ivzrw pq onsaafsy if bts yenmxckmwvf ca tzm Yoiczmehzr uwydptwze oid tmoohe avfsmekbqr dn eifvzmsbuqvl tqazjgq. Pq kmolm m dvpwz ab ohw ktshiuix pvsaa at hojxtcbefmewn, afl bfzdakfsy okkuzgalqzu xhwuuqvl jmmqoigve gpcz ie hce Tmxcpsgd-Lvvbgbubnkq zqoxtawz, kciup isme xqdgo otaqfqev qz hce 1960k. Bgfdny'a tchokmjivlabk fzsmtfsy if i ofdmavmz krgaqqptawz wi 1952, wzmz vjmgaqlpad iohn wwzq goidt uzgeyix wi tzm Gbdtwl Wwigvwy. Vz aukqdoev bdsvtemzh rilp rshadm tcmmgvqg (xhwuuqvl uiehmalqab) vs sv mzoejvmhdvw ba dmikwz. Hpravs rdev qz 1954, xpsl whsm tow iszkk jqtjrw pug 42id tqdhcdsg, rfjm ugmbddw xawnofqzu. Vn avcizsl lqhzreqzsy tzif vds vmmhc wsa eidcalq; vds ewfvzr svp gjmw wfvzrk jqzdenmp vds vmmhc wsa mqxivmzhvl. Gv 10 Esktwunsm 2009, fgtxcrifo mb Dnlmdbzt uiydviyv, Nfdtaat Dmiem Ywiikbqf Bojlab Wrgez avdw iz cafakuog pmjxwx ahwxcby gv nscadn at ohw Jdwoikp scqejvysit xwd "hce sxboglavs kvy zm ion tjmmhzd." Sa at Haq 2012 i bfdvsbq azmtmd'g widt ion bwnafz tzm Tcpsw wr Zjrva ivdcz eaigd yzmbo Tmzubb a kbmhptgzk dvrvwz wa efiohzd."""
    hackedMessage = hackVigenere(ciphertext)

    if hackedMessage != None:
        print('Copying hacked message to clipboard:')
        print(hackedMessage)
        pyperclip.copy(hackedMessage)
    else:
        print('Failed to hack encryption.')


def findRepeatSequencesSpacings(message):
    # Goes through the message and finds any 3 to 5 letter sequences
    # that are repeated. Returns a dict with the keys of the sequence and
    # values of a list of spacings (num of letters between the repeats).

    # Use a regular expression to remove non-letters from the message.
    message = NONLETTERS_PATTERN.sub('', message.upper())

    # Compile a list of seqLen-letter sequences found in the message.
    seqSpacings = {} # keys are sequences, values are list of int spacings
    for seqLen in range(3, 6):
        for seqStart in range(len(message) - seqLen):
            # Determine what the sequence is, and store it in seq
            seq = message[seqStart:seqStart + seqLen]

            # Look for this sequence in the rest of the message
            for i in range(seqStart + seqLen, len(message) - seqLen):
                if message[i:i + seqLen] == seq:
                    # Found a repeated sequence.
                    if seq not in seqSpacings:
                        seqSpacings[seq] = [] # initialize blank list

                    # Append the spacing distance between the repeated
                    # sequence and the original sequence.
                    seqSpacings[seq].append(i - seqStart)
    return seqSpacings


def getUsefulFactors(num):
    # Returns a list of useful factors of num. By "useful" we mean factors
    # less than MAX_KEY_LENGTH + 1. For example, getUsefulFactors(144)
    # returns [2, 72, 3, 48, 4, 36, 6, 24, 8, 18, 9, 16, 12]

    if num < 2:
        return [] # numbers less than 2 have no useful factors

    factors = [] # the list of factors found

    # When finding factors, you only need to check the integers up to
    # MAX_KEY_LENGTH.
    for i in range(2, MAX_KEY_LENGTH + 1): # don't test 1
        if num % i == 0:
            factors.append(i)
            factors.append(int(num / i))
    if 1 in factors:
        factors.remove(1)
    return list(set(factors))


def getItemAtIndexOne(x):
    return x[1]


def getMostCommonFactors(seqFactors):
    # First, get a count of how many times a factor occurs in seqFactors.
    factorCounts = {} # key is a factor, value is how often if occurs

    # seqFactors keys are sequences, values are lists of factors of the
    # spacings. seqFactors has a value like: {'GFD': [2, 3, 4, 6, 9, 12,
    # 18, 23, 36, 46, 69, 92, 138, 207], 'ALW': [2, 3, 4, 6, ...], ...}
    for seq in seqFactors:
        factorList = seqFactors[seq]
        for factor in factorList:
            if factor not in factorCounts:
                factorCounts[factor] = 0
            factorCounts[factor] += 1

    # Second, put the factor and its count into a tuple, and make a list
    # of these tuples so we can sort them.
    factorsByCount = []
    for factor in factorCounts:
        # exclude factors larger than MAX_KEY_LENGTH
        if factor <= MAX_KEY_LENGTH:
            # factorsByCount is a list of tuples: (factor, factorCount)
            # factorsByCount has a value like: [(3, 497), (2, 487), ...]
            factorsByCount.append( (factor, factorCounts[factor]) )

    # Sort the list by the factor count.
    factorsByCount.sort(key=getItemAtIndexOne, reverse=True)

    return factorsByCount


def kasiskiExamination(ciphertext):
    # Find out the sequences of 3 to 5 letters that occur multiple times
    # in the ciphertext. repeatedSeqSpacings has a value like:
    # {'EXG': [192], 'NAF': [339, 972, 633], ... }
    repeatedSeqSpacings = findRepeatSequencesSpacings(ciphertext)

    # See getMostCommonFactors() for a description of seqFactors.
    seqFactors = {}
    for seq in repeatedSeqSpacings:
        seqFactors[seq] = []
        for spacing in repeatedSeqSpacings[seq]:
            seqFactors[seq].extend(getUsefulFactors(spacing))

    # See getMostCommonFactors() for a description of factorsByCount.
    factorsByCount = getMostCommonFactors(seqFactors)

    # Now we extract the factor counts from factorsByCount and
    # put them in allLikelyKeyLengths so that they are easier to
    # use later.
    allLikelyKeyLengths = []
    for twoIntTuple in factorsByCount:
        allLikelyKeyLengths.append(twoIntTuple[0])

    return allLikelyKeyLengths


def getNthSubkeysLetters(n, keyLength, message):
    # Returns every Nth letter for each keyLength set of letters in text.
    # E.g. getNthSubkeysLetters(1, 3, 'ABCABCABC') returns 'AAA'
    #      getNthSubkeysLetters(2, 3, 'ABCABCABC') returns 'BBB'
    #      getNthSubkeysLetters(3, 3, 'ABCABCABC') returns 'CCC'
    #      getNthSubkeysLetters(1, 5, 'ABCDEFGHI') returns 'AF'

    # Use a regular expression to remove non-letters from the message.
    message = NONLETTERS_PATTERN.sub('', message)

    i = n - 1
    letters = []
    while i < len(message):
        letters.append(message[i])
        i += keyLength
    return ''.join(letters)


def attemptHackWithKeyLength(ciphertext, mostLikelyKeyLength):
    # Determine the most likely letters for each letter in the key.
    ciphertextUp = ciphertext.upper()
    # allFreqScores is a list of mostLikelyKeyLength number of lists.
    # These inner lists are the freqScores lists.
    allFreqScores = []
    for nth in range(1, mostLikelyKeyLength + 1):
        nthLetters = getNthSubkeysLetters(nth, mostLikelyKeyLength, ciphertextUp)

        # freqScores is a list of tuples like:
        # [(<letter>, <Eng. Freq. match score>), ... ]
        # List is sorted by match score. Higher score means better match.
        # See the englishFreqMatchScore() comments in freqAnalysis.py.
        freqScores = []
        for possibleKey in LETTERS:
            decryptedText = vigenereCipher.decryptMessage(possibleKey, nthLetters)
            keyAndFreqMatchTuple = (possibleKey, freqAnalysis.englishFreqMatchScore(decryptedText))
            freqScores.append(keyAndFreqMatchTuple)
        # Sort by match score
        freqScores.sort(key=getItemAtIndexOne, reverse=True)

        allFreqScores.append(freqScores[:NUM_MOST_FREQ_LETTERS])

    if not SILENT_MODE:
        for i in range(len(allFreqScores)):
            # use i + 1 so the first letter is not called the "0th" letter
            print('Possible letters for letter %s of the key: ' % (i + 1), end='')
            for freqScore in allFreqScores[i]:
                print('%s ' % freqScore[0], end='')
            print() # print a newline

    # Try every combination of the most likely letters for each position
    # in the key.
    for indexes in itertools.product(range(NUM_MOST_FREQ_LETTERS), repeat=mostLikelyKeyLength):
        # Create a possible key from the letters in allFreqScores
        possibleKey = ''
        for i in range(mostLikelyKeyLength):
            possibleKey += allFreqScores[i][indexes[i]][0]

        if not SILENT_MODE:
            print('Attempting with key: %s' % (possibleKey))

        decryptedText = vigenereCipher.decryptMessage(possibleKey, ciphertextUp)

        if detectEnglish.isEnglish(decryptedText):
            # Set the hacked ciphertext to the original casing.
            origCase = []
            for i in range(len(ciphertext)):
                if ciphertext[i].isupper():
                    origCase.append(decryptedText[i].upper())
                else:
                    origCase.append(decryptedText[i].lower())
            decryptedText = ''.join(origCase)

            # Check with user to see if the key has been found.
            print('Possible encryption hack with key %s:' % (possibleKey))
            print(decryptedText[:200]) # only show first 200 characters
            print()
            print('Enter D for done, or just press Enter to continue hacking:')
            response = input('> ')

            if response.strip().upper().startswith('D'):
                return decryptedText

    # No English-looking decryption found, so return None.
    return None


def hackVigenere(ciphertext):
    # First, we need to do Kasiski Examination to figure out what the
    # length of the ciphertext's encryption key is.
    allLikelyKeyLengths = kasiskiExamination(ciphertext)
    if not SILENT_MODE:
        keyLengthStr = ''
        for keyLength in allLikelyKeyLengths:
            keyLengthStr += '%s ' % (keyLength)
        print('Kasiski Examination results say the most likely key lengths are: ' + keyLengthStr + '\n')

    for keyLength in allLikelyKeyLengths:
        if not SILENT_MODE:
            print('Attempting hack with key length %s (%s possible keys)...' % (keyLength, NUM_MOST_FREQ_LETTERS ** keyLength))
        hackedMessage = attemptHackWithKeyLength(ciphertext, keyLength)
        if hackedMessage != None:
            break

    # If none of the key lengths we found using Kasiski Examination
    # worked, start brute-forcing through key lengths.
    if hackedMessage == None:
        if not SILENT_MODE:
            print('Unable to hack message with likely key length(s). Brute forcing key length...')
        for keyLength in range(1, MAX_KEY_LENGTH + 1):
            # don't re-check key lengths already tried from Kasiski
            if keyLength not in allLikelyKeyLengths:
                if not SILENT_MODE:
                    print('Attempting hack with key length %s (%s possible keys)...' % (keyLength, NUM_MOST_FREQ_LETTERS ** keyLength))
                hackedMessage = attemptHackWithKeyLength(ciphertext, keyLength)
                if hackedMessage != None:
                    break
    return hackedMessage


# If vigenereHacker.py is run (instead of imported as a module) call
# the main() function.
if __name__ == '__main__':
    main()
########NEW FILE########
