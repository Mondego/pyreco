__FILENAME__ = bar
#!/usr/bin/env python

import fileinput

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2012-12-09"

class GroupObjects:
    __debug = False

    def __checkIfPossible(self, inNumber, inGroupPos):
        """
        Returns true if the given number on the given group can be positioned on
        the self.__position position.
        This method compares the number against all the groups O(n - 1) where n is
        the number of groups

        @param inNumber int The number to be compared
        @param inGroupPos int The position of the group who contains the number
        """

        maxPos = 0
        minPos = 0

        for groupPos in xrange(0, len(self.__groups)):
            if inGroupPos <> groupPos:
                if self.__debug:
                    print "Group: %s Number: %s Comparing Group: %s Comp Num: %s" % (
                        inGroupPos,
                        inNumber,
                        groupPos,
                        self.__groups[groupPos][0])

                # Check if the compared group contain a number smaller than the current
                # number, then we can use it to increase the possible position
                if self.__groups[groupPos][0] <= inNumber:
                    minPos += 1
                    if self.__debug:
                        print "Inc Pos"

                # Check if the bigger number of the current group is smaller than the
                # current one, then the player will play always a number who will move
                # the current number one position
                if self.__groups[groupPos][len(self.__groups[groupPos]) - 1] < inNumber:
                    maxPos += 1

        # Check if the number can be included into the numbers on the whised position
        if minPos >= (self.__position - 1) and maxPos <= (self.__position - 1):
            if self.__debug:
                print "Found: %s" % (inNumber)
            return True

        return False

    def resolve(self):
        """
        @return int the number of all the numbers that can fit on the given position
        """
        possibleSolutions = set()

        # Check all the numbers against all the groups in order to determinate all the
        # possible positions for the number number, each number will be compared against
        # the biggest and smallest numbers of each group, then O(n * m) where n is the
        # number of numbers, and m the number of groups
        for groupPos in xrange(0, len(self.__groups)):
            for number in self.__groups[groupPos]:
                if number not in possibleSolutions:
                    if self.__checkIfPossible(number, groupPos):
                        possibleSolutions.add(number)
                        if self.__debug:
                            print "Comparing: %s" % (number)
                    

        if self.__debug:
            print "Solutions: %s" % (sorted(possibleSolutions))

        return len(possibleSolutions)

    def __init__(self, inPosition, inPositions):
        # Get all the groups, ans sort the numbers for each group, removing the first one,
        # that is the number of numbers
        self.__groups = [sorted(map(int, numbers.split()[1:])) for numbers in inPositions]
        self.__position = inPosition

        if self.__debug:
            print "Position: %s Groups: %s" % (self.__position, self.__groups) 

if __name__ == "__main__":
    lines = [line.replace('\n', '') for line in fileinput.input()]

    currentLine = 1
    for problem in xrange(0, int(lines[0])):
        problemInfo = map(int, lines[currentLine].split())
        print GroupObjects(
            problemInfo[1],
            lines[currentLine + 1:currentLine + 1 + problemInfo[0]]).resolve()

        currentLine += problemInfo[0] + 1

########NEW FILE########
__FILENAME__ = game
#!/usr/bin/env python

import fileinput

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2013-03-22"

class Game:
    __debug = False
    __number = None

    def __removeMaxPossible(self, inNumber):
        """
        This method removes the maximun number satisfying the n-2^k constraint

        @return int The number after remove the max number as an integer
        @return bool False if is not possible to remove any number
        """
        # Get the number in binary and remove the "0b" prefix
        binNumber = bin(inNumber)[2:]
        # The first zero will determinate the first max number than can be removed keeping the same number of '1'
        # and complaining with the n-2^k constraint
        firstZeroPos = binNumber.find('0')

        # If we don't have zeros, we can remove anithing keeping the same number of '1' :'(
        if firstZeroPos == -1:
            return False

        if self.__debug:
            print "N: %d" % (inNumber)
            print "To Remove: 1%s" % ('0' * (len(binNumber) - firstZeroPos - 1))
            print inNumber - int("1%s" % ('0' * (len(binNumber) - firstZeroPos - 1)), 2)
            print bin(inNumber - int("1%s" % ('0' * (len(binNumber) - firstZeroPos - 1)), 2))[2:]

        return inNumber - int("1%s" % ('0' * (len(binNumber) - firstZeroPos - 1)), 2)

    def resolve(self):
        """
        @return str The player who will win the game
        """
        firstWin = False
        # Substract numbers until have a number that can't be reduced (withouth any zero on it)
        n = self.__removeMaxPossible(self.__number)
        while n != False:
            firstWin = not firstWin
            n = self.__removeMaxPossible(n)

        if firstWin:
            return "First Player"

        return "Second Player"

    def __init__(self, inNumber):
        self.__number = inNumber

        if self.__debug:
            print "Number: %s" % (bin(inNumber)[2:])

if __name__ == "__main__":
    lines = map(int, [line.replace('\n', '') for line in fileinput.input()])

    for number in lines[1:]:
        print Game(number).resolve()

########NEW FILE########
__FILENAME__ = master_mind
#!/usr/bin/env python

import fileinput, itertools

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2012-12-30"

class MasterMind:
    __debug = False

    def __checkIfPossibleByPairs(self):
        """ If the score is bigger than the half of the guess len in two of the guesses, they
        should to share at least the score - (guess lengh / 2) elements """
        prevGuess = self.__guesses[0]
        for guess in reversed(self.__guesses):
            if guess[len(guess) - 1] < (self.__guessLen / 2):
                return True

            sharedElems = 0
            for pos in xrange(0, self.__guessLen):
                if guess[pos] == prevGuess[pos]:
                    sharedElems += 1

            if self.__debug:
                print "Shared: %s - Len: %s - Score: %s" % (sharedElems, (self.__guessLen / 2), guess[len(guess) - 1])

            if sharedElems < (guess[len(guess) - 1] - (self.__guessLen / 2)):
                return False

        return True

    def __createPossibleKeys(self, inGuesses):
        possibles = {}
        notPossibles = {}
        keyMembers = {}

        for pos in xrange(0, self.__guessLen):
            possibles[pos] = set()
            notPossibles[pos] = set()

        for guess in inGuesses:
            if self.__debug:
                print "Guess: %s" % (guess)
            remainScore = guess[len(guess) - 1]

            totalNotPos = 0
            for pos in xrange(0, self.__guessLen):
                if guess[pos] in notPossibles[pos]:
                    totalNotPos += 1

            # If the total lenght of the guess minus the not possible number are
            # equal to the score, all the remain numbers are parts of the key
            if (self.__guessLen - totalNotPos) == remainScore:
                for pos in xrange(0, self.__guessLen):
                    if guess[pos] not in notPossibles[pos]:
                        keyMembers[pos] = guess[pos]
            else:
                # All the numbers that we can asset in the key, will decrease the score,
                # and all the number that are not in the key will increase the score, but will
                # nos be considerer in a future
                for pos, value in keyMembers.items():
                    if guess[pos] == value:
                        remainScore -= 1
                    else:
                        remainScore += 1

                if remainScore == 0:
                    for pos in xrange(0, self.__guessLen):
                        notPossibles[pos].add(guess[pos])
                        possibles[pos].discard(guess[pos])
                        if self.__debug:
                            print "Discarted: %s" % (guess[pos])
                else:
                    for pos in xrange(0, self.__guessLen):
                        if (self.__guessLen - pos) == remainScore:
                            if pos not in keyMembers:
                                keyMembers[pos] = guess[pos]
                            remainScore -= 1
                        else:
                            if guess[pos] not in notPossibles[pos]:
                                remainScore -= 1
                                possibles[pos].add(guess[pos])

            if self.__debug:
                print "Key members: %s" % (keyMembers)
                print "Not Possibles: %s" % (notPossibles)
                print "Possibles: %s" % (possibles)

        mainKeys = []
        if len(possibles) > 0:
            for pos in xrange(0, self.__guessLen):
                if pos in keyMembers:
                    mainKeys.append([keyMembers[pos]])
                else:
                    if len(possibles[pos]) == 0:
                        keys = []
                        for count in xrange(1, self.__inHiggerInt + 1):
                            if count not in notPossibles[pos]:
                                keys.append(count)
                        mainKeys.append(keys)
                    else:
                        mainKeys.append(list(possibles[pos]))

        if self.__debug:
            print "Main keys: %s" % (mainKeys)

        possibleKeyValues = []
        for pos in xrange(0, self.__guessLen):
            if pos in keyMembers:
                possibleKeyValues.append([keyMembers[pos]])
            else:
                keys = []
                for count in xrange(1, self.__inHiggerInt + 1):
                    if count not in notPossibles[pos]:
                        keys.append(count)

                possibleKeyValues.append(keys)
                        

        if self.__debug:
            print "Possible keys: %s" % (possibleKeyValues)

        return mainKeys, possibleKeyValues

    def __checkIfPossibleWithGuesses(self, inKey):
        if self.__debug:
            print "Checking:"
            print inKey

        for guess in self.__guesses:
            score = 0
            for pos in xrange(0, self.__guessLen):
                if inKey[pos] == guess[pos]:
                    score += 1

            if score < guess[len(guess) - 1]:
                return False

        return True

    def resolve(self):
        # Create a set with all the possible keys using the guess with the lowest score...
        self.__guesses = sorted(self.__guesses, key = lambda guess: guess[len(guess) - 1])

        # First of all check if is possible comparing the matches between the keys, is
        # the fastest method that can define if is not possible
        if not self.__checkIfPossibleByPairs():
            return "No"

        # Get the posible keys, mainKeys will be the keys with most posibilities to match
        # because of they include all the numbersincluded into the different guesses, and
        # possibleKeys the rest of posible keys with the numbers that can't be discarted
        mainKeys, possibleKeys = self.__createPossibleKeys(self.__guesses)

        # Check the keys with most posibilities
        for key in itertools.product(*mainKeys):
            if self.__checkIfPossibleWithGuesses(key):
                return "Yes"

        # Check the rest, this is the brute force  method :'(
        for key in itertools.product(*possibleKeys):
            if self.__checkIfPossibleWithGuesses(key):
                return "Yes"

        # No key matches, no hope left :'(
        return "No"

    def __init__(self, inHiggerInt, inGuessLen, inGuesses):
        if self.__debug:
            print "HiggerGuess: %s GuessLen: %s " % (inHiggerInt, inGuessLen)

        self.__inHiggerInt = inHiggerInt
        self.__guesses = inGuesses
        self.__guessLen = inGuessLen

if __name__ == "__main__":
    lines = [line.replace('\n', '') for line in fileinput.input()]

    currentLine = 1

    for problemLine in xrange(0, int(lines[0])):
        problemInfo = map(int, lines[currentLine].split())
        guesses = []
        for guess in xrange(0, problemInfo[2]):
            currentLine += 1
            guesses.append(map(int, lines[currentLine].split()))

        print MasterMind(problemInfo[0], problemInfo[1], guesses).resolve()
        currentLine += 1

########NEW FILE########
__FILENAME__ = reverse_polish
#!/usr/bin/env python

""" I didn't test this solution against the Facebook validator, I was interrupted when I was doing it :'( """

import fileinput, math

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2012-12-09"

class ReversePolishNotation:
    __debug = False

    def __calcMaxNumOfOps(self):
        replace = 0
        stackLength = 0
        for count in xrange(0, len(self.__input)):
            if self.__input[count] == 'x':
                stackLength += 1
            else:
                # We have an operator, and nothing to work with
                # We can, remove the operator or replace it in order to
                # avoid problems with future operators, we replace it,
                # this is only to get an aproximation of the max num of ops
                if stackLength <= 1:
                    stackLength += 1
                    replace += 1
                else:
                    stackLength -= 1

        self.__maxNumOfOps = int(replace + math.floor((stackLength - 1) / 2) + ((stackLength - 1) % 2))

    def __isValid(self, operation):
        stackLength = 0
        for count in xrange(0, len(operation)):
            if operation[count] != '-':
                if operation[count] == 'x':
                    stackLength += 1
                else:
                    if stackLength < 1:
                        return False
                    else:
                        stackLength -= 1

        return stackLength == 1

    def __resolveByDeep(self, operation, currentPos = 0, currentOps = 0):
        # Check if the current operation is valid, in this case, we can set
        # the max numbre of ops to the current number of ops
        if self.__isValid(operation):
            if self.__debug:
                print "Valid: %s - %s" % (currentOps, operation)
            self.__maxNumOfOps = currentOps

        # Check if this is not a valid way, or the number os current ops are
        # bigger than another best option
        if currentOps >= self.__maxNumOfOps or currentPos >= len(operation):
            if self.__debug:
                print operation
                print "returning -1 Operation: %s Max Operations: %s ..." % (currentOps, self.__maxNumOfOps)
            return -1

        self.__resolveByDeep(operation, currentPos + 1, currentOps)

        # Try adding an x
        newOperation = operation[:]
        newOperation.insert(currentPos, 'x')
        self.__resolveByDeep(newOperation, currentPos + 2, currentOps + 1)

        # Try adding an *
        newOperation = operation[:]
        newOperation.insert(currentPos, '*')
        self.__resolveByDeep(newOperation, currentPos + 2, currentOps + 1)

        # Try Removing the char (replace by -)
        newOperation = operation[:]
        newOperation[currentPos] = '-'
        self.__resolveByDeep(newOperation, currentPos + 1, currentOps + 1)

        # Try replacing the character by the opposite
        newOperation = operation[:]
        if newOperation[currentPos] == '*':
            newOperation[currentPos] = 'x'
        else:
            newOperation[currentPos] = '*'
        self.__resolveByDeep(newOperation, currentPos + 1, currentOps + 1)

    def resolve(self):
        self.__calcMaxNumOfOps()
        self.__resolveByDeep(self.__input)
        return self.__maxNumOfOps

    def __init__(self, inProblem):
        self.__input = list(inProblem)
        self.__maxNumOfOps = None

if __name__ == "__main__":
    lines = [line.replace('\n', '') for line in fileinput.input()]

    for problem in xrange(1, int(lines[0]) + 1):
        print ReversePolishNotation(lines[problem]).resolve()

########NEW FILE########
__FILENAME__ = secret_decoder
#!/usr/bin/env python

import fileinput

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2013-01-13"

class SecretDecoder:
    __debug = False

    def __checkIfPossibleLine(self, inOriginal, inLine):
        """
        This method returns true if the inLine is a possible combination compared with
        the inOringinal line words by words and char by char or false if is not a possible combination

        @return bool True if is possible, False if not
        """
        if self.__debug:
            print "Check if possible: %s" % (inLine)

        charDict = {}
        intDict = {}
        # Check char by char all the words
        for wordPos in xrange(0, len(inLine)):
            for charPos in xrange(0, len(inLine[wordPos])):
                # Use a dictionary in order to know if the character was previously setted, and
                # if it was, check if the replacement matches
                if charDict.get(inLine[wordPos][charPos], '') == '':
                    charDict[inLine[wordPos][charPos]] = inOriginal[wordPos][charPos]
                else:
                    if charDict[inLine[wordPos][charPos]] != inOriginal[wordPos][charPos]:
                        if self.__debug:
                            print "No possible"

                        return False

                # Use a dictionary in order to know if the character was previously setted, and
                # if it was, check if the replacement matches
                if intDict.get(inOriginal[wordPos][charPos], '') == '':
                    intDict[inOriginal[wordPos][charPos]] = inLine[wordPos][charPos]
                else:
                    if intDict[inOriginal[wordPos][charPos]] != inLine[wordPos][charPos]:
                        if self.__debug:
                            print "No possible"

                        return False

        if self.__debug:
            print "Possible"

        return True

    def __checkByDepp(self, inOriginalLine, inLine = [], inCurrentWord = 0):
        """
        Recursive search, check all the posible combinations for the given line as a string with
        the necessary format to be printed
        """
        if self.__debug:
            print "Checking: %s - %s" % (inOriginalLine, inLine)

        if self.__checkIfPossibleLine(inOriginalLine, inLine):
            # If the line is possible, and the number of words are the same, we have a
            # line, return it, this will stop the recursivity :)
            if len(inOriginalLine) == len(inLine):
                return "%s = %s" % (' '.join(inOriginalLine), ' '.join(inLine))

            # Check all the words with the same lenght that the number of encrypted characters have
            for word in self.__wordsByLen[len(inOriginalLine[inCurrentWord])]:
                newLine = inLine[:]
                newLine.append(word)
                solution = self.__checkByDepp(inOriginalLine, newLine, inCurrentWord + 1)
                if solution <> False:
                    return solution

        return False

    def resolve(self):
        """
        This method launches the recursive serach of the correct combination and returns as string the text
        decoded if possible, with the necessary format given by the specifications

        @return str The text decoded and formatted
        """
        decrypted = []
        for line in self.__linesEncoded:
            decrypted.append(self.__checkByDepp(line))

        return '\n'.join(decrypted)

    def __init__(self, inInputLines):
        # Will contain the original lines encoded as lists of words
        self.__linesEncoded = []
        # This dictionary will be used to store all the possible words sorted by length in order to
        # do as fast as possible the replacement
        self.__wordsByLen = {}

        readingSecrets = False

        # Parse the input lines and prepare the dictionary of words by length, the lists with the encoded
        # lines, and the list with the possible words to be used
        for line in inInputLines[1:]:
            if line == '//secret':
                readingSecrets = True
            else:
                if readingSecrets:
                    self.__linesEncoded.append(line.split())
                else:
                    if self.__wordsByLen.get(len(line), False) == False:
                        self.__wordsByLen[len(line)] = [line]
                    else:
                        self.__wordsByLen[len(line)].append(line)

        if self.__debug:
            print "Encoded: %s" % (self.__linesEncoded)
            print "Words by len: %s" % (self.__wordsByLen)

if __name__ == "__main__":
    lines = [line.replace('\n', '') for line in fileinput.input()]

    print SecretDecoder(lines).resolve()

########NEW FILE########
__FILENAME__ = staves
#!/usr/bin/env python

import itertools

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2013-03-21"

class Staves:
    __debug = False

    def __checkWighted(self, inStr1, inStr2):
        stavesInt = map(int, list(inStr1 + inStr2))

        regularSum = sum(stavesInt)

        weigthedSum = 0
        for pos in xrange(0, len(stavesInt)):
            weigthedSum += stavesInt[pos] * (pos + 1)

        return (float(weigthedSum) / regularSum) == (float(len(stavesInt) + 1) / 2)

    def __checkPossible(self, inStr1, inStr2):
        return len(self.__string.replace(inStr1, '').replace(inStr2, '')) == (len(self.__string) - len(inStr1) - len(inStr2))

    def resolve(self):
        stavesByLen = {}

        for count in xrange(0, len(self.__string)):
            for subStrLen in xrange(0, len(self.__string) - count):
                stave = self.__string[count:count + subStrLen + 1]
                if len(stave) in stavesByLen:
                    stavesByLen[len(stave)].append(stave)
                else:
                    stavesByLen[len(stave)] = [stave]

        if self.__debug:
            print stavesByLen

        for length in sorted(stavesByLen.keys(), reverse = True):
            for combination in itertools.combinations(stavesByLen[length], 2):
                if self.__checkPossible(combination[0], combination[1]):
                    if (
                        (self.__checkWighted(combination[0], combination[1])) or
                        (self.__checkWighted(combination[0][::-1], combination[1])) or
                        (self.__checkWighted(combination[0], combination[1][::-1])) or
                        (self.__checkWighted(combination[0][::-1], combination[1][::-1]))):

                        return "%d %d %d" % (
                            self.__string.find(combination[0]),
                            self.__string.find(combination[1]),
                            len(combination[0]))

        return False

    def __init__(self, inStr):
        self.__string = inStr

print Staves(raw_input()).resolve()

########NEW FILE########
__FILENAME__ = unique_substrings
#!/usr/bin/env python

__author__ = "Alonso Vidales"
__email__ = "alonso.vidales@tras2.es"
__date__ = "2013-03-21"

class UniqueSubstrings:
    def resolve(self):
        # Will contain all the possible substrings
        substrings = set()

        # Get all the possible substrings from the main string
        for count in xrange(0, len(self.string)):
            for subStrLen in xrange(0, len(self.string) - count):
                substrings.add(self.string[count:count + subStrLen + 1])

        return len(substrings)

    def __init__(self, inStr):
        self.string = inStr

print UniqueSubstrings(raw_input()).resolve()

########NEW FILE########
