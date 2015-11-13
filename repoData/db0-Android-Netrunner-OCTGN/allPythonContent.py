__FILENAME__ = actions
    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the basic table actions in ANR. They are the ones the player calls when they use an action in the menu.
# Many of them are also called from the autoscripts.
###=================================================================================================================###

import re
import collections
import time


#---------------------------------------------------------------------------
# Global variables
#---------------------------------------------------------------------------
identName = None # The name of our current identity
Identity = None
origController = {} # A dictionary which holds the original controller of cards who have temporary switched control to allow the opponent to manipulate them (usually during access)
ModifyDraw = 0 #if True the audraw should warn the player to look at r&D instead

gatheredCardList = False # A variable used in reduceCost to avoid scanning the table too many times.
costIncreasers = [] # used in reduceCost to store the cards that might hold potential cost-increasing effects. We store them globally so that we only scan the table once per execution
costReducers = [] # Same as above

installedCount = {} # A dictionary which keeps track how many of each card type have been installed by the player.

autoRezFlags = [] # A dictionary which holds cards that the corp has set to Auto Rez at the start of their turn.
currClicks = 0

PriorityInform = True # Explains what the "prioritize card" action does.
newturn = True #We use this variable to track whether a player has yet to do anything this turn.
endofturn = False #We use this variable to know if the player is in the end-of-turn phase.
lastKnownNrClicks = 0 # A Variable keeping track of what the engine thinks our action counter should be, in case we change it manually.

#---------------------------------------------------------------------------
# Clicks indication
#---------------------------------------------------------------------------

def useClick(group = table, x=0, y=0, count = 1, manual = False):
   debugNotify(">>> useClick(){}".format(extraASDebug())) #Debug
   global currClicks, lastKnownNrClicks
   mute()
   extraText = ''
   if count == 0: return '{} takes a free action'.format(me)
   if ds == 'runner' and re.search(r'running',getGlobalVariable('status')):
      if getGlobalVariable('SuccessfulRun') == 'True': jackOut() # If the runner has done a successful run but forgot to end it, then simply jack them out automatically.
      elif not confirm("You have not yet finished your previous run. Normally you're not allowed to use clicks during runs, are you sure you want to continue?\
                    \n\n(Pressing 'No' will abort this action and you can then Jack-out or finish the run succesfully with [ESC] or [F3] respectively"): return 'ABORT'
   clicksReduce = findCounterPrevention(me.Clicks, 'Clicks', me)
   if clicksReduce: notify(":::WARNING::: {} had to forfeit their next {} clicks".format(me, clicksReduce))
   me.Clicks -= clicksReduce
   if me.Clicks < count:
      if not confirm("You do not have enough clicks left to take this action. Are you sure you want to continue?\n\n(Did you remember to start your turn with [F1]?)"): return 'ABORT'
      else: extraText = ' (Exceeding Max!)'
   currClicks += count + lastKnownNrClicks - me.Clicks# If the player modified their click counter manually, the last two will increase/decreate our current click accordingly.
   me.Clicks -= count
   lastKnownNrClicks = me.Clicks
   #if not manual: clearLeftoverEvents() # We don't clear all event when manually dragging events to the table, or it will clear the one we just played as well. 
   # Removed above for speed. Now done only in turn end.
   debugNotify("<<< useClick", 3) #Debug
   if count == 2: return "{} {} {} uses Double Click #{} and #{}{}".format(uniClick(),uniClick(),me,currClicks - 1, currClicks,extraText)
   elif count == 3: return "{} {} {} {} uses Triple Click #{}, #{} and #{}{}".format(uniClick(),uniClick(),uniClick(),me,currClicks - 2, currClicks - 1, currClicks,extraText)
   else: return "{} {} uses Click #{}{}".format(uniClick(),me,currClicks,extraText)

def modClicks(group = table,x=0,y=0,targetPL = me, count = 1, action = 'interactive'):
   debugNotify(">>> modClicks() for {} with count {}".format(targetPL,count)) #Debug
   mute()
   loopWait = 0
   while getGlobalVariable('Max Clicks') == 'CHECKED OUT':
      rnd(1,10)
      if loopWait >= 3 and not count % 3: notify("=> {} is still checking Max Clicks...".format(me))
      loopWait += 1
      if loopWait == 15: 
         notify(":::ERROR::: cannot check out the max clicks variable. Try again later")
         return 'ABORT'
   maxClicksDict = eval(getGlobalVariable('Max Clicks'))
   debugNotify("maxClicksDict = {}".format(maxClicksDict))
   setGlobalVariable('Max Clicks','CHECKED OUT')
   if action == 'interactive': # If we're silent and at count 0, we're just looking to grab how many maxclicks we have at the end.
      count = askInteger("What is your new current maximum Clicks per turn?", maxClicksDict[targetPL._id])
      if count == None: return
      maxClicksDict[targetPL._id] = count
      notify("{} has set their Max Clicks to {} per turn".format(me,count))
   elif action == 'increment': maxClicksDict[targetPL._id] += count 
   elif action == 'set to': maxClicksDict[targetPL._id] = count
   if maxClicksDict.get(targetPL._id,'NULL') == 'NULL': # If the value has not been set, we reset it to avoid a crash.
      notify(":::WARNING::: {}'s Max Clicks were not set. Setting at the default value".format(targetPL))
      if targetPL.getGlobalVariable('ds') == 'corp': maxClicksDict[targetPL._id] = 3
      else: maxClicksDict[targetPL._id] = 4
   setGlobalVariable('Max Clicks',str(maxClicksDict)) 
   debugNotify("<<< modClicks() with return {}".format(maxClicksDict[targetPL._id])) #Debug
   return maxClicksDict[targetPL._id]

#---------------------------------------------------------------------------
# Start/End of turn
#---------------------------------------------------------------------------
def goToEndTurn(group, x = 0, y = 0):
   debugNotify(">>> goToEndTurn(){}".format(extraASDebug())) #Debug
   mute()
   global endofturn, currClicks, newturn
   if ds == None:
      whisper ("Please perform the game setup first (Ctrl+Shift+S)")
      return
   if re.search(r'running',getGlobalVariable('status')): jackOut() # If the player forgot to end the run, we do it for them now.
   if me.Clicks > 0: # If the player has not used all their clicks for this turn, remind them, just in case.
      if debugVerbosity <= 0 and not confirm("You have not taken all your clicks for this turn, are you sure you want to declare end of turn"): return
   if currentHandSize(me) < 0: 
      notify(":::Warning:::{} goes to sleep, never to wake up again (flatlined due to excessive brain damage.)".format(me)) #If the target does not have any more cards in their hand, inform they've flatlined.
      reportGame('Flatlined')
      return
   atTimedEffects('PreEnd')
   if len(me.hand) > currentHandSize(): #If the player is holding more cards than their hand max. remind them that they need to discard some
                                        # and put them in the end of turn to allow them to do so.
      if endofturn: #If the player has gone through the end of turn phase and still has more hands, allow them to continue but let everyone know.
         if debugVerbosity <= 0 and not confirm("You still hold more cards than your hand size maximum. Are you sure you want to proceed?"): return
         else: notify(":::Warning::: {} has ended their turn holding more cards ({}) than their hand size maximum of {}".format(me,len(me.hand),currentHandSize()))
      else: # If the player just ended their turn, give them a chance to discard down to their hand maximum.
         if ds == "corp": notify ("The Corporation of {} is performing an Internal Audit before CoB.".format(me))
         else: notify ("Runner {} is rebooting all systems for the day.".format(me))
         if debugVerbosity <= 0: information(':::Warning:::\n\n You have more card in your hand than your current hand size maximum of {}. Please discard enough and then use the "Declare End of Turn" action again.'.format(currentHandSize()))
         endofturn = True
         return
   playTurnEndSound()
   endofturn = False
   newturn = False
   currClicks = 0
   myCards = [card for card in table if card.controller == me and card.owner == me]
   for card in myCards: # We refresh once-per-turn cards to be used on the opponent's turn as well (e.g. Net Shield)
      if card._id in Stored_Type and fetchProperty(card, 'Type') != 'ICE': card.orientation &= ~Rot90
   clearRestrictionMarkers()
   atTimedEffects('End')
   clearAll() # Just in case the player has forgotten to remove their temp markers.
   announceEoT()
   opponent = ofwhom('onOpponent')
   opponent.setActivePlayer() # new in OCTGN 3.0.5.47

def goToSot (group, x=0,y=0):
   debugNotify(">>> goToSot(){}".format(extraASDebug())) #Debug
   global newturn, endofturn, lastKnownNrClicks, currClicks, turn
   mute()
   if endofturn or currClicks or newturn or me.Clicks != 0:
      if debugVerbosity <= 0 and not confirm("You have not yet properly ended you previous turn. You need to use F12 after you've finished all your clicks.\n\nAre you sure you want to continue?"): return
      else:
         if len(me.hand) > currentHandSize(): # Just made sure to notify of any shenanigans
            notify(":::Warning::: {} has skipped their End-of-Turn phase and they are holding more cards ({}) than their hand size maximum of {}".format(me,len(me.hand),currentHandSize()))
         else: notify(":::Warning::: {} has skipped their End-of-Turn phase".format(me))
         endofturn = False
   if ds == None:
      whisper ("Please perform the game setup first (Ctrl+Shift+S)")
      return
   if not me.isActivePlayer:
      if turn != 0 and not confirm("You opponent does not seem to have finished their turn properly with F12 yet. Continue?"): return
      else: me.setActivePlayer()
   playTurnStartSound()
   try: atTimedEffects('PreStart') # Trying to figure out where #275 is coming from
   except: notify(":::ERROR::: When executing PreStart scripts. Please report at: https://github.com/db0/Android-Netrunner-OCTGN/issues/275")
   currClicks = 0 # We wipe it again just in case they ended their last turn badly but insist on going through the next one.
   try: # Trying to figure out where #275 is coming from
      getMaxClicks = modClicks(action = 'chk')
      if getMaxClicks == 'ABORT': 
         if ds == 'corp': me.Clicks = 3
         else: me.Clicks = 4
      else: me.Clicks = getMaxClicks
   except: 
      notify(":::ERROR::: When setting max clicks. Please report at: https://github.com/db0/Android-Netrunner-OCTGN/issues/275")
      if ds == 'corp': me.Clicks = 3
      else: me.Clicks = 4      
   lastKnownNrClicks = me.Clicks
   try: # Trying to figure out where #275 is coming from
      myCards = [card for card in table if card.controller == me and card.owner == me]
      for card in myCards:
         if card._id in Stored_Type and fetchProperty(card, 'Type') != 'ICE': card.orientation &= ~Rot90 # Refresh all cards which can be used once a turn.
         if card.Name == '?' and card.owner == me and not card.isFaceUp:
            debugNotify("Peeking() at goToSot()")
            card.peek() # We also peek at all our facedown cards which the runner accessed last turn (because they left them unpeeked)
   except: notify(":::ERROR::: When trying to refresh cards. Please report at: https://github.com/db0/Android-Netrunner-OCTGN/issues/275")
   clearRestrictionMarkers()
   remoteServers = (card for card in table if card.Name == 'Remote Server' and card.controller != me)
   for card in remoteServers: remoteCall(card.controller,'passCardControl',[card,me]) 
   # At the start of each player's turn, we swap the ownership of all remote server, to allow them to double-click them (If they're a runner) or manipulate them (if they're a corp)
   # We do not use grabCardControl as that may take a while, as it's waiting for control change to resolve.                                                                                    
   newturn = True
   turn += 1
   autoRez()
   clearAllNewCards()
   if ds == 'runner':
      setGlobalVariable('Remote Run','False')
      setGlobalVariable('Central Run','False')
   atTimedEffects('Start') # Check all our cards to see if there's any Start of Turn effects active.
   announceSoT()
   opponent = ofwhom('onOpponent')

def autoRez():
   # A function which rezzes all cards which have been flagged to be auto-rezzed at the start of the turn.
   debugNotify(">>> autoRez()") #Debug
   mute()
   global autoRezFlags
   for cID in autoRezFlags:
      card = Card(cID)
      whisper("--- Attempting to Auto Rez {}".format(fetchProperty(card, 'Name')))
      if intRez(card, silentCost = True) == 'ABORT': whisper(":::WARNING::: Could not rez {} automatically. Ignoring".format(fetchProperty(card, 'Name')))
   del autoRezFlags[:]
   debugNotify("<<< autoRez()", 3) #Debug
#------------------------------------------------------------------------------
# Game Setup
#------------------------------------------------------------------------------

def createStartingCards():
   try:
      debugNotify(">>> createStartingCards()") #Debug
      if ds == "corp":
         if debugVerbosity >= 5: information("Creating Trace Card")
         traceCard = table.create("eb7e719e-007b-4fab-973c-3fe228c6ce20", (569 * flipBoard) + flipModX, (163 * flipBoard) + flipModY, 1, True) #The Trace card
         storeSpecial(traceCard)
         if debugVerbosity >= 5: information("Creating HQ")
         HQ = table.create("81cba950-9703-424f-9a6f-af02e0203762", (169 * flipBoard) + flipModX, (188 * flipBoard) + flipModY, 1, True)
         storeSpecial(HQ) # We pass control of the centrals to the runner, so that they can double click them to start runs
         HQ.setController(findOpponent())
         if debugVerbosity >= 5: information("Creating R&D")
         RD = table.create("fbb865c9-fccc-4372-9618-ae83a47101a2", (277 * flipBoard) + flipModX, (188 * flipBoard) + flipModY, 1, True)
         storeSpecial(RD)
         RD.setController(findOpponent())
         if debugVerbosity >= 5: information("Creating Archives")
         ARC = table.create("47597fa5-cc0c-4451-943b-9a14417c2007", (382 * flipBoard) + flipModX, (188 * flipBoard) + flipModY, 1, True)
         storeSpecial(ARC)
         ARC.setController(findOpponent())
         if debugVerbosity >= 5: information("Creating Virus Scan")
         AV = table.create("23473bd3-f7a5-40be-8c66-7d35796b6031", (478 * flipBoard) + flipModX, (165 * flipBoard) + flipModY, 1, True) # The Virus Scan card.
         storeSpecial(AV)
         try:
            BTN = table.create("fb146e53-714b-4b29-861a-d58ca9840c00", (638 * flipBoard) + flipModX, (25 * flipBoard) + flipModY, 1, True) # The No Rez Button
            BTN = table.create("e904542b-83db-4022-9e8e-9369fe7bc761", (638 * flipBoard) + flipModX, (95 * flipBoard) + flipModY, 1, True) # The OK Button
            BTN = table.create("0887f64f-4fe8-4a5b-9d41-77408fe0224b", (638 * flipBoard) + flipModX, (165 * flipBoard) + flipModY, 1, True) # The Wait Button
         except: delayed_whisper("!!!ERROR!!! In createStartingCards()\n!!! Please Install Markers Set v2.2.1+ !!!")
      else:
         if debugVerbosity >= 5: information("Creating Trace Card")
         traceCard = table.create("eb7e719e-007b-4fab-973c-3fe228c6ce20", (342 * flipBoard) + flipModX, (-331 * flipBoard) + flipModY, 1, True) #The Trace card
         storeSpecial(traceCard)
         #TC = table.create("71a89203-94cd-42cd-b9a8-15377caf4437", 471, -325, 1, True) # The Technical Difficulties card.
         #TC.moveToTable(471, -325) # It's never creating them in the right place. Move is accurate.
         #storeSpecial(TC)
         try:
            BTN = table.create("33ac6951-93ec-4034-9578-0d7dcc77c3f8", (638 * flipBoard) + flipModX, (-80 * flipBoard) + flipModY, 1, True) # The Access Imminent Button
            BTN = table.create("e904542b-83db-4022-9e8e-9369fe7bc761", (638 * flipBoard) + flipModX, (-150 * flipBoard) + flipModY, 1, True) # The OK Button
            BTN = table.create("0887f64f-4fe8-4a5b-9d41-77408fe0224b", (638 * flipBoard) + flipModX, (-220 * flipBoard) + flipModY, 1, True) # The Wait Button
         except: delayed_whisper("!!!ERROR!!! In createStartingCards()\n!!! Please Install Markers Set v2.2.1+ !!!")
   except: notify("!!!ERROR!!! {} - In createStartingCards()\n!!! PLEASE INSTALL MARKERS SET FILE !!!".format(me))


def intJackin(group = table, x = 0, y = 0, manual = False):
   debugNotify(">>> intJackin(){}".format(extraASDebug())) #Debug
   mute()
   if not Identity:
      information("::: ERROR::: No identify found! Please load a deck which contains an identity card.")
      return
   else:
      if Identity.group == table and not manual and not confirm("Are you sure you want to setup for a new game? (This action should only be done after a table reset)"): return
   #for type in Automations: switchAutomation(type,'Announce') # Too much spam.
   deck = me.piles['R&D/Stack']
   debugNotify("Checking Deck", 3)
   if len(deck) == 0:
      whisper ("Please load a deck first!")
      return
   debugNotify("Placing Identity", 3)
   debugNotify("Identity is: {}".format(Identity), 3)
   if ds == "corp":
      Identity.moveToTable((169 * flipBoard) + flipModX, (255 * flipBoard) + flipModY)
      rnd(1,10) # Allow time for the ident to be recognised
      modClicks(count = 3, action = 'set to')
      me.MU = 0
      notify("{} is the CEO of the {} Corporation".format(me,Identity))
   else:
      Identity.moveToTable((106 * flipBoard) + flipModX, (-331 * flipBoard) + flipModY)
      rnd(1,10)  # Allow time for the ident to be recognised
      modClicks(count = 4, action = 'set to')
      me.MU = 4
      BL = num(Identity.Cost)
      me.counters['Base Link'].value = BL
      notify("{} is representing the Runner {}. They start with {} {}".format(me,Identity,BL,uniLink()))
   debugNotify("Creating Starting Cards", 3)
   createStartingCards()
   debugNotify("Shuffling Deck", 3)
   shuffle(me.piles['R&D/Stack'])
   debugNotify("Drawing 5 Cards", 3)
   notify("{}'s {} is shuffled ".format(me,pileName(me.piles['R&D/Stack'])))
   drawMany(me.piles['R&D/Stack'], 5)
   debugNotify("Reshuffling Deck", 3)
   shuffle(me.piles['R&D/Stack']) # And another one just to be sure
   executePlayScripts(Identity,'STARTUP')
   initGame()
   setleague(manual = False) # Check if this is a league match
   announceSupercharge()

def createRemoteServer(group,x=0,y=0):
   debugNotify(">>> createSDF(){}".format(extraASDebug())) #Debug
   Server = table.create("d59fc50c-c727-4b69-83eb-36c475d60dcb", x, y - (40 * playerside), 1, False)
   placeCard(Server,'INSTALL')

#------------------------------------------------------------------------------
# Run...
#------------------------------------------------------------------------------
def intRun(aCost = 1, Name = 'R&D', silent = False):
   debugNotify(">>> intRun(). Current status:{}".format(getGlobalVariable('status'))) #Debug
   if ds != 'runner':
      whisper(":::ERROR:::Corporations can't run!")
      return 'ABORT'
   if re.search(r'running',getGlobalVariable('status')):
      whisper(":::ERROR:::You are already jacked-in. Please end the previous run (press [Esc] or [F3]) before starting a new one")
      return
   targetPL = findOpponent()
   BadPub = targetPL.counters['Bad Publicity'].value
   enemyIdent = getSpecial('Identity',targetPL)
   myIdent = getSpecial('Identity',me)
   abortArrow = False
   ### Custom Run Prevention Cards ###
   if enemyIdent.Subtitle == "Replicating Perfection":
      debugNotify("Checking Jinteki: Replicating Perfection restriction")
      if getGlobalVariable('Central Run') == 'False' and Name == 'Remote': 
         whisper(":::ERROR::: Your opponent is playing {}:{}. You cannot run a remote server until you've first run on a central server".format(enemyIdent,enemyIdent.Subtitle))
         return 'ABORT'
   ClickCost = useClick(count = aCost)
   if ClickCost == 'ABORT': return 'ABORT'
   playRunStartSound()
   if Name == 'Archives': announceTXT = 'the Archives'
   elif Name == 'Remote': announceTXT = 'a remote server'
   else: announceTXT = Name
   if not silent: notify ("{} to start a run on {}.".format(ClickCost,announceTXT))
   #barNotifyAll('#000000',"{} starts a run on {}.".format(fetchRunnerPL(),announceTXT))
   debugNotify("Setting bad publicity", 2)
   if BadPub > 0:
         myIdent.markers[mdict['BadPublicity']] += BadPub
         notify("--> The Bad Publicity of {} allows {} to secure {} for this run".format(enemyIdent,myIdent,uniCredit(BadPub)))
   debugNotify("Painting run Arrow", 2)
   if Name != 'Remote':
      targetServer = getSpecial(Name,enemyIdent.controller)
      if not targetServer: abortArrow = True # If for some reason we can't find the relevant central server card (e.g. during debug), we abort gracefully
      setGlobalVariable('Central Run','True')
   else:
      targetRemote = findTarget("Targeted-atRemote Server-isMutedTarget") # We try to see if the player had a remote targeted, if so we make it the target.
      if len(targetRemote) > 0: targetServer = targetRemote[0] # If there's no remote targeted, we paint no arrow.
      else: abortArrow = True # If we cannot figure out which remote the runner is running on,
      setGlobalVariable('Remote Run','True')
   if not abortArrow:
      targetServer.target(False)
      myIdent.arrow(targetServer, True)
   setGlobalVariable('status','running{}'.format(Name))
   atTimedEffects('Run')

def runHQ(group, x=0,y=0):
   debugNotify(">>> runHQ(){}".format(extraASDebug())) #Debug
   intRun(1, "HQ")

def runRD(group, x=0,y=0):
   debugNotify(">>> runRD(){}".format(extraASDebug())) #Debug
   intRun(1, "R&D")

def runArchives(group, x=0,y=0):
   debugNotify(">>> runArchives(){}".format(extraASDebug())) #Debug
   intRun(1, "Archives")

def runServer(group, x=0,y=0):
   debugNotify(">>> runSDF(){}".format(extraASDebug())) #Debug
   intRun(1, "Remote")

def jackOut(group=table,x=0,y=0, silent = False):
   mute()
   debugNotify(">>> jackOut(). Current status:{}".format(getGlobalVariable('status'))) #Debug
   opponent = ofwhom('-ofOpponent') # First we check if our opponent is a runner or a corp.
   if ds == 'corp': targetPL = opponent
   else: targetPL = me
   enemyIdent = getSpecial('Identity',targetPL)
   myIdent = getSpecial('Identity',me)
   runTargetRegex = re.search(r'running([A-Za-z&]+)',getGlobalVariable('status'))
   if not runTargetRegex: # If the runner is not running at the moment, do nothing
      if targetPL != me: whisper("{} is not running at the moment.".format(targetPL))
      else: whisper("You are not currently jacked-in.")
   else: # Else announce they are jacked in and resolve all post-run effects.
      runTarget = runTargetRegex.group(1) # If the runner is not feinting, then extract the target from the shared variable
      if ds == 'runner' : myIdent.markers[mdict['BadPublicity']] = 0 #If we're the runner, then remove out remaining bad publicity tokens
      else: 
         grabCardControl(enemyIdent) # Taking control to avoid errors.
         enemyIdent.markers[mdict['BadPublicity']] = 0 # If we're not the runner, then find the runners and remove any bad publicity tokens
         passCardControl(enemyIdent,enemyIdent.owner)
      if getGlobalVariable('SuccessfulRun') == 'False': playRunUnsuccesfulSound()
      atTimedEffects('JackOut') # If this was a simple jack-out, then make the end-of-run effects trigger only jack-out effects
      setGlobalVariable('status','idle') # Clear the run variable
      setGlobalVariable('feintTarget','None') # Clear any feinted targets
      setGlobalVariable('SuccessfulRun','False') # Set the variable which tells the code if the run was successful or not, to false.
      setGlobalVariable('Access','DENIED')
      setGlobalVariable('accessAttempts','0')
      debugNotify("About to announce end of Run", 2) #Debug
      if not silent: # Announce the end of run from the perspective of each player.
         if targetPL != me: 
            notify("{} has kicked {} out of their corporate grid".format(myIdent,enemyIdent))
            playCorpEndSound()
         else: notify("{} has jacked out of their run on the {} server".format(myIdent,runTarget))
      #barNotifyAll('#000000',"{} has jacked out.".format(fetchRunnerPL()))
      clearAll(True, True) # On jack out we clear all player's counters, but don't discard cards from the table.
   debugNotify("<<< jackOut()", 3) # Debug

def runSuccess(group=table,x=0,y=0, silent = False):
   mute()
   debugNotify(">>> runSuccess(). Current status:{}".format(getGlobalVariable('status'))) #Debug
   opponent = ofwhom('-ofOpponent') # First we check if our opponent is a runner or a corp.
   if ds == 'corp': 
      if re.search(r'running',getGlobalVariable('status')):
         notify("{} acknowledges a successful run.".format(me))
         setGlobalVariable('Access','GRANTED')
      else: whisper("Nobody is running your servers at the moment!")
   else:
      runTargetRegex = re.search(r'running([A-Za-z&]+)',getGlobalVariable('status'))
      if not runTargetRegex: # If the runner is not running at the moment, do nothing
         whisper(":::Error::: You are not currently jacked-in.")
      elif getGlobalVariable('SuccessfulRun') == 'True':
         whisper(":::Error::: You have already completed this run succesfully. Jacking out instead...")
         jackOut()
      elif getGlobalVariable('Access') == 'DENIED' and num(getGlobalVariable('accessAttempts')) == 0 and getGlobalVariable('Quick Access') != 'Fucking':
         BUTTON_Access() # The first time a player tries to succeed the run, we press the button for them
      elif getGlobalVariable('Quick Access') == 'False' and getGlobalVariable('Access') == 'DENIED' and (num(getGlobalVariable('accessAttempts')) < 3 or (num(getGlobalVariable('accessAttempts')) >= 3 and not confirm("Corp has not yet acknowledged your successful run. Bypass their reaction window?"))):
         notify(":::WARNING::: {} is about to access the server and is waiting for final corporation reacts.\n(Corp must now press the [OK] button F3 to acknowledge the access.)".format(me))
         setGlobalVariable('accessAttempts',str(num(getGlobalVariable('accessAttempts')) + 1))
         return 'DENIED'
      else:
         setGlobalVariable('SuccessfulRun','True')
         if getGlobalVariable('feintTarget') != 'None': runTarget = getGlobalVariable('feintTarget') #If the runner is feinting, now change the target server to the right one
         else: runTarget = runTargetRegex.group(1) # If the runner is not feinting, then extract the target from the shared variable
         atTimedEffects('SuccessfulRun')
         notify("{} has successfully run the {} server".format(identName,runTarget))
         #barNotifyAll('#000000',"{} has run succesfully.".format(fetchRunnerPL()))
         if runTarget == 'Remote': setGlobalVariable('Remote Run','Success')
         else: setGlobalVariable('Central Run','Success')
   debugNotify("<<< runSuccess()", 3) # Debug
#------------------------------------------------------------------------------
# Tags...
#------------------------------------------------------------------------------
def pay2andDelTag(group, x = 0, y = 0):
   debugNotify(">>> pay2andDelTag(){}".format(extraASDebug())) #Debug
   mute()
   if ds != "runner":
      whisper("Only runners can use this action")
      return
   if me.Tags < 1:
      whisper("You don't have any tags")
      return
   ClickCost = useClick()
   if ClickCost == 'ABORT': return
   playRemoveTagSound()
   dummyCard = getSpecial('Tracing') # Just a random card to pass to the next function. Can't be bothered to modify the function to not need this.
   reduction = reduceCost(dummyCard, 'DELTAG', 2)
   if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))
   elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
   else: extraText = ''
   if payCost(2 - reduction) == "ABORT":
      me.Clicks += 1 # If the player didn't notice they didn't have enough credits, we give them back their click
      return # If the player didn't have enough money to pay and aborted the function, then do nothing.
   me.counters['Tags'].value -= 1
   notify ("{} and pays {}{} to lose a tag.".format(ClickCost,uniCredit(2 - reduction),extraText))

#------------------------------------------------------------------------------
# Markers
#------------------------------------------------------------------------------
def intAddCredits ( card, count):
   debugNotify(">>> intAddCredits(){}".format(extraASDebug())) #Debug
   mute()
   if ( count > 0):
      card.markers[mdict['Credits']] += count
      if ( card.isFaceUp == True): notify("{} adds {} from the bank on {}.".format(me,uniCredit(count),card))
      else: notify("{} adds {} on a card.".format(me,uniCredit(count)))

def addCredits(card, x = 0, y = 0):
   debugNotify(">>> addCredits(){}".format(extraASDebug())) #Debug
   mute()
   count = askInteger("Add how many Credits?", 1)
   if count == None: return
   intAddCredits(card, count)

def remCredits(card, x = 0, y = 0):
   debugNotify(">>> remCredits(){}".format(extraASDebug())) #Debug
   mute()
   count = askInteger("Remove how many Credits?", 1)
   if count == None: return
   if count > card.markers[mdict['Credits']]: count = card.markers[mdict['Credits']]
   card.markers[mdict['Credits']] -= count
   if card.isFaceUp == True: notify("{} removes {} from {}.".format(me,uniCredit(count),card))
   else: notify("{} removes {} from a card.".format(me,uniCredit(count)))

def remXCredits (card, x = 0, y = 0):
   debugNotify(">>> remCredits2BP(){}".format(extraASDebug())) #Debug
   mute()
   count = askInteger("Remove how many Credits?", 1)
   if count == None: return
   if count > card.markers[mdict['Credits']]: count = card.markers[mdict['Credits']]
   card.markers[mdict['Credits']] -= count
   me.counters['Credits'].value += count
   if card.isFaceUp == True: notify("{} removes {} from {} to their Credit Pool.".format(me,uniCredit(count),card))
   else: notify("{} takes {} from a card to their Credit Pool.".format(me,uniCredit(count)))

def addPlusOne(card, x = 0, y = 0):
   debugNotify(">>> addPlusOne(){}".format(extraASDebug())) #Debug
   mute()
   if mdict['MinusOne'] in card.markers:
      card.markers[mdict['MinusOne']] -= 1
   else:
      card.markers[mdict['PlusOne']] += 1
   notify("{} adds one +1 marker on {}.".format(me,card))

def addMinusOne(card, x = 0, y = 0):
   debugNotify(">>> addMinusOne(){}".format(extraASDebug())) #Debug
   mute()
   if mdict['PlusOne'] in card.markers:
      card.markers[mdict['PlusOne']] -= 1
   else:
      card.markers[mdict['MinusOne']] += 1
   notify("{} adds one -1 marker on {}.".format(me,card))

def addPlusOnePerm(card, x = 0, y = 0):
   debugNotify(">>> addPlusOnePerm(){}".format(extraASDebug())) #Debug
   mute()
   card.markers[mdict['PlusOnePerm']] += 1
   notify("{} adds one Permanent +1 marker on {}.".format(me,card))

def addMarker(cards, x = 0, y = 0): # A simple function to manually add any of the available markers.
   debugNotify(">>> addMarker(){}".format(extraASDebug())) #Debug
   mute()
   marker, quantity = askMarker() # Ask the player how many of the same type they want.
   if quantity == 0: return
   for card in cards: # Then go through their cards and add those markers to each.
      card.markers[marker] += quantity
      notify("{} adds {} {} counter to {}.".format(me, quantity, marker[0], card))

def addVirusCounter(card, x = 0, y = 0):
   card.markers[mdict['Virus']] += 1

def addPowerCounter(card, x = 0, y = 0):
   card.markers[mdict['Power']] += 1

def addAgendaCounter(card, x = 0, y = 0):
   card.markers[mdict['Agenda']] += 1
#------------------------------------------------------------------------------
# Advancing cards
#------------------------------------------------------------------------------
def advanceCardP(card, x = 0, y = 0):
   debugNotify(">>> advanceCardP(){}".format(extraASDebug())) #Debug
   mute()
   update()
   ClickCost = useClick()
   if ClickCost == 'ABORT': return
   reduction = reduceCost(card, 'ADVANCEMENT', 1)
   if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))
   elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
   else: extraText = ''
   if payCost(1 - reduction) == "ABORT":
      me.Clicks += 1 # If the player didn't notice they didn't have enough credits, we give them back their click
      return # If the player didn't have enough money to pay and aborted the function, then do nothing.
   card.markers[mdict['Advancement']] += 1
   remoteCall(findOpponent(),'playSound',['Advance-Card']) # Attempt to fix lag
   #playSound('Advance-Card')
   if card.isFaceUp: notify("{} and paid {}{} to advance {}.".format(ClickCost,uniCredit(1 - reduction),extraText,card))
   else: notify("{} and paid {}{} to advance a card.".format(ClickCost,uniCredit(1 - reduction),extraText))

def addXadvancementCounter(card, x=0, y=0):
   debugNotify(">>> addXadvancementCounter(){}".format(extraASDebug())) #Debug
   mute()
   count = askInteger("Add how many counters?", 1)
   if count == None: return
   card.markers[mdict['Advancement']] += count
   if card.isFaceUp == True: notify("{} adds {} advancement counters on {}.".format(me,count,card))
   else: notify("{} adds {} advancement counters on a card.".format(me,count))

def delXadvancementCounter(card, x = 0, y = 0):
   debugNotify(">>> delXadvancementCounter(){}".format(extraASDebug())) #Debug
   mute()
   count = askInteger("Remove how many counters?", 1)
   if count == None: return
   if count > card.markers[mdict['Advancement']]: count = card.markers[mdict['Advancement']]
   card.markers[mdict['Advancement']] -= count
   if card.isFaceUp == True: notify("{} removes {} advancement counters on {}.".format(me,count,card))
   else: notify("{} adds {} advancement counters on a card.".format(me,count))

def advanceCardM(card, x = 0, y = 0):
   debugNotify(">>> advanceCardM(){}".format(extraASDebug())) #Debug
   mute()
   card.markers[mdict['Advancement']] -= 1
   if (card.isFaceUp == True): notify("{} removes 1 advancement counter on {}.".format(me,card))
   else: notify("{} removes 1 advancement counter on a card.".format(me))

#---------------------
# Tracing...
#----------------------

def inputTraceValue (card, x=0,y=0, limit = 0, silent = False):
   debugNotify(">>> inputTraceValue(){}".format(extraASDebug())) #Debug
   mute()
   limitText = ''
   card = getSpecial('Tracing')
   limit = num(limit) # Just in case
   debugNotify("Trace Limit: {}".format(limit), 2)
   if limit > 0: limitText = '\n\n(Max Trace Power: {})'.format(limit)
   if ds == 'corp': traceTXT = 'Trace'
   else: traceTXT = 'Link'
   if ds == 'corp': 
      barNotifyAll('#000000',"{} is initiating a trace...".format(me))
      playTraceStartSound()
   else: barNotifyAll('#000000',"{} is working on their base link".format(me))
   TraceValue = askInteger("Increase {} Strength by how much?{}".format(traceTXT,limitText), 0)
   if TraceValue == None:
      whisper(":::Warning::: Trace attempt aborted by player.")
      return 'ABORT'
   while limit > 0 and TraceValue > limit:
      TraceValue = askInteger("Please increase by equal to or less than the max trace power!\nIncrease Trace power by how much?{}".format(limitText), 0)
      if TraceValue == None:
         whisper(":::Warning::: Trace attempt aborted by player.")
         return 'ABORT'
   while TraceValue - reduceCost(card, 'TRACE', TraceValue, dryRun = True) > me.Credits and not confirm("You do not seem to have enough bits to increase your Trace Strength by this amount. Continue anyway?"):
      TraceValue = askInteger("Increase {} Strength by how much?{}".format(traceTXT, limitText), 0)
      if TraceValue == None:
         whisper(":::Warning::: Trace attempt aborted by player.")
         return 'ABORT'
   reduction = reduceCost(card, 'TRACE', TraceValue)
   if reduction > 0: extraText = " (Cost reduced by {})".format(uniCredit(reduction))
   elif reduction < 0: extraText = " (Cost increased by {})".format(uniCredit(abs(reduction)))
   else: extraText = ''
   if payCost(TraceValue - reduction)  == 'ABORT': return
   #card.markers[mdict['Credits']] = TraceValue
   if ds == 'corp':
      if not silent: notify("{} starts a trace with a base strength of 0 reinforced by {}{}.".format(me,TraceValue,extraText))
      setGlobalVariable('CorpTraceValue',str(TraceValue))
      OpponentTrace = getSpecial('Tracing',ofwhom('ofOpponent'))
      OpponentTrace.highlight = EmergencyColor
   else:
      if not silent: notify("{} reinforces their {} by {} for a total of {}{}.".format(me,uniLink(),TraceValue, TraceValue + me.counters['Base Link'].value,extraText))
      CorpTraceValue = num(getGlobalVariable('CorpTraceValue'))
      currentTraceEffectTuple = eval(getGlobalVariable('CurrentTraceEffect'))
      debugNotify("currentTraceEffectTuple = {}".format(currentTraceEffectTuple), 2)
      if CorpTraceValue > TraceValue + me.counters['Base Link'].value:
         notify("-- {} has been traced".format(identName))
         playTraceLostSound()
         autoscriptOtherPlayers('UnavoidedTrace', card)
         try:
            if currentTraceEffectTuple[1] != 'None':
               debugNotify("Found currentTraceEffectTuple")
               executePostEffects(Card(currentTraceEffectTuple[0]),currentTraceEffectTuple[1], count = CorpTraceValue - TraceValue - me.counters['Base Link'].value) # We sent this function the card which triggered the trace, and the effect which was triggered.
         except: 
            debugNotify("currentTraceEffectTuple == None")
            pass # If it's an exception it means our tuple does not exist, so there's no current trace effects. Manual use of the trace card?
      else:
         notify("-- {} has eluded the trace".format(identName))
         playTraceAvoidedSound()
         autoscriptOtherPlayers('EludedTrace', card)
         try:
            if currentTraceEffectTuple[2] != 'None':
               executePostEffects(Card(currentTraceEffectTuple[0]),currentTraceEffectTuple[2]) # We sent this function the card which triggered the trace, and the effect which was triggered.
         except: pass # If it's an exception it means our tuple does not exist, so there's no current trace effects. Manual use of the trace card?
      setGlobalVariable('CurrentTraceEffect','None') # Once we're done with the current effects of the trace, we clear the CurrentTraceEffect global variable
      setGlobalVariable('CorpTraceValue','None') # And the corp's trace value
      card.highlight = None
   return TraceValue

#def revealTraceValue (card, x=0,y=0): # Obsolete in ANR
#   if debugVerbosity >= 1: notify(">>> revealTraceValue(){}".format(extraASDebug())) #Debug
#   mute()
#   global TraceValue
#   card = getSpecial('Tracing')
#   card.isFaceUp = True
#   card.markers[mdict['Credits']] = TraceValue
#   notify ( "{} reveals a Trace Value of {}.".format(me,TraceValue))
#   if TraceValue == 0: autoscriptOtherPlayers('clearTraceAttempt') # if the trace value is 0, then we consider the trace attempt as valid, so we call scripts triggering from that.
#   TraceValue = 0

#def payTraceValue (card, x=0,y=0):
#   if debugVerbosity >= 1: notify(">>> payTraceValue(){}".format(extraASDebug())) #Debug
#   mute()
#   extraText = ''
#   card = getSpecial('Tracing')
#   reduction = reduceCost(card, 'TRACE', card.markers[mdict['Credits']])
#   if reduction: extraText = " (reduced by {})".format(uniCredit(reduction))
#   if payCost(card.markers[mdict['Credits']] - reduction)  == 'ABORT': return
#   notify ("{} pays the {}{} they used during this trace attempt.".format(me,uniCredit(card.markers[mdict['Credits']]),extraText))
#   card.markers[mdict['Credits']] = 0
#   autoscriptOtherPlayers('TraceAttempt',card)

def cancelTrace ( card, x=0,y=0):
   debugNotify(">>> cancelTrace(){}".format(extraASDebug())) #Debug
   mute()
   TraceValue = 0
   card.markers[mdict['Credits']] = 0
   notify ("{} cancels the Trace.".format(me) )

#------------------------------------------------------------------------------
# Counter & Damage Functions
#-----------------------------------------------------------------------------

def payCost(count = 1, cost = 'not free', counter = 'BP', silentCost = False): # A function that removed the cost provided from our credit pool, after checking that we have enough.
   debugNotify(">>> payCost(){}".format(extraASDebug())) #Debug
   if cost != 'not free': return 'free'
   count = num(count)
   if count <= 0 : return 0# If the card has 0 cost, there's nothing to do.
   if counter == 'BP':
      if me.counters['Credits'].value < count:
         if silentCost: return 'ABORT'
         if not confirm("You do not seem to have enough Credits in your pool to take this action. Are you sure you want to proceed? \
                      \n(If you do, your Credit Pool will go to the negative. You will need to increase it manually as required.)"): return 'ABORT' # If we don't have enough Credits in the pool, we assume card effects or mistake and notify the player that they need to do things manually.
      me.counters['Credits'].value -= count
   elif counter == 'AP': # We can also take costs from other counters with this action.
      if me.counters['Agenda Points'].value < count and not confirm("You do not seem to have enough Agenda Points to take this action. Are you sure you want to proceed? \
         \n(If you do, your Agenda Points will go to the negative. You will need to increase them manually as required.)"): return 'ABORT'
      me.counters['Agenda Points'].value -= count
   return "{} (remaining: {})".format(uniCredit(count),uniCredit(me.Credits))

def findExtraCosts(card, action = 'REZ'):
   # Some hardcoded effects that increase the cost of a card.
   debugNotify(">>> findExtraCosts(). Action is: {}.".format(action)) #Debug
   increase = 0
   for marker in card.markers:
      if re.search(r'Cortez Chip',marker[0]) and action == 'REZ': increase += 2 * card.markers[marker]
   debugNotify("<<< findExtraCosts(). Increase: {}.".format(increase), 3) #Debug
   return increase

def reduceCost(card, action = 'REZ', fullCost = 0, dryRun = False, reversePlayer = False): 
   # reversePlayer is a variable that holds if we're looking for cost reducing effects affecting our opponent, rather than the one running the script.
   global costReducers,costIncreasers
   type = action.capitalize()
   debugNotify(">>> reduceCost(). Action is: {}. FullCost = {}".format(type,fullCost)) #Debug
   #if fullCost == 0: return 0 # Not used as we now have actions which also increase costs
   fullCost = abs(fullCost)
   reduction = 0
   status = getGlobalVariable('status')
   debugNotify("Status: {}".format(status), 3)
   ### First we check if the card has an innate reduction.
   Autoscripts = fetchProperty(card, 'AutoScripts').split('||')
   if len(Autoscripts):
      debugNotify("Checking for onPay reductions")
      for autoS in Autoscripts:
         if not re.search(r'onPay', autoS):
            debugNotify("No onPay trigger found in {}!".format(autoS), 2)
            continue
         reductionSearch = re.search(r'Reduce([0-9]+)Cost({}|All)'.format(type), autoS)
         if debugVerbosity >= 2: #Debug
            if reductionSearch: notify("!!! self-reduce regex groups: {}".format(reductionSearch.groups()))
            else: notify("!!! No self-reduce regex Match!")
         oppponent = ofwhom('-ofOpponent')
         if re.search(r'ifNoisyOpponent', autoS) and oppponent.getGlobalVariable('wasNoisy') != '1':
            debugNotify("No required noisy bit found!", 2)
            continue
         count = num(reductionSearch.group(1))
         targetCards = findTarget(autoS,card = card)
         multiplier = per(autoS, card, 0, targetCards)
         reduction += (count * multiplier)
         fullCost -= (count * multiplier)
         if count * multiplier > 0 and not dryRun: notify("-- {}'s full cost is reduced by {}".format(card,count * multiplier))
   else:
      debugNotify("No self-reducing autoscripts found!", 2)
   ### First we go through the table and gather any cards providing potential cost reduction
   if not gatheredCardList: # A global variable set during access of card use, that stores if we've scanned the tables for cards which reduce costs, so that we don't have to do it again.
      debugNotify("No gatheredCardList. About to Scan table cards.")
      del costReducers[:]
      del costIncreasers[:]
      RC_cardList = sortPriority([c for c in table
                              if c.isFaceUp
                              and c.highlight != RevealedColor
                              and c.highlight != StealthColor # Cards reserved for stealth do not give the credits elsewhere. Stealth cards like dagger use those credits via TokensX
                              and c.highlight != InactiveColor])
      reductionRegex = re.compile(r'(Reduce|Increase)([0-9#XS]+)Cost({}|All)-affects([A-Z][A-Za-z ]+)(-not[A-Za-z_& ]+)?'.format(type)) # Doing this now, to reduce load.
      for c in RC_cardList: # Then check if there's other cards in the table that reduce its costs.
         debugNotify("Scanning {}".format(c), 2) #Debug
         Autoscripts = CardsAS.get(c.model,'').split('||')
         if len(Autoscripts) == 0: 
            debugNotify("No AS found. Continuing")
            continue
         for autoS in Autoscripts:
            debugNotify("AS: {}".format(autoS), 2) #Debug
            if not chkRunningStatus(autoS): 
               debugNotify("Rejecting because not running")
               continue # if the reduction is only during runs, and we're not in a run, bypass this effect
            if not chkPlayer(autoS, origController.get(c._id,c.controller), False, reversePlayerChk = reversePlayer): 
               debugNotify("Rejecting because player does not match")
               continue
            reductionSearch = reductionRegex.search(autoS)
            if debugVerbosity >= 2: #Debug
               if reductionSearch: notify("!!! Regex is {}".format(reductionSearch.groups()))
               else: notify("!!! No reduceCost regex Match!")
            if re.search(r'excludeDummy', autoS) and c.highlight == DummyColor: continue
            if re.search(r'ifInstalled',autoS) and (card.group != table or card.highlight == RevealedColor): continue
            if reductionSearch: # If the above search matches (i.e. we have a card with reduction for Rez and a condition we continue to check if our card matches the condition)
               if reductionSearch.group(1) == 'Reduce':
                  debugNotify("Adding {} to cost reducers".format(c))
                  costReducers.append((c,reductionSearch,autoS)) # We put the costReducers in a different list, as we want it to be checked after all the increasers are checked
               else:
                  debugNotify("Adding {} to cost Increasers".format(c))
                  costIncreasers.append((c,reductionSearch,autoS)) # Cost increasing cards go into the main list we'll check in a bit, as we need to check them first.
                  # In each entry we store a tuple of the card object and the search result for its cost modifying abilities, so that we don't regex again later.
   else: debugNotify("gatheredCardList = {}".format(gatheredCardList))
   ### Now we check if any cards increase costs first since those costs can be later reduced via BP or other cards.
   for cTuple in costIncreasers:  
      debugNotify("Checking next cTuple", 4) #Debug
      c = cTuple[0]
      reductionSearch = cTuple[1]
      autoS = cTuple[2]
      debugNotify("cTuple[0] (i.e. card) is: {}".format(c), 2) #Debug
      debugNotify("cTuple[2] (i.e. autoS) is: {}".format(autoS), 4) #Debug
      if reductionSearch.group(4) == 'All' or checkCardRestrictions(gatherCardProperties(card), prepareRestrictions(autoS,seek = 'reduce')):
         debugNotify(" ### Search match! Increase Value is {}".format(reductionSearch.group(2)), 3) # Debug
         if not checkSpecialRestrictions(autoS,card): continue # Check if the card who's cost we're reducing matches the special restrictions of the autoscript
         if re.search(r'ifHosted',autoS): 
            c = fetchHost(card)
            if not c: continue # If we're only reducing cost for hosted cards and it isn't one, we do nothing.
         if re.search(r'onlyOnce',autoS):
            if dryRun: # For dry Runs we do not want to add the "Activated" token on the card.
               if oncePerTurn(c, act = 'dryRun') == 'ABORT': continue
            else:
               if oncePerTurn(c, act = 'automatic') == 'ABORT': continue # if the card's effect has already been used, check the next one
         if reductionSearch.group(2) == '#':
            markersCount = c.markers[mdict['Credits']]
            markersRemoved = 0
            while markersCount > 0:
               debugNotify("Increasing Cost with and Markers from {}".format(c), 2) # Debug
               reduction -= 1
               fullCost += 1
               markersCount -= 1
               markersRemoved += 1
            if not dryRun and markersRemoved != 0:
               c.markers[mdict['Credits']] -= markersRemoved # If we have a dryRun, we don't remove any tokens.
               notify(" -- {} credits are used from {}".format(markersRemoved,c))
         elif reductionSearch.group(2) == 'X':
            markerName = re.search(r'-perMarker{([\w ]+)}', autoS)
            try:
               marker = findMarker(c, markerName.group(1))
               if marker:
                  for iter in range(c.markers[marker]):
                     reduction -= 1
                     fullCost += 1
            except: notify("!!!ERROR!!! ReduceXCost - Bad Script")
         elif reductionSearch.group(2) == 'S': # 'S' Stands for Special (i.e. custom effects)
            if c.name == 'Running Interference':
               if card.Type == 'ICE':  
                  reduction -= num(card.Cost)
                  fullCost += num(card.Cost)
         else:
            for iter in range(num(reductionSearch.group(2))):  # if there is a match, the total reduction for this card's cost is increased.
               reduction -= 1
               fullCost += 1
   ### We now check for cards which reduce costs universally and as a constant effect               
   for cTuple in costReducers: 
      debugNotify("Checking next cTuple", 4) #Debug
      c = cTuple[0]
      reductionSearch = cTuple[1]
      autoS = cTuple[2]
      debugNotify("cTuple[0] (i.e. card) is: {}".format(c), 2) #Debug
      debugNotify("cTuple[2] (i.e. autoS) is: {}".format(autoS), 4) #Debug
      if reductionSearch.group(4) == 'All' or checkCardRestrictions(gatherCardProperties(card), prepareRestrictions(autoS,seek = 'reduce')):
         debugNotify(" ### Search match! Reduction Value is {}".format(reductionSearch.group(2)), 3) # Debug
         if not checkSpecialRestrictions(autoS,card): continue # Check if the card who's cost we're reducing matches the special restrictions of the autoscript
         if re.search(r'ifHosted',autoS): 
            c = fetchHost(card)
            if not c: continue # If we're only reducing cost for hosted cards and it isn't one, we do nothing.
         if re.search(r'onlyOnce',autoS):
            if dryRun: # For dry Runs we do not want to add the "Activated" token on the card.
               if oncePerTurn(c, act = 'dryRun') == 'ABORT': continue
            else:
               if oncePerTurn(c, act = 'automatic') == 'ABORT': continue # if the card's effect has already been used, check the next one
         if reductionSearch.group(2) == '#' and c.highlight == PriorityColor: # We also check if we have any recurring credits to spend on cards which the player has prioritized. Those will spend before BP.
            markersCount = c.markers[mdict['Credits']]
            markersRemoved = 0
            while markersCount > 0:
               debugNotify("Reducing Cost with and Markers from {}".format(c), 2) # Debug
               if fullCost > 0:
                  reduction += 1
                  fullCost -= 1
                  markersCount -= 1
                  markersRemoved += 1
               else: break
            if not dryRun and markersRemoved != 0:
               c.markers[mdict['Credits']] -= markersRemoved # If we have a dryRun, we don't remove any tokens.
               notify(" -- {} credits are used from {}".format(markersRemoved,c))
         elif reductionSearch.group(2) == 'X':
            markerName = re.search(r'-perMarker{([\w ]+)}', autoS)
            try:
               marker = findMarker(c, markerName.group(1))
               if marker:
                  for iter in range(c.markers[marker]):
                     if fullCost > 0:
                        reduction += 1
                        fullCost -= 1
            except: notify("!!!ERROR!!! ReduceXCost - Bad Script")
         else:
            for iter in range(num(reductionSearch.group(2))):  # if there is a match, the total reduction for this card's cost is increased.
               if fullCost > 0:
                  reduction += 1
                  fullCost -= 1
   ### Now we check if we're in a run and we have bad publicity credits to spend on reducing costs, since we want to spend that first usually.
   if re.search(r'running',status) and fullCost > 0:
      debugNotify("Checking for running reductions")
      if type == 'Force': myIdent = getSpecial('Identity',ofwhom('-ofOpponent'))
      else: myIdent = getSpecial('Identity',me)
      if myIdent.markers[mdict['BadPublicity']]:
         usedBP = 0
         BPcount = myIdent.markers[mdict['BadPublicity']]
         debugNotify("BPcount = {}".format(BPcount), 2)
         while fullCost > 0 and BPcount > 0:
            reduction += 1
            fullCost -= 1
            usedBP += 1
            BPcount -= 1
            if fullCost == 0: break
         if not dryRun and usedBP != 0:
            myIdent.markers[mdict['BadPublicity']] -= usedBP
            notify(" -- {} spends {} Bad Publicity credits".format(myIdent,usedBP))
   for cTuple in costReducers: # Finally we check for cards which also reduce costs by spending credits on themselves (since we only want to remove those as a last resort.)
      debugNotify("Checking next cTuple", 4) #Debug
      c = cTuple[0]
      reductionSearch = cTuple[1]
      autoS = cTuple[2]
      debugNotify("cTuple[0] (i.e. card) is: {}".format(c), 2) #Debug
      debugNotify("cTuple[2] (i.e. autoS) is: {}".format(autoS), 4) #Debug
      if reductionSearch.group(4) == 'All' or checkCardRestrictions(gatherCardProperties(card), prepareRestrictions(autoS,seek = 'reduce')):
         debugNotify(" ### Search match! Reduction Value is {}".format(reductionSearch.group(2)), 3) # Debug
         if not checkSpecialRestrictions(autoS,card): continue # Check if the card who's cost we're reducing matches the special restrictions of the autoscript
         if re.search(r'ifHosted',autoS): 
            c = fetchHost(card)
            if not c: continue # If we're only reducing cost for hosted cards and it isn't one, we do nothing.
         if re.search(r'onlyOnce',autoS):
            if dryRun: # For dry Runs we do not want to add the "Activated" token on the card.
               if oncePerTurn(c, act = 'dryRun') == 'ABORT': continue
            else:
               if oncePerTurn(c, act = 'automatic') == 'ABORT': continue # if the card's effect has already been used, check the next one
         if reductionSearch.group(2) == '#':
            markersCount = c.markers[mdict['Credits']]
            markersRemoved = 0
            while markersCount > 0:
               debugNotify("Reducing Cost with and Markers from {}".format(c), 2) # Debug
               if fullCost > 0:
                  reduction += 1
                  fullCost -= 1
                  markersCount -= 1
                  markersRemoved += 1
               else: break
            if not dryRun and markersRemoved != 0:
               c.markers[mdict['Credits']] -= markersRemoved # If we have a dryRun, we don't remove any tokens.
               notify(" -- {} credits are used from {}".format(markersRemoved,c))
   debugNotify("<<< reduceCost() with return {}".format(reduction))
   return reduction

def intdamageDiscard(count = 1):
   debugNotify(">>> intdamageDiscard()") #Debug
   mute()
   for DMGpt in range(count): #Start applying the damage
      notify("+++ Applying damage {} of {}...".format(DMGpt+1,count))
      if len(me.hand) == 0:
         notify ("{} has flatlined.".format(me))
         reportGame('Flatlined')
         break
      else:
         card = me.hand.random()
         if ds == 'corp': card.moveTo(me.piles['Archives(Hidden)']) # For testing.
         else: card.moveTo(me.piles['Heap/Archives(Face-up)'])
         notify("--DMG: {} discarded.".format(card))

def addBrainDmg(group, x = 0, y = 0):
   mute()
   debugNotify(">>> addBrainDmg()") #Debug
   enhancer = findEnhancements("Inflict1BrainDamage")
   DMG = 1 + enhancer
   if Automations['Damage Prevention'] and confirm("Is this damage preventable?") and findDMGProtection(DMG, 'Brain', me): # If we find any defense against it, inform that it was prevented
      notify ("{} prevents 1 Brain Damage.".format(me))
   else:
      applyBrainDmg()
      notify ("{} suffers 1 Brain Damage.".format(me))
      finalDMG = DMG - chkDmgSpecialEffects('Brain', DMG)[0]
      intdamageDiscard(finalDMG)
      #intdamageDiscard(me.hand)    
      playDMGSound('Brain')
      autoscriptOtherPlayers('BrainDMGInflicted',getSpecial('Identity',fetchRunnerPL()))
   debugNotify("<<< addBrainDmg()") #Debug

def applyBrainDmg(player = me, count = 1):
   debugNotify(">>> applyBrainDmg(){}".format(extraASDebug())) #Debug
   specialCard = getSpecial('Identity', player)
   specialCard.markers[mdict['BrainDMG']] += count

def addMeatDmg(group, x = 0, y = 0):
   mute()
   debugNotify(">>> addMeatDmg(){}".format(extraASDebug())) #Debug
   enhancer = findEnhancements("Inflict1MeatDamage")
   DMG = 1 + enhancer
   if Automations['Damage Prevention'] and confirm("Is this damage preventable?") and findDMGProtection(DMG, 'Meat', me):
      notify ("{} prevents 1 Meat Damage.".format(me))
   else:
      notify ("{} suffers 1 Meat Damage.".format(me))
      finalDMG = DMG - chkDmgSpecialEffects('Meat', DMG)[0]
      intdamageDiscard(finalDMG)
      #intdamageDiscard(me.hand)
      playDMGSound('Meat')
      autoscriptOtherPlayers('MeatDMGInflicted',getSpecial('Identity',fetchRunnerPL()))

def addNetDmg(group, x = 0, y = 0):
   mute()
   debugNotify(">>> addNetDmg(){}".format(extraASDebug())) #Debug
   enhancer = findEnhancements("Inflict1MeatDamage")
   DMG = 1 + enhancer
   if Automations['Damage Prevention'] and confirm("Is this damage preventable?") and findDMGProtection(DMG, 'Net', me):
      notify ("{} prevents 1 Net Damage.".format(me))
   else:
      notify ("{} suffers 1 Net Damage.".format(me))
      finalDMG = DMG - chkDmgSpecialEffects('Net', DMG)[0]
      intdamageDiscard(finalDMG)
      #intdamageDiscard(me.hand)
      playDMGSound('Net')
      autoscriptOtherPlayers('NetDMGInflicted',getSpecial('Identity',fetchRunnerPL()))

def getCredit(group, x = 0, y = 0):
   debugNotify(">>> getCredit(){}".format(extraASDebug())) #Debug
   mute()
   update()
   ClickCost = useClick()
   if ClickCost == 'ABORT': return
   creditsReduce = findCounterPrevention(1, 'Credits', me)
   if creditsReduce: extraTXT = " ({} forfeited)".format(uniCredit(creditsReduce))
   else: extraTXT = ''
   notify ("{} and receives {}{}.".format(ClickCost,uniCredit(1 - creditsReduce),extraTXT))
   me.counters['Credits'].value += 1 - creditsReduce
   debugNotify("About to autoscript other players")
   playClickCreditSound()
   autoscriptOtherPlayers('CreditClicked', Identity)

def findDMGProtection(DMGdone, DMGtype, targetPL): # Find out if the player has any card preventing damage
   debugNotify(">>> findDMGProtection() with DMGtype: {}".format(DMGtype)) #Debug
   if not Automations['Damage Prevention']: return 0
   protectionFound = 0
   protectionType = 'protection{}DMG'.format(DMGtype) # This is the string key that we use in the mdict{} dictionary
   for card in table: # First we check if we have some emergency protection cards.
      debugNotify("Checking {} for emergency protection".format(card))
      for autoS in CardsAS.get(card.model,'').split('||'):
         debugNotify("Checking autoS = {} ".format(autoS),4)
         if card.controller == targetPL and re.search(r'onDamage', autoS):
            availablePrevRegex = re.search(r'protection(Meat|Net|Brain|NetBrain|All)DMG', autoS)
            debugNotify("availablePrevRegex = {} ".format(availablePrevRegex.groups()))
            if availablePrevRegex and (re.search(r'{}'.format(DMGtype),availablePrevRegex.group(1)) or availablePrevRegex.group(1) == 'All'):
               if re.search(r'onlyOnce',autoS) and card.orientation == Rot90: continue # If the card has a once per-turn ability which has been used, ignore it
               if (re.search(r'excludeDummy',autoS) or re.search(r'CreateDummy',autoS)) and card.highlight == DummyColor: continue
               if targetPL == me:
                  if confirm("You control a {} which can prevent some of the damage you're about to suffer. Do you want to activate it now?".format(fetchProperty(card, 'name'))):
                     splitScripts = autoS.split("$$")
                     for passedScript in splitScripts: X = redirect(passedScript, card, announceText = None, notificationType = 'Quick', X = 0)
                     if re.search(r'onlyOnce',autoS): card.orientation = Rot90
               else:
                  notify(":::NOTICE::: {} is about to inflict {} Damage. {} can now use their damage prevention effects such as {}.".format(me,DMGtype,targetPL,card))
                  pingCount = 0 
                  while not confirm("{} controls a {} which can prevent some of the damage you're about to inflict to them. Please wait until they decide to use it.\
                                  \n\nHas the runner  decided whether or not to the effects of their damage prevention card?\
                                    \n(Pressing 'No' will send a ping to the runner  player to remind him to take action)".format(targetPL.name,fetchProperty(card, 'name'))):
                        pingCount += 1
                        if pingCount > 2 and confirm("You've tried to ping your opponent {} times already. Do you perhaps want to abort this script?".format(pingCount)): return 'ABORT'
                        rnd(1,1000)
                        notify(":::NOTICE::: {} is still waiting for {} to decide whether to use {} or not".format(me,targetPL,card))
   cardList = sortPriority([c for c in table
               if c.controller == targetPL
               and c.markers])
   for card in cardList: # First we check for complete damage protection (i.e. protection from all types), which is always temporary.
      if card.markers[mdict['protectionAllDMG']]:
         if card.markers[mdict['protectionAllDMG']] == 100: # If we have 100 markers of damage prevention, the card is trying to prevent all Damage.
            protectionFound += DMGdone
            DMGdone = 0
            card.markers[mdict['protectionAllDMG']] = 0
         else:
            while DMGdone > 0 and card.markers[mdict['protectionAllDMG']] > 0:
               protectionFound += 1
               DMGdone -= 1
               card.markers[mdict['protectionAllDMG']] -= 1
         for autoS in CardsAS.get(card.model,'').split('||'):
            if re.search(r'trashCost', autoS) and re.search(re.escape(protectionType), autoS) and not (re.search(r'CreateDummy', autoS) and card.highlight != DummyColor):
               if not (re.search(r'trashCost-ifEmpty', autoS) and card.markers[mdict[protectionType]] > 0):
                  debugNotify("{} has with trashCost".format(card), 3)
                  ModifyStatus('TrashMyself', targetPL.name, card, notification = 'Quick') # If the modulator -trashCost is there, the card trashes itself in order to use it's damage prevention ability
         if DMGdone == 0: break
   for card in cardList:
      if card.markers[mdict[protectionType]]:
         if card.markers[mdict[protectionType]] == 100: # If we have 100 markers of damage prevention, the card is trying to prevent all Damage.
            protectionFound += DMGdone
            DMGdone = 0
            card.markers[mdict[protectionType]] = 0
         else:
            while DMGdone > 0 and card.markers[mdict[protectionType]] > 0: # For each point of damage we do.
               protectionFound += 1 # We increase the protection found by 1
               DMGdone -= 1 # We reduce how much damage we still need to prevent by 1
               card.markers[mdict[protectionType]] -= 1 # We reduce the card's damage protection counters by 1
         debugNotify("Checking if card has a trashCost")
         for autoS in CardsAS.get(card.model,'').split('||'):
            if re.search(r'trashCost', autoS) and re.search(re.escape(protectionType), autoS) and not (re.search(r'CreateDummy', autoS) and card.highlight != DummyColor):
               debugNotify("Card has a trashcost")
               if not (re.search(r'trashCost-ifEmpty', autoS) and card.markers[mdict[protectionType]] > 0):
                  ModifyStatus('TrashMyself', targetPL.name, card, notification = 'Quick') # If the modulator -trashCost is there, the card trashes itself in order to use it's damage prevention ability
         if DMGdone == 0: break # If we've found enough protection to alleviate all damage, stop the search.
   if DMGtype == 'Net' or DMGtype == 'Brain': altprotectionType = 'protectionNetBrainDMG' # To check for the combined Net & Brain protection counter as well.
   else: altprotectionType = None
   for card in cardList: # We check for the combined protections after we use the single protectors.
      if altprotectionType and card.markers[mdict[altprotectionType]]:
         if card.markers[mdict[altprotectionType]] == 100: # If we have 100 markers of damage prevention, the card is trying to prevent all Damage.
            protectionFound += DMGdone
            DMGdone = 0
            card.markers[mdict[altprotectionType]] = 0
         else:
            while DMGdone > 0 and card.markers[mdict[altprotectionType]] > 0:
               protectionFound += 1 #
               DMGdone -= 1
               card.markers[mdict[altprotectionType]] -= 1
               
         for autoS in CardsAS.get(card.model,'').split('||'):
            if re.search(r'trashCost', autoS) and re.search(re.escape(protectionType), autoS) and not (re.search(r'CreateDummy', autoS) and card.highlight != DummyColor):
               if not (re.search(r'trashCost-ifEmpty', autoS) and card.markers[mdict[protectionType]] > 0):     
                  ModifyStatus('TrashMyself', targetPL.name, card, notification = 'Quick') # If the modulator -trashCost is there, the card trashes itself in order to use it's damage prevention ability
         if DMGdone == 0: break
   debugNotify("<<< findDMGProtection() by returning: {}".format(protectionFound), 3)
   return protectionFound

def findEnhancements(Autoscript): #Find out if the player has any cards increasing damage dealt.
   debugNotify(">>> findEnhancements(){}".format(extraASDebug())) #Debug
   enhancer = 0
   DMGtype = re.search(r'\bInflict[0-9]+(Meat|Net|Brain)Damage', Autoscript)
   if DMGtype:
      for card in table:
         if card.controller == me and card.isFaceUp:
            debugNotify("Checking {}".format(card), 2) #Debug
            Autoscripts = CardsAS.get(card.model,'').split('||')
            for autoS in Autoscripts:
               if re.search(r'-isScored', autoS) and card.controller.getGlobalVariable('ds') != 'corp': continue
               cardENH = re.search(r'Enhance([0-9]+){}Damage'.format(DMGtype.group(1)), autoS)
               if cardENH: enhancer += num(cardENH.group(1))
               enhancerMarker = 'enhanceDamage:{}'.format(DMGtype.group(1))
               debugNotify(' encancerMarker: {}'.format(enhancerMarker), 3)
               foundMarker = findMarker(card, enhancerMarker)
               if foundMarker:
                  enhancer += card.markers[foundMarker]
                  card.markers[foundMarker] = 0
   debugNotify("<<< findEnhancements() by returning: {}".format(enhancer), 3)
   return enhancer

def findVirusProtection(card, targetPL, VirusInfected): # Find out if the player has any virus preventing counters.
   debugNotify(">>> findVirusProtection(){}".format(extraASDebug())) #Debug
   protectionFound = 0
   if card.markers[mdict['protectionVirus']]:
      while VirusInfected > 0 and card.markers[mdict['protectionVirus']] > 0: # For each virus infected...
         protectionFound += 1 # We increase the protection found by 1
         VirusInfected -= 1 # We reduce how much viruses we still need to prevent by 1
         card.markers[mdict['protectionVirus']] -= 1 # We reduce the card's virus protection counters by 1
   debugNotify("<<< findVirusProtection() by returning: {}".format(protectionFound), 3)
   return protectionFound

def findCounterPrevention(count, counter, targetPL): # Find out if the player has any markers preventing them form gaining specific counters (Credits, Agenda Points etc)
   debugNotify(">>> findCounterPrevention() for {}. Return immediately <<<".format(counter)) #Debug
   return 0
   preventionFound = 0
   forfeit = None
   preventionType = 'preventCounter:{}'.format(counter)
   forfeitType = 'forfeitCounter:{}'.format(counter)
   cardList = [c for c in table
               if c.controller == targetPL
               and c.markers]
   for card in sortPriority(cardList):
      foundMarker = findMarker(card, preventionType)
      if not foundMarker: foundMarker = findMarker(card, forfeitType)
      if foundMarker: # If we found a counter prevention marker of the specific type we're looking for...
         while count > 0 and card.markers[foundMarker] > 0: # For each point of damage we do.
            preventionFound += 1 # We increase the prevention found by 1
            count -= 1 # We reduce how much counter we still need to add by 1
            card.markers[foundMarker] -= 1 # We reduce the specific counter prevention counters by 1
         if count == 0: break # If we've found enough protection to alleviate all counters, stop the search.
   debugNotify("<<< findCounterPrevention() by returning: {}".format(preventionFound), 3)
   return preventionFound
#------------------------------------------------------------------------------
# Card Actions
#------------------------------------------------------------------------------

def scrAgenda(card, x = 0, y = 0,silent = False, forced = False):
   debugNotify(">>> scrAgenda(){}".format(extraASDebug())) #Debug
   #global scoredAgendas
   mute()
   cheapAgenda = False
   storeProperties(card)
   if card.markers[mdict['Scored']] > 0:
      notify ("This agenda has already been scored")
      return
   if ds == 'runner' and card.Type != "Agenda" and not card.isFaceUp:
      card.isFaceUp = True
      random = rnd(100,1000) # Hack Workaround
      if card.Type != "Agenda":
         whisper ("You can only score Agendas")
         card.isFaceUp = False
         return
   if ds == 'runner': agendaTxt = 'LIBERATE'
   else: agendaTxt = 'SCORE'
   if fetchProperty(card, 'Type') == "Agenda":
      if ds == 'corp' and card.markers[mdict['Advancement']] < findAgendaRequirement(card) and not forced:
         if confirm("You have not advanced this agenda enough to score it. Bypass?"):
            cheapAgenda = True
            currentAdv = card.markers[mdict['Advancement']]
         else: return
      elif not silent and not confirm("Do you want to {} agenda {}?".format(agendaTxt.lower(),fetchProperty(card, 'name'))): return
      grabCardControl(card) # Taking control of the agenda for the one that scored it.
      card.isFaceUp = True
      if agendaTxt == 'SCORE' and chkTargeting(card) == 'ABORT':
         card.isFaceUp = False
         notify("{} cancels their action".format(me))
         return
      ap = num(fetchProperty(card,'Stat'))
      card.markers[mdict['Scored']] += 1
      apReduce = findCounterPrevention(ap, 'Agenda Points', me)
      if apReduce: extraTXT = " ({} forfeited)".format(apReduce)
      else: extraTXT = ''
      debugNotify("About to Score", 2)
      me.counters['Agenda Points'].value += ap - apReduce
      placeCard(card, action = 'SCORE')
      notify("{} {}s {} and receives {} agenda point(s){}".format(me, agendaTxt.lower(), card, ap - apReduce,extraTXT))
      if cheapAgenda: notify(":::Warning:::{} did not have enough advance tokens ({} out of {})! ".format(card,currentAdv,card.Cost))
      playScoreAgendaSound(card)
      executePlayScripts(card,agendaTxt)
      autoscriptOtherPlayers('Agenda'+agendaTxt.capitalize()+'d',card) # The autoscripts triggered by this effect are using AgendaLiberated and AgendaScored as the hook
      if me.counters['Agenda Points'].value >= 7 or (getSpecial('Identity',fetchCorpPL()).name == "Harmony Medtech" and me.counters['Agenda Points'].value >= 6):
         notify("{} wins the game!".format(me))
         reportGame()
      card.highlight = None # In case the card was highlighted as revealed, we remove that now.
      card.markers[mdict['Advancement']] = 0 # We only want to clear the advance counters after the automations, as they may still be used.
   else:
      whisper ("You can't score this card")

def scrTargetAgenda(group = table, x = 0, y = 0):
   cardList = [c for c in table if c.targetedBy and c.targetedBy == me]
   for card in cardList:
      storeProperties(card)
      if fetchProperty(card, 'Type') == 'Agenda':
         if card.markers[mdict['Scored']] and card.markers[mdict['Scored']] > 0: whisper(":::ERROR::: This agenda has already been scored")
         else:
            scrAgenda(card)
            return
   notify("You need to target an unscored agenda in order to use this action")

def accessTarget(group = table, x = 0, y = 0, noQuestionsAsked = False):
   debugNotify(">>> accessTarget()") #Debug
   mute()
   global origController
   targetPL = ofwhom('-ofOpponent')
   if getGlobalVariable('SuccessfulRun') != 'True' and not noQuestionsAsked:
      if not re.search(r'running',getGlobalVariable('status')) and not confirm("You're not currently running. Are you sure you're allowed to access this card?"): return
      if runSuccess() == 'DENIED': return # If the player is trying to access, then we assume the run was a success.
   cardList = [c for c in table
               if c.targetedBy
               and c.targetedBy == me
               and c.controller == targetPL
               and not c.markers[mdict['Scored']]
               and not c.markers[mdict['ScorePenalty']]
               and c.Type != 'Server'
               and c.Type != 'ICE' # To prevent mistakes
               and not (c.orientation == Rot90 and not c.isFaceUp)
               and c.Type != 'Remote Server']
   for card in cardList:
      origController[card._id] = card.controller # We store the card's original controller to know against whom to check for scripts (e.g. when accessing a rezzed encryption protocol)
      grabCardControl(card)
      cFaceD = False
      if not card.isFaceUp:
         card.isFaceUp = True
         rnd(1,100) # Bigger delay, in case the lag makes the card take too long to read.
         cFaceD = True
         card.highlight = InactiveColor
      storeProperties(card)
      Autoscripts = CardsAS.get(card.model,'').split('||')
      for autoS in Autoscripts:
         if re.search(r'onAccess:',autoS):
            debugNotify(" accessRegex found!")
            if re.search(r'-ifNotInstalled',autoS): continue # -ifNotInstalled effects don't work with the Access Card shortcut.
            notify("{} has just accessed a {}!".format(me,card.name))
            debugNotify("Doing Remote Call with player = {}. card = {}, autoS = {}".format(me,card,autoS))
            remoteCall(card.owner, 'remoteAutoscript', [card,autoS])
            if re.search(r'-pauseRunner',autoS): # If the -pauseRunner modulator exists, we need to prevent the runner form trashing or scoring cards, as the amount of advancement tokens they have will be wiped and those may be important for the ambush effect.
               passCardControl(card,card.owner) # We pass control back to the original owner in case of a trap, to allow them to manipulate their own card (e.g. Toshiyuki Sakai)
               while not confirm("Ambush! You have stumbled into a {}\
                               \n(This card activates even when inactive. You need to wait for the corporation now.)\
                             \n\nHas the corporation decided whether or not to the effects of this ambush?\
                               \n(Pressing 'No' will send a ping to the corporation player to remind him to take action)\
                                 ".format(card.name)):
                  rnd(1,1000)
                  notify(":::NOTICE::: {} is still waiting for {} to decide whether to use {} or not".format(me,card.owner,card))
      if card.group != table: whisper(":::Access Aborted::: Card has left the table!")
      else:
         grabCardControl(card) # If the card is still in the table after any trap option resolves...
         if card.Type == 'ICE':
            cStatTXT = '\nStrength: {}.'.format(card.Stat)
         elif card.Type == 'Asset' or card.Type == 'Upgrade':
            cStatTXT = '\nTrash Cost: {}.'.format(card.Stat)
         elif card.Type == 'Agenda':
            cStatTXT = '\nAgenda Points: {}.'.format(card.Stat)
         else: cStatTXT = ''
         title = "Card: {}.\
                \nType: {}.\
                \nKeywords: {}.\
                \nCost: {}.\
                  {}\n\nCard Text: {}\
              \n\nWhat do you want to do with this card?".format(fetchProperty(card, 'name'),fetchProperty(card, 'Type'),fetchProperty(card, 'Keywords'),fetchProperty(card, 'Cost'),cStatTXT,fetchProperty(card, 'Rules'))
         if card.Type == 'Agenda' or card.Type == 'Asset' or card.Type == 'Upgrade':
            if card.Type == 'Agenda': action1TXT = 'Liberate for {} Agenda Points.'.format(card.Stat)
            else:
               reduction = reduceCost(card, 'TRASH', num(card.Stat), dryRun = True)
               if reduction > 0:
                  extraText = " ({} - {})".format(card.Stat,reduction)
                  extraText2 = " (reduced by {})".format(uniCredit(reduction))
               elif reduction < 0:
                  extraText = " ({} + {})".format(card.Stat,abs(reduction))
                  extraText2 = " (increased by {})".format(uniCredit(abs(reduction)))
               else:
                  extraText = ''
                  extraText2 = '' # I only set this here, even though it's used in line 1190 later, because to reach that part, it will have to pass through this if clause always.
               action1TXT = 'Pay {}{} to Trash.'.format(num(card.Stat) - reduction,extraText)
            options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)",action1TXT]
         else:
            options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)"]
         choice = SingleChoice(title, options, 'button')
         if choice == None: choice = 0
         if choice == 1:
            sendToTrash(card)
            notify("{} {} {} at no cost".format(me,uniTrash(),card))
         elif choice == 2:
            if card.Type == 'Agenda':
               scrAgenda(card,silent = True)
            else:
               reduction = reduceCost(card, 'TRASH', num(card.Stat))
               rc = payCost(num(card.Stat) - reduction, "not free")
               if rc == "ABORT": pass # If the player couldn't pay to trash the card, we leave it where it is.
               sendToTrash(card)
               notify("{} paid {}{} to {} {}".format(me,uniCredit(num(card.Stat) - reduction),extraText2,uniTrash(),card))
         else: pass
         if cFaceD and card.group == table and not card.markers[mdict['Scored']] and not card.markers[mdict['ScorePenalty']]: card.isFaceUp = False
         card.highlight = None
         if card.group == table and not card.markers[mdict['Scored']] and not card.markers[mdict['ScorePenalty']]: 
            passCardControl(card,card.owner) # We pass control back to the corp, but only if we didn't steal the card.
            try: del origController[card._id] # We use a try: just in case...
            except: pass

def RDaccessX(group = table, x = 0, y = 0,count = None): # A function which looks at the top X cards of the corp's deck and then asks the runner what to do with each one.
   debugNotify(">>> RDaccessX()") #Debug
   mute()
   global gatheredCardList, origController
   RDtop = []
   removedCards = 0
   if ds == 'corp':
      whisper("This action is only for the use of the runner. Use the 'Look at top X cards' function on your R&D's context manu to access your own deck")
      return
   pauseRecovery = eval(getGlobalVariable('Paused Runner'))
   if pauseRecovery and pauseRecovery[0] == 'R&D':
      #confirm('{}'.format(pauseRecovery))
      barNotifyAll('#000000',"{} is resuming R&D Access".format(me))   
      skipIter = pauseRecovery[1] # This is the iter at which we'll resume from
      count = pauseRecovery[2] # The count of cards is what the previous access was, minus any removed cards (e.g.trashed ones)
   else:
      barNotifyAll('#000000',"{} is initiating R&D Access".format(me))
      if not count: count = askInteger("How many files are you able to access from the corporation's R&D?",1)
      if count == None: return
      skipIter = -1 # We only using this variable if we're resuming from a paused R&D access.
      playAccessSound('RD')
   targetPL = ofwhom('-ofOpponent')
   grabPileControl(targetPL.piles['R&D/Stack'])
   debugNotify("Found opponent. Storing the top {} as a list".format(count), 3) #Debug
   RDtop = list(targetPL.piles['R&D/Stack'].top(count))
   if len(RDtop) == 0:
      whisper("Corp's R&D is empty. You cannot take this action")
      return
   if debugVerbosity >= 4:
      for card in RDtop: notify(" Card: {}".format(card))
   notify("{} is accessing the top {} cards of {}'s R&D".format(me,count,targetPL))
   for iter in range(len(RDtop)):
      if iter <= skipIter: continue
      debugNotify("Moving card {}".format(iter), 3) #Debug
      notify(" -- {} is now accessing the {} card".format(me,numOrder(iter)))
      origController[RDtop[iter]._id] = targetPL # We store the card's original controller to know against whom to check for scripts (e.g. when accessing a rezzed encryption protocol)
      RDtop[iter].moveToBottom(me.ScriptingPile)
      storeProperties(RDtop[iter])
      debugNotify(" Looping...", 4)
      loopChk(RDtop[iter],'Type')
      Autoscripts = CardsAS.get(RDtop[iter].model,'').split('||')
      debugNotify("Grabbed AutoScripts", 4)
      for autoS in Autoscripts:
         if re.search(r'onAccess:',autoS):
            if re.search(r'-ifInstalled',autoS): continue # -ifInstalled cards work only while on the table.
            if re.search(r'-ifNotAccessedInRD',autoS): continue # -ifNotInRD cards work only while not accessed from R&D.
            debugNotify(" accessRegex found!")
            notify("{} has just accessed {}!".format(me,RDtop[iter].name))
            remoteCall(RDtop[iter].owner, 'remoteAutoscript', [RDtop[iter],autoS])
            if re.search(r'-pauseRunner',autoS): 
               notify(":::WARNING::: {} has stumbled onto {}. Once the effects of this card are complete, they need to press Ctrl+A to continue their access from where they left it.\nThey have seen {} out of {} cards until now.".format(me,RDtop[iter].name,iter + 1, count))
               RDtop[iter].moveTo(targetPL.piles['R&D/Stack'],iter - removedCards)
               passPileControl(targetPL.piles['R&D/Stack'],targetPL)
               gatheredCardList = False  # We set this variable to False, so that reduceCost() calls from other functions can start scanning the table again.
               setGlobalVariable('Paused Runner',str(['R&D',iter - removedCards,count - removedCards]))
               return
      debugNotify(" Storing...", 4)
      cType = RDtop[iter].Type
      cKeywords = RDtop[iter].Keywords
      cStat = RDtop[iter].Stat
      cCost = RDtop[iter].Cost
      cName = RDtop[iter].name
      cRules = RDtop[iter].Rules
      debugNotify("Stored properties. Checking type...", 3) #Debug
      if cType == 'ICE':
         cStatTXT = '\nStrength: {}.'.format(cStat)
      elif cType == 'Asset' or cType == 'Upgrade':
         cStatTXT = '\nTrash Cost: {}.'.format(cStat)
      elif cType == 'Agenda':
         cStatTXT = '\nAgenda Points: {}.'.format(cStat)
      else: cStatTXT = ''
      title = "Card: {}.\
             \nType: {}.\
             \nKeywords: {}.\
             \nCost: {}.\
               {}\n\nCard Text: {}\
           \n\nWhat do you want to do with this card?".format(cName,cType,cKeywords,cCost,cStatTXT,cRules)
      if cType == 'Agenda' or cType == 'Asset' or cType == 'Upgrade':
         if cType == 'Agenda': action1TXT = 'Liberate for {} Agenda Points.'.format(cStat)
         else:
            reduction = reduceCost(RDtop[iter], 'TRASH', num(cStat), dryRun = True)
            gatheredCardList = True # We set this variable to True, to tell future reducecosts in this execution, not to scan the table a second time.
            if reduction > 0:
               extraText = " ({} - {})".format(cStat,reduction)
               extraText2 = " (reduced by {})".format(uniCredit(reduction))
            elif reduction < 0:
               extraText = " ({} + {})".format(cStat,abs(reduction))
               extraText2 = " (increased by {})".format(uniCredit(reduction))
            else:
               extraText = ''
               extraText2 = ''
            action1TXT = 'Pay {}{} to Trash.'.format(num(cStat) - reduction,extraText)
         options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)",action1TXT]
      else:
         options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)"]
      choice = SingleChoice(title, options, 'button')
      if choice == None: choice = 0
      if choice == 1:
         sendToTrash(RDtop[iter])
         loopChk(RDtop[iter],'Type')
         notify("{} {} {} at no cost".format(me,uniTrash(),RDtop[iter]))
         removedCards += 1
      elif choice == 2:
         if cType == 'Agenda':
            RDtop[iter].moveToTable(0,0)
            RDtop[iter].highlight = RevealedColor
            scrAgenda(RDtop[iter],silent = True)
            removedCards += 1
         else:
            reduction = reduceCost(RDtop[iter], 'TRASH', num(cStat))
            rc = payCost(num(cStat) - reduction, "not free")
            if rc == "ABORT": continue # If the player couldn't pay to trash the card, we leave it where it is.
            sendToTrash(RDtop[iter])
            loopChk(RDtop[iter],'Type')
            notify("{} paid {}{} to {} {}".format(me,uniCredit(num(cStat) - reduction),extraText2,uniTrash(),RDtop[iter]))
            removedCards += 1
      else: 
         debugNotify("Selected doing nothing. About to move back...", 4)
         RDtop[iter].moveTo(targetPL.piles['R&D/Stack'],iter - removedCards)
      try: del origController[RDtop[iter]._id] # We use a try: just in case...
      except: pass         
   notify("{} has finished accessing {}'s R&D".format(me,targetPL))
   passPileControl(targetPL.piles['R&D/Stack'],targetPL)
   gatheredCardList = False  # We set this variable to False, so that reduceCost() calls from other functions can start scanning the table again.
   setGlobalVariable('Paused Runner','False')
   debugNotify("<<< RDaccessX()", 3)
   
def ARCscore(group=table, x=0,y=0):
   mute()
   global origController
   debugNotify(">>> ARCscore(){}".format(extraASDebug())) #Debug
   removedCards = 0
   ARCHcards = []
   if ds == 'corp':
      whisper("This action is only for the use of the runner.")
      return
   targetPL = ofwhom('-ofOpponent')
   debugNotify("Found opponent.", 3) #Debug
   ARC = targetPL.piles['Heap/Archives(Face-up)']
   grabPileControl(ARC)
   grabPileControl(targetPL.piles['Archives(Hidden)'])
   for card in targetPL.piles['Archives(Hidden)']: card.moveTo(ARC) # When the runner accesses the archives, all  cards of the face up archives.
   passPileControl(targetPL.piles['Archives(Hidden)'],targetPL)
   if len(ARC) == 0:
      whisper("Corp's Archives are empty. You cannot take this action")
      return
   playAccessSound('Archives')
   rnd(10,100) # A small pause
   agendaFound = False
   for card in ARC:
      debugNotify("Checking: {}.".format(card), 3) #Debug
      origController[card._id] = targetPL # We store the card's original controller to know against whom to check for scripts (e.g. when accessing a rezzed encryption protocol)
      if card.Type == 'Agenda' and not re.search(r'-disableAutoStealingInArchives',CardsAS.get(card.model,'')): 
         agendaFound = True
         card.moveToTable(0,0)
         card.highlight = RevealedColor
         scrAgenda(card) # We don't want it silent, as it needs to ask the runner to score, in case of agendas like Fetal AI for which they have to pay as well.
         if card.highlight == RevealedColor: card.moveTo(ARC) # If the runner opted not to score the agenda, put it back into the deck.
      Autoscripts = CardsAS.get(card.model,'').split('||')
      debugNotify("Grabbed AutoScripts", 4)
      for autoS in Autoscripts:
         if chkModulator(card, 'worksInArchives', 'onAccess'):
            debugNotify("-worksInArchives accessRegex found!")
            notify("{} has just accessed a {}!".format(me,card.name))
            remoteCall(card.owner, 'remoteAutoscript', [card,autoS])
      try: del origController[card._id] # We use a try: just in case...
      except: pass
   if not agendaFound: notify("{} has rumaged through {}'s archives but found no Agendas".format(Identity,targetPL))
   passPileControl(ARC,targetPL)
   debugNotify("<<< ARCscore()")

def HQaccess(group=table, x=0,y=0, silent = False):
   mute()
   global origController
   debugNotify(">>> HQAccess(){}".format(extraASDebug())) #Debug
   if ds == 'corp':
      whisper("This action is only for the use of the runner.")
      return
   targetPL = ofwhom('-ofOpponent')
   debugNotify("Found opponent.", 3) #Debug
   grabPileControl(targetPL.hand)
   revealedCards = [c for c in table if c.highlight == RevealedColor]
   if len(revealedCards): # Checking if we're continuing from a Paused HQ Access.
      barNotifyAll('#000000',"{} is resuming their HQ Access".format(me))      
   elif getGlobalVariable('Paused Runner') != 'False':
      # If the pause variable is still active, it means the last access was paused by there were no other cards to resume, so we just clear the variable.
      setGlobalVariable('Paused Runner','False')
      return
   else:
      if not silent and not confirm("You are about to access a random card from the corp's HQ.\
                                   \nPlease make sure your opponent is not manipulating their hand, and does not have a way to cancel this effect before continuing\
                                 \n\nProceed?"): return
      barNotifyAll('#000000',"{} is initiating HQ Access".format(me))
      count = askInteger("How many files are you able to access from the corporation's HQ?",1)
      if count == None: return
      playAccessSound('HQ')
      revealedCards = showatrandom(count = count, targetPL = targetPL, covered = True)
   for revealedCard in revealedCards:
      loopChk(revealedCard)
      origController[revealedCard._id] = targetPL # We store the card's original controller to know against whom to check for scripts (e.g. when accessing a rezzed encryption protocol)
      #storeProperties(revealedCard) # So as not to crash reduceCost() later
      revealedCard.sendToFront() # We send our currently accessed card to the front, so that the corp can see it. The rest are covered up.
      accessRegex = re.search(r'onAccess:([^|]+)',CardsAS.get(revealedCard.model,''))
      if accessRegex:
         debugNotify(" accessRegex found! {}".format(accessRegex.group(1)), 2)
         notify("{} has just accessed a {}!".format(me,revealedCard))
      Autoscripts = CardsAS.get(revealedCard.model,'').split('||')
      for autoS in Autoscripts:
         if re.search(r'onAccess:',autoS):
            if re.search(r'-ifInstalled',autoS): continue # -ifInstalled cards work only while on the table.
            debugNotify(" accessRegex found!")
            notify("{} has just accessed a {}!".format(me,revealedCard.name))
            remoteCall(revealedCard.owner, 'remoteAutoscript', [revealedCard,autoS])
            if re.search(r'-pauseRunner',autoS): 
               notify(":::WARNING::: {} has stumbled onto {}. Once the effects of this card are complete, they need to press Ctrl+Q to continue their access from where they left it.".format(me,revealedCard.name))
               revealedCard.moveTo(targetPL.hand) # We return it to the player's hand because the effect will decide where it goes afterwards
               if not len([c for c in table if c.highlight == RevealedColor]): clearCovers() # If we have no leftover cards to access after a
               passPileControl(targetPL.hand,targetPL)
               setGlobalVariable('Paused Runner',str(['HQ']))
               return
      debugNotify("Not a Trap.", 2) #Debug
      if revealedCard.Type == 'ICE':
         cStatTXT = '\nStrength: {}.'.format(revealedCard.Stat)
      elif revealedCard.Type == 'Asset' or revealedCard.Type == 'Upgrade':
         cStatTXT = '\nTrash Cost: {}.'.format(revealedCard.Stat)
      elif revealedCard.Type == 'Agenda':
         cStatTXT = '\nAgenda Points: {}.'.format(revealedCard.Stat)
      else: cStatTXT = ''
      debugNotify("Crafting Title", 2) #Debug
      title = "Card: {}.\
             \nType: {}.\
             \nKeywords: {}.\
             \nCost: {}.\
               {}\n\nCard Text: {}\
           \n\nWhat do you want to do with this card?".format(revealedCard.Name,revealedCard.Type,revealedCard.Keywords,revealedCard.Cost,cStatTXT,revealedCard.Rules)
      if revealedCard.Type == 'Agenda' or revealedCard.Type == 'Asset' or revealedCard.Type == 'Upgrade':
         if revealedCard.Type == 'Agenda': action1TXT = 'Liberate for {} Agenda Points.'.format(revealedCard.Stat)
         else:
            reduction = reduceCost(revealedCard, 'TRASH', num(revealedCard.Stat), dryRun = True)
            if reduction > 0:
               extraText = " ({} - {})".format(revealedCard.Stat,reduction)
               extraText2 = " (reduced by {})".format(uniCredit(reduction))
            elif reduction < 0:
               extraText = " ({} + {})".format(revealedCard.Stat,abs(reduction))
               extraText2 = " (increased by {})".format(uniCredit(abs(reduction)))
            else:
               extraText = ''
               extraText2 = ''
            action1TXT = 'Pay {}{} to Trash.'.format(num(revealedCard.Stat) - reduction,extraText)
         options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)",action1TXT]
      else:
         options = ["Leave where it is.","Force trash at no cost.\n(Only through card effects)"]
      debugNotify("Opening Choice Window", 2) #Debug
      choice = SingleChoice(title, options, 'button')
      if choice == None: choice = 0
      if choice == 1:
         sendToTrash(revealedCard)
         loopChk(revealedCard,'Type')
         notify("{} {} {} at no cost".format(me,uniTrash(),revealedCard))
      elif choice == 2:
         if revealedCard.Type == 'Agenda':
            scrAgenda(revealedCard,silent = True)
         else:
            reduction = reduceCost(revealedCard, 'TRASH', num(revealedCard.Stat))
            rc = payCost(num(revealedCard.Stat) - reduction, "not free")
            if rc == "ABORT": revealedCard.moveTo(targetPL.hand) # If the player couldn't pay to trash the card, we leave it where it is.
            sendToTrash(revealedCard)
            loopChk(revealedCard,'Type')
            notify("{} paid {}{} to {} {}".format(me,uniCredit(num(revealedCard.Stat) - reduction),extraText2,uniTrash(),revealedCard))
      else: revealedCard.moveTo(targetPL.hand)
      try: del origController[revealedCard._id] # We use a try: just in case...
      except: pass
   rnd(1,10) # a little pause
   for c in revealedCards: c.highlight = None # We make sure no card remains highlighted for some reason.
   passPileControl(targetPL.hand,targetPL)
   setGlobalVariable('Paused Runner','False')
   clearCovers() # Finally we clear any remaining cover cards.
   debugNotify("<<< HQAccess()", 3)
   
def isRezzable (card):
   debugNotify(">>> isRezzable(){}".format(extraASDebug())) #Debug
   mute()
   Type = fetchProperty(card, 'Type')
   if Type == "ICE" or Type == "Asset" or Type == "Upgrade" or Type == "Agenda": return True
   else: return False

def intRez (card, x=0, y=0, cost = 'not free', silent = False, silentCost = False, preReduction = 0):
   debugNotify(">>> intRez(){}".format(extraASDebug())) #Debug
   mute()
   rc = ''
   storeProperties(card)
   if card.isFaceUp:
      whisper("you can't rez a rezzed card")
      return 'ABORT'
   if not isRezzable(card):
      whisper("Not a rezzable card")
      return 'ABORT'
   if not checkUnique(card): return 'ABORT' #If the player has the unique card rezzed and opted not to trash it, do nothing.
   if chkTargeting(card) == 'ABORT':
      notify("{} cancels their action".format(me))
      return 'ABORT'
   if cost != 'free': reduction = reduceCost(card, 'REZ', num(fetchProperty(card, 'Cost'))) + preReduction
   else: reduction = preReduction
   if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))
   elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
   else: extraText = ''
   increase = findExtraCosts(card, 'REZ')
   rc = payCost(num(fetchProperty(card, 'Cost')) - reduction + increase, cost, silentCost = silentCost)
   if rc == "ABORT": return 'ABORT' # If the player didn't have enough money to pay and aborted the function, then do nothing.
   elif rc == "free": extraText = " at no cost"
   elif rc != 0: rc = "for {}".format(rc)
   else: rc = ''
   card.isFaceUp = True
   if not silent:
      if card.Type == 'ICE': notify("{} has rezzed {} {}{}.".format(me, card, rc, extraText))
      if card.Type == 'Asset': notify("{} has acquired {} {}{}.".format(me, card, rc, extraText))
      if card.Type == 'Upgrade': notify("{} has installed {} {}{}.".format(me, card, rc, extraText))
   playRezSound(card)
   update() # Bug workaround.
   executePlayScripts(card,'REZ')
   autoscriptOtherPlayers('CardRezzed',card)

def rezForFree(card, x = 0, y = 0):
   debugNotify(">>> rezForFree(){}".format(extraASDebug())) #Debug
   intRez(card, cost = 'free')

def flagAutoRez(card, x = 0, y = 0):
   global autoRezFlags
   storeProperties(card)
   if card.isFaceUp:
      whisper("you can't rez a rezzed card")
      return 'ABORT'
   if not isRezzable(card):
      whisper("Not a rezzable card")
      return 'ABORT'
   if card._id in autoRezFlags:
      autoRezFlags.remove(card._id)
      whisper("--- {} will not attempt to rez at the start of your turn".format(fetchProperty(card, 'Name')))
   else:
      autoRezFlags.append(card._id)
      whisper("--- {} has been flagged to automatically rez at the start of your turn".format(fetchProperty(card, 'Name')))

def derez(card, x = 0, y = 0, silent = False):
   debugNotify(">>> derez(){}".format(extraASDebug())) #Debug
   mute()
   storeProperties(card)
   if card.isFaceUp:
      if not isRezzable(card):
         whisper ("Not a rezzable card")
         return 'ABORT'
      else:
         if not silent: notify("{} derezzed {}".format(me, card))
         card.markers[mdict['Credits']] = 0
         playDerezSound(card)
         executePlayScripts(card,'DEREZ')
         autoscriptOtherPlayers('CardDerezzed',card)
         card.isFaceUp = False
         if card.owner == me:
            if debugVerbosity >= 0 and not confirm("Peek at card?"): return
            card.peek()
   else:
      notify ( "you can't derez a unrezzed card")
      return 'ABORT'

def expose(card, x = 0, y = 0, silent = False):
   debugNotify(">>> expose(){}".format(extraASDebug())) #Debug
   if not card.isFaceUp:
      mute()
      if card.controller != me: notify("{} attempts to expose target card.".format(me)) # When the opponent exposes, we don't actually go through with it, to avoid mistakes.
      else:
         card.isFaceUp = True
         if card.highlight == None: card.highlight = RevealedColor # we don't want to accidentally wipe dummy card highlight.
         if not silent: notify("{} exposed {}".format(me, card))
   else:
      card.isFaceUp = False
      debugNotify("Peeking() at expose()")
      card.peek()
      if card.highlight == RevealedColor: card.highlight = None
      if not silent: notify("{} hides {} once more again".format(me, card))

def rolld6(group = table, x = 0, y = 0, silent = False):
   debugNotify(">>> rolld6(){}".format(extraASDebug())) #Debug
   mute()
   n = rnd(1, 6)
   if not silent: notify("{} rolls {} on a 6-sided die.".format(me, n))
   return n

def selectAsTarget (card, x = 0, y = 0):
   debugNotify(">>> selectAsTarget(){}".format(extraASDebug())) #Debug
   card.target(True)

def clear(card, x = 0, y = 0, silent = False):
   debugNotify(">>> clear() card: {}".format(card), ) #Debug
   mute()
   if not silent: notify("{} clears {}.".format(me, card))
   if card.highlight != DummyColor and card.highlight != RevealedColor and card.highlight != NewCardColor and card.highlight != InactiveColor and card.highlight != StealthColor and card.highlight != PriorityColor: 
      debugNotify("Clearing {} Highlight for {}".format(card.highlight,card))
      card.highlight = None
   card.markers[mdict['BaseLink']] = 0
   card.markers[mdict['PlusOne']] = 0
   card.markers[mdict['MinusOne']] = 0
   card.target(False)
   debugNotify("<<< clear()", 3)

def clearAll(markersOnly = False, allPlayers = False): # Just clears all the player's cards.
   debugNotify(">>> clearAll()") #Debug
   if allPlayers: 
      for player in getPlayers():
         if player != me: remoteCall(player,'clearAll',[markersOnly, False])
   for card in table:
      if card.controller == me: 
         if card.name == 'Trace': card.highlight = None # We clear the card in case a tracing is pending that was not done.
         clear(card,silent = True)
         if card.owner == me and card.Type == 'Identity' and Stored_Type.get(card._id,'NULL') == 'NULL':
            delayed_whisper(":::DEBUG::: Identity was NULL. Re-storing as an attempt to fix")
            storeProperties(card, True)
   if not markersOnly: clearLeftoverEvents()
   debugNotify("<<< clearAll()", 3)

def clearAllNewCards(remoted = False): # Clears all highlights from new cards.
   debugNotify(">>> clearAllNewCards(){}".format(extraASDebug())) #Debug
   if not remoted:
      for player in getPlayers():
         if player != me: remoteCall(player,'clearAllNewCards',[True])
   for card in table:
      if card.highlight == NewCardColor and card.controller == me: 
         debugNotify("Clearing New card {}".format(card))
         card.highlight = None  
   debugNotify(">>> clearAllNewCards(){}".format(extraASDebug())) #Debug
   
def intTrashCard(card, stat, cost = "not free",  ClickCost = '', silent = False):
   debugNotify(">>> intTrashCard(){}".format(extraASDebug())) #Debug
   global trashEasterEggIDX
   mute()
   MUtext = ""
   rc = ''
   storeProperties(card)
   if card.group.name == 'Heap/Archives(Face-up)' or card.group.name == 'Archives(Hidden)': # If the card is already trashed (say from a previous script), we don't want to try and trash it again
      return # We don't return abort, otherwise scripts will stop executing (e.g. see using Fairy to break two subroutines)
   if card.markers[mdict['Scored']] or card.markers[mdict['ScorePenalty']]: 
      exileCard(card) # If the card is scored, then card effects don't trash it, but rather remove it from play (Otherwise the runner could score it again)
      return
   if ClickCost == '':
      ClickCost = '{} '.format(me) # If not clicks were used, then just announce our name.
      goodGrammar = 'es' # LOL Grammar Nazi
   else:
      ClickCost += ' and '
      goodGrammar = ''
   if UniCode: goodGrammar = ''
   cardowner = card.owner
   if fetchProperty(card, 'Type') == "Tracing" or fetchProperty(card, 'Type') == "Counter Hold" or (fetchProperty(card, 'Type') == "Server" and fetchProperty(card, 'name') != "Remote Server"):
      whisper("{}".format(trashEasterEgg[trashEasterEggIDX]))
      if trashEasterEggIDX < 7:
         trashEasterEggIDX += 1
         return 'ABORT'
      elif trashEasterEggIDX == 7:
         card.moveToBottom(cardowner.piles['Heap/Archives(Face-up)'])
         trashEasterEggIDX = 0
         return 'ABORT'
   if card.highlight == DummyColor and getSetting('DummyTrashWarn',True) and not silent and not confirm(":::Warning!:::\n\nYou are about to trash a dummy card. You will not be able to restore it without using the effect that created it originally.\n\nAre you sure you want to proceed? (This message will not appear again)"):
      setSetting('DummyTrashWarn',False)
      return
   else: setSetting('DummyTrashWarn',False)
   if cost != 'free': reduction = reduceCost(card, 'TRASH', num(stat)) # So as not to waste time.
   else: reduction = 0
   if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))
   elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
   else: extraText = ''
   rc = payCost(num(stat) - reduction, cost)
   if rc == "ABORT": return 'ABORT' # If the player didn't have enough money to pay and aborted the function, then do nothing.
   elif rc == 0:
      if ClickCost.endswith(' and'): ClickCost[:-len(' and')] # if we have no click cost, we don't need the connection.
   else:
      ClickCost += "pays {} to".format(rc) # If we have Credit cost, append it to the Click cost to be announced.
      goodGrammar = ''
   if fetchProperty(card, 'Type') == 'Event' or fetchProperty(card, 'Type') == 'Operation': silent = True # These cards are already announced when played. No need to mention them a second time.
   if card.isFaceUp:
      MUtext = chkRAM(card, 'UNINSTALL')
      if rc == "free" and not silent:
         debugNotify("About to trash card for free. Cost = {}".format(cost), 2)
         if cost == "host removed": notify("{} {} {} because its host has been removed from play{}.".format(card.owner, uniTrash(), card, MUtext))
         else: notify("{} {} {} at no cost{}.".format(me, uniTrash(), card, MUtext))
      elif not silent: notify("{} {}{} {}{}{}.".format(ClickCost, uniTrash(), goodGrammar, card, extraText, MUtext))
      sendToTrash(card)
   elif (ds == "runner" and card.controller == me) or (ds == "runner" and card.controller != me and cost == "not free") or (ds == "corp" and card.controller != me ):
   #I'm the runner and I trash my cards, or an accessed card from the corp, or I 'm the corp and I trash a runner's card, then the card will go to the open archives
      sendToTrash(card)
      if rc == "free" and not silent:
         if card.highlight == DummyColor: notify ("{} clears {}'s lingering effects.".format(me, card)) # In case the card is a dummy card, we change the notification slightly.
         else: notify ("{} {} {}{} at no cost.".format(me, uniTrash(), card, extraText))
      elif not silent: notify("{} {}{} {}{}.".format(ClickCost, uniTrash() , goodGrammar, card, extraText))
   else: #I'm the corp and I trash my own hidden cards or the runner and trash a hidden corp card without cost (e.g. randomly picking one from their hand)
      sendToTrash(card, cardowner.piles['Archives(Hidden)'])
      if rc == "free" and not silent: notify("{} {} a hidden card at no cost.".format(me, uniTrash()))
      elif not silent: notify("{} {}{} a hidden card.".format(ClickCost, uniTrash(), goodGrammar))
   debugNotify("<<< intTrashCard()", 3)

def trashCard (card, x = 0, y = 0):
   debugNotify(">>> trashCard(){}".format(extraASDebug())) #Debug
   if card.highlight == DummyColor: intTrashCard(card, card.Stat, "free") # lingering effects don't require cost to trash.
   else: intTrashCard(card, card.Stat)

def trashForFree (card, x = 0, y = 0):
   debugNotify(">>> trashForFree(){}".format(extraASDebug())) #Debug
   intTrashCard(card, card.Stat, "free")

def pay2AndTrash(card, x=0, y=0):
   debugNotify(">>> pay2AndTrash(){}".format(extraASDebug())) #Debug
   ClickCost = useClick()
   if ClickCost == 'ABORT': return
   intTrashCard(card, 2, ClickCost = ClickCost)

def trashTargetFree(group, x=0, y=0):
   debugNotify(">>> trashTargetFree(){}".format(extraASDebug())) #Debug
   targetCards = [c for c in table
                 if c.targetedBy
                 and c.targetedBy == me]
   if len(targetCards) == 0: return
   for card in targetCards:
      storeProperties(card)
      intTrashCard(card, fetchProperty(card, 'Stat'), "free")

def trashTargetPaid(group, x=0, y=0):
   debugNotify(">>> trashTargetFree(){}".format(extraASDebug())) #Debug
   targetCards = [c for c in table
                 if c.targetedBy
                 and c.targetedBy == me]
   if len(targetCards) == 0: return
### I think the below is not necessary from experience ###
#   if not confirm("You are about to trash your opponent's cards. This may cause issue if your opponent is currently manipulating them\
#             \nPlease ask your opponent to wait until the notification appears before doing anything else\
#           \n\nProceed?"): return
   for card in targetCards:
      storeProperties(card)
      cardType = fetchProperty(card, 'Type')
      if ds == 'corp':
         if cardType != 'Resource' and not confirm("Only resources can be trashed from the runner.\n\nBypass Restriction?"): continue
         if not card.controller.Tags and not confirm("You can only Trash the runner's resources when they're tagged\n\nBypass Restriction?"): continue
         ClickCost = useClick()
         if ClickCost == 'ABORT': return
         intTrashCard(card, 2, ClickCost = ClickCost)
      else:
         if cardType != 'Upgrade' and cardType != 'Asset' and not confirm("You can normally only pay to trash the Corp's Nodes and Upgrades.\n\nBypass Restriction?"): continue
         intTrashCard(card, fetchProperty(card, 'Stat')) # If we're a runner, trash with the cost of the card's trash.

def exileCard(card, silent = False):
   debugNotify(">>> exileCard(){}".format(extraASDebug())) #Debug
   # Puts the removed card in the shared pile and outside of view.
   mute()
   storeProperties(card)
   if fetchProperty(card, 'Type') == "Tracing" or fetchProperty(card, 'Type') == "Counter Hold" or fetchProperty(card, 'Type') == "Server":
      whisper("This kind of card cannot be exiled!")
      return 'ABORT'
   else:
      if card.isFaceUp: MUtext = chkRAM(card, 'UNINSTALL')
      else: MUtext = ''
      if card.markers[mdict['Scored']]:
         if card.Type == 'Agenda': APloss = num(card.Stat)
         else: APloss = card.markers[mdict['Scored']] # If we're trashing a card that's not an agenda but nevertheless counts as one, the amount of scored counters are the AP it provides.
         me.counters['Agenda Points'].value -= APloss # Trashing Agendas for any reason, now takes they value away as well.
         notify("--> {} loses {} Agenda Points".format(me, APloss))
      if card.markers[mdict['ScorePenalty']]: # A card with Score Penalty counters was giving us minus agenda points. By exiling it, we recover those points.
         if card.Type == 'Agenda': APgain = num(card.Stat)
         else: APgain = card.markers[mdict['ScorePenalty']]
         me.counters['Agenda Points'].value += APgain 
         notify("--> {} recovers {} Agenda Points".format(me, APgain))
         if me.counters['Agenda Points'].value >= 7 or (getSpecial('Identity',fetchCorpPL()).name == "Harmony Medtech" and me.counters['Agenda Points'].value >= 6):
            notify("{} wins the game!".format(me))
            reportGame() # If we removed agenda points penalty (e.g. Data Dealer a Shi.Kyu) and that made us reach 7 agenda points, we can win the game at this point.
      executePlayScripts(card,'TRASH') # We don't want to run automations on simply revealed cards.
      clearAttachLinks(card)
      changeCardGroup(card,card.owner.piles['Removed from Game'])
   if not silent: notify("{} exiled {}{}.".format(me,card,MUtext))

def uninstall(card, x=0, y=0, destination = 'hand', silent = False):
   debugNotify(">>> uninstall(){}".format(extraASDebug())) #Debug
   # Returns an installed card into our hand.
   mute()
   storeProperties(card)
   if destination == 'R&D' or destination == 'Stack': group = card.owner.piles['R&D/Stack']
   else: group = card.owner.hand
   #confirm("destination: {}".format(destination)) # Debug
   if fetchProperty(card, 'Type') == "Tracing" or fetchProperty(card, 'Type') == "Counter Hold" or (fetchProperty(card, 'Type') == "Server" and fetchProperty(card, 'name') != "Remote Server"):
      whisper("This kind of card cannot be uninstalled!")
      return 'ABORT'
   else:
      if card.isFaceUp: MUtext = chkRAM(card, 'UNINSTALL')
      else: MUtext = ''
      executePlayScripts(card,'UNINSTALL')
      autoscriptOtherPlayers('CardUninstalled',card)
      clearAttachLinks(card)
      card.moveTo(group)
   if not silent: notify("{} uninstalled {}{}.".format(me,card,MUtext))

def useCard(card,x=0,y=0):
   debugNotify(">>> useCard(){}".format(extraASDebug())) #Debug
   if card.highlight == None or card.highlight == NewCardColor:
      card.highlight = SelectColor
      notify ( "{} uses the ability of {}.".format(me,card) )
   else:
      if card.highlight == DummyColor:
         whisper(":::WARNING::: This highlight signifies that this card is a lingering effect left behind from the original\
                \nYou cannot clear such cards, please use the trash action to remove them.")
         return
      notify("{} clears {}.".format(me, card))
      card.highlight = None
      card.target(False)

def prioritize(card,x=0,y=0):
   debugNotify(">>> prioritize(){}".format(extraASDebug())) #Debug
   if card.highlight == None:
      card.highlight = PriorityColor
      notify ("{} prioritizes {} for using counters automatically.".format(me,card))
      if getSetting('PriorityInform',True):
         information("This action prioritizes a card for when selecting which card will use its counters from automated effects\
                    \nSuch automated effects include losing counters from stealth cards for using noisy icebreakers, or preventing damage\
                  \n\nSelecting a card for priority gives it first order in the pick. So it will use its counters before any other card will\
                  \n\nThe second order of priority is targeting a card. A card that is targeted at the time of the effect, will lose its counters after all cards highlighted with priority have\
                  \n\nFinally, if any part of the effect is left requiring the use of counters, any card without priority or targeted will be used.\
                  \n\nKeep this in mind if you wish to fine tune which cards use their counter automatically first\
                    \n(This message will not appear again)")
         setSetting('PriorityInform',False)
   else:
      if card.highlight == DummyColor:
         information(":::ERROR::: This highlight signifies that this card is a lingering effect left behind from the original\
                \nYou cannot prioritize such cards as they would lose their highlight and thus create problems with automation.\
                \nIf you want one such card to use counter before others, simply target (shift+click) it for the duration of the effect.")
         return
      notify("{} clears {}'s priority.".format(me, card))
      card.highlight = None
      card.target(False)

def stealthReserve(card,x=0,y=0):
   debugNotify(">>> prioritize(){}".format(extraASDebug())) #Debug
   if card.highlight == None:
      card.highlight = StealthColor
      notify ("{} reserves credits on {} for stealth cards.".format(me,card))
   else:
      if card.highlight == DummyColor:
         information(":::ERROR::: This highlight signifies that this card is a lingering effect left behind from the original\
                \nYou cannot reserve such cards for stealth as they would lose their highlight and thus create problems with automation.\
                \nIf you want one such card to use counter before others, simply target (shift+click) it for the duration of the effect.")
         return
      notify("{} clears {}'s stealth reservation.".format(me, card))
      card.highlight = None
      card.target(False)
      
def rulings(card, x = 0, y = 0):
   debugNotify(">>> rulings(){}".format(extraASDebug())) #Debug
   mute()
   #if not card.isFaceUp: return
   #openUrl('http://www.netrunneronline.com/cards/{}/'.format(card.Errata))
   if card.Subtitle != '': subTXT = ':' + card.Subtitle
   else: subTXT = ''
   openUrl('http://netrunnercards.info/find/?q={}{}&mode=embed'.format(fetchProperty(card, 'name'),subTXT)) # Errata is not filled in most card so this works better until then

def inspectCard(card, x = 0, y = 0): # This function shows the player the card text, to allow for easy reading until High Quality scans are procured.
   debugNotify(">>> inspectCard(){}".format(extraASDebug())) #Debug
   ASText = "This card has the following automations:"
   if re.search(r'onPlay', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will have an effect when coming into play from your hand.'
   if re.search(r'onScore', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will have an effect when being scored.'
   if re.search(r'onRez', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will have an effect when its being rezzed.'
   if re.search(r'onInstall', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will have an effect when its being installed.'
   if re.search(r'whileRezzed', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will has a continous effect while in play.'
   if re.search(r'whileScored', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will has a continous effect while scored.'
   if re.search(r'whileRunning', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will has a continous effect while running.'
   if re.search(r'atTurnStart', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will perform an automation at the start of your turn.'
   if re.search(r'atTurnEnd', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will perform an automation at the end of your turn.'
   if re.search(r'atRunStart', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will perform an automation at the start of your run.'
   if re.search(r'atJackOut', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will perform an automation at the end of a run.'
   if re.search(r'onAccess', Stored_AutoScripts.get(card._id,'')): ASText += '\n * It will perform an automation when the runner accesses it.'
   if CardsAA.get(card.model,'') != '' or Stored_AutoActions.get(card._id,'') != '':
      debugNotify("We have AutoActions", 2) #Debug
      if ASText == 'This card has the following automations:': ASText = '\nThis card will perform one or more automated actions when you double click on it.'
      else: ASText += '\n\nThis card will also perform one or more automated actions when you double click on it.'
   if ASText == 'This card has the following automations:': ASText = '\nThis card has no automations.'
   #if fetchProperty(card, 'name') in automatedMarkers:
   #   ASText += '\n\nThis card can create markers, which also have automated effects.'
   if card.type == 'Tracing': information("This is your tracing card. Double click on it to reinforce your trace or base link.\
                                         \nIt will ask you for your bid and then take the same amount of credits from your bank automatically")
   elif card.type == 'Server': information("These are your Servers. Start stacking your Ice above them and your Agendas, Upgrades and Nodes below them.\
                                     \nThey have no automated abilities so remember to manually pay credits for every ICE you install after the first!")
   elif card.type == 'Counter Hold': information("This is your Counter Hold. This card stores all the beneficial and harmful counters you might accumulate over the course of the game.\
                                          \n\nIf you're playing a corp, Bad Publicity, viruses and other such tokens may be put here as well. By double clicking this card, you'll use three clicks to clean all viruses from your cards.\
                                          \nIf you're playing a runner, brain damage markers, tags and any other tokens the corp gives you will be put here. by double clicking this card, you'll be able to select one of the markers to remove by paying its cost.\
                                        \n\nTo remove any token manually, simply drag & drop it out of this card.")
   elif card.type == 'Button': information("This is a button to help you quickly shout announcements to your opponent.\
                                          \nTo use a card button just double click on it.\
                                        \n\nThe Various buttons are: \
                                        \n\n* 'Access Imminent': Use this before you press F3 for a successful run, if you want to give the corporation an opportunity to rez upgrades/assets or use paid abilities\
                                        \n\n* 'No Rez': Use this as a corp to inform the runner you're not rezzing the currently approached ICE.\
                                        \n\n* 'Wait': Use this if you want to stop the opponent while you play reactions.\
                                        \n\n* 'OK': Use this to inform your opponent you have no more reactions to play.")
   else:
      if debugVerbosity > 0: finalTXT = 'AutoScript: {}\n\n AutoAction: {}'.format(CardsAS.get(card.model,''),CardsAA.get(card.model,''))
      else: finalTXT = "Card Text: {}\n\n{}\n\nWould you like to see the card's details online?".format(card.Rules,ASText)
      if confirm("{}".format(finalTXT)): rulings(card)

def inspectTargetCard(group, x = 0, y = 0): # This function shows the player the card text, to allow for easy reading until High Quality scans are procured.
   debugNotify(">>> inspectTargetCard(){}".format(extraASDebug())) #Debug
   for card in table:
      if card.targetedBy and card.targetedBy == me: inspectCard(card)
      
#------------------------------------------------------------------------------
# Hand Actions
#------------------------------------------------------------------------------

def currentHandSize(player = me):
   debugNotify(">>> currentHandSizel(){}".format(extraASDebug())) #Debug
   specialCard = getSpecial('Identity', player)
   if specialCard.markers[mdict['BrainDMG']]: currHandSize =  player.counters['Hand Size'].value - specialCard.markers[mdict['BrainDMG']]
   else: currHandSize = player.counters['Hand Size'].value
   return currHandSize

def intPlay(card, cost = 'not free', scripted = False, preReduction = 0, retainPos = False):
   debugNotify(">>> intPlay(){}".format(extraASDebug())) #Debug
   global gatheredCardList
   gatheredCardList = False # We reset this variable because we can call intPlay from other scripts. And at that point we want to re-scan the table.
   extraText = '' # We set this here, because the if clause that may modify this variable will not be reached in all cases. So we need to set it to null here to avoid a python error later.
   mute()
   chooseSide() # Just in case...
   if not scripted: whisper("+++ Processing. Please Hold...")
   storeProperties(card)
   update()
   if not checkNotHardwareConsole(card, manual = retainPos): return	#If player already has a Console in play and doesnt want to play that card, do nothing.
   if card.Type != 'ICE' and card.Type != 'Agenda' and card.Type != 'Upgrade' and card.Type != 'Asset': # We only check for uniqueness on install, against cards that install face-up
      if not checkUnique(card, manual = retainPos): return #If the player has the unique card and opted not to trash it, do nothing.
   if scripted: NbReq = 0
   elif re.search(r'Double', getKeywords(card)) and not chkDoublePrevention():
      NbReq = 2 # Some cards require two clicks to play. This variable is passed to the useClick() function.
   else: NbReq = 1 #In case it's not a "Double" card. Then it only uses one click to play.
   ClickCost = useClick(count = NbReq, manual = retainPos)
   if ClickCost == 'ABORT': 
      if retainPos: card.moveTo(me.hand)
      return  #If the player didn't have enough clicks and opted not to proceed, do nothing.
   if (card.Type == 'Operation' or card.Type == 'Event') and chkTargeting(card) == 'ABORT': 
      me.Clicks += NbReq # We return any used clicks in case of aborting due to missing target
      card.moveTo(me.hand)
      return 'ABORT'# If it's an Operation or Event and has targeting requirements, check with the user first.
   host = chkHostType(card)
   debugNotify("host received: {}".format(host), 4)
   if host:
      try:
         if host == 'ABORT':
            me.Clicks += NbReq
            if retainPos: card.moveTo(me.hand)
            return 'ABORT'
      except: # If there's an exception, it means that the host is a card object which cannot be compared to a string
         debugNotify("Found Host", 2)
         hostTXT = ' on {}'.format(host) # If the card requires a valid host and we found one, we will mention it later.
   else:
      debugNotify("No Host Requirement", 2)
      hostTXT = ''
   debugNotify("Finished Checking Host Requirements", 2)
   if card.Type == 'Event' or card.Type == 'Operation': action = 'PLAY'
   else: action = 'INSTALL'
   MUtext = ''
   rc = ''
   if card.Type == 'Resource' and re.search(r'Hidden', getKeywords(card)): hiddenresource = 'yes'
   else: hiddenresource = 'no'
   expectedCost = num(card.Cost) - preReduction
   if expectedCost < 0: expectedCost = 0
   if card.Type == 'ICE' or card.Type == 'Agenda' or card.Type == 'Asset' or card.Type == 'Upgrade':
      placeCard(card, action, retainPos = retainPos)
      if fetchProperty(card, 'Type') == 'ICE': card.orientation ^= Rot90 # Ice are played sideways.
      notify("{} to install a card.".format(ClickCost))
      #card.isFaceUp = False # Now Handled by placeCard()
   elif card.Type == 'Program' or card.Type == 'Event' or card.Type == 'Resource' or card.Type == 'Hardware':
      MUtext = chkRAM(card)
      if card.Type == 'Resource' and hiddenresource == 'yes':
         placeCard(card, action, retainPos = retainPos)
         executePlayScripts(card,action)
         card.isFaceUp = False
         notify("{} to install a hidden resource.".format(ClickCost))
         return
      if cost == 'not free': # If the cost is not free, then we check for cost reductors/increasers and do a dryrun to gather how much the reduction is going to be.
         reduction = reduceCost(card, action, expectedCost, dryRun = True) #Checking to see if the cost is going to be reduced by cards we have in play.
         if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction)) #If it is, make sure to inform.
         elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      else: reduction = 0
      rc = payCost(expectedCost - reduction, cost)
      if rc == "ABORT":
         me.Clicks += NbReq # If the player didn't notice they didn't have enough credits, we give them back their click
         if retainPos: card.moveTo(me.hand)
         return 'ABORT' # If the player didn't have enough money to pay and aborted the function, then do nothing.
      elif rc == "free": 
         extraText = " at no cost"
         rc = ''
      elif rc != 0: rc = " and pays {}".format(rc)
      else: rc = ''
      if cost == 'not free': reduction = reduceCost(card, action, expectedCost) # Now we go ahead and actually remove any markers from cards
      placeCard(card, action, retainPos = retainPos)
      if card.Type == 'Program':
         for targetLookup in table: # We check if we're targeting a daemon to install the program in.
            if targetLookup.targetedBy and targetLookup.targetedBy == me and (re.search(r'Daemon',getKeywords(targetLookup)) or re.search(r'CountsAsDaemon', CardsAS.get(targetLookup.model,''))) and possess(targetLookup, card, silent = True) != 'ABORT':
               MUtext = ", installing it into {}".format(targetLookup)
               break
         notify("{}{} to install {}{}{}{}.".format(ClickCost, rc, card, hostTXT, extraText,MUtext))
      elif card.Type == 'Event': notify("{}{} to prep with {}{}.".format(ClickCost, rc, card, extraText))
      elif card.Type == 'Hardware': notify("{}{} to setup {}{}{}{}.".format(ClickCost, rc, card, hostTXT, extraText,MUtext))
      elif card.Type == 'Resource' and hiddenresource == 'no': notify("{}{} to acquire {}{}{}{}.".format(ClickCost, rc, card, hostTXT, extraText,MUtext))
      else: notify("{}{} to play {}{}{}.".format(ClickCost, rc, card, extraText,MUtext))
   else:
      if cost == 'not free': 
         reduction = reduceCost(card, action, expectedCost, dryRun = True) #Checking to see if the cost is going to be reduced by cards we have in play.
         if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction)) #If it is, make sure to inform.
         elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      else: reduction = 0
      rc = payCost(expectedCost - reduction, cost)
      if rc == "ABORT":
         me.Clicks += NbReq # If the player didn't notice they didn't have enough credits, we give them back their click
         if retainPos: card.moveTo(me.hand)
         return 'ABORT' # If the player didn't have enough money to pay and aborted the function, then do nothing.
      elif rc == "free": 
         extraText = " at no cost"
         rc = ''
      elif rc != 0: rc = " and pays {}".format(rc)
      else: rc = '' # When the cast costs nothing, we don't include the cost.
      if cost == 'not free': reduction = reduceCost(card, action, expectedCost)
      placeCard(card, action, retainPos = retainPos)
      if card.Type == 'Operation': notify("{}{} to initiate {}{}.".format(ClickCost, rc, card, extraText))
      else: notify("{}{} to play {}{}.".format(ClickCost, rc, card, extraText))
   playInstallSound(card)
   card.highlight = NewCardColor # We give all new cards an orange highlight to make them easiet to see.
   playEvOpSound(card)
   executePlayScripts(card,action)
   autoscriptOtherPlayers('Card'+action.capitalize(),card) # we tell the autoscriptotherplayers that we installed/played a card. (e.g. See Haas-Bioroid ability)
   if debugVerbosity >= 3: notify("<<< intPlay().action: {}\nAutoscriptedothers: {}".format(action,'Card'+action.capitalize())) #Debug
   if debugVerbosity >= 1:
      if Stored_Type.get(card._id,None): notify("++++ Stored Type: {}".format(fetchProperty(card, 'Type')))
      else: notify("++++ No Stored Type Found for {}".format(card))
      if Stored_Keywords.get(card._id,None): notify("++++ Stored Keywords: {}".format(fetchProperty(card, 'Keywords')))
      else: notify("++++ No Stored Keywords Found for {}".format(card))
      if Stored_Cost.get(card._id,None): notify("++++ Stored Cost: {}".format(fetchProperty(card, 'Cost')))
      else: notify("++++ No Stored Cost Found for {}".format(card))

def playForFree(card, x = 0, y = 0):
   debugNotify(">>> playForFree(){}".format(extraASDebug())) #Debug
   intPlay(card,"free")

def movetoTopOfStack(card):
   debugNotify(">>> movetoTopOfStack(){}".format(extraASDebug())) #Debug
   mute()
   deck = me.piles['R&D/Stack']
   card.moveTo(deck)
   notify ("{} moves a card to top of their {}.".format(me,pileName(deck)))

def movetoBottomOfStack(card):
   debugNotify(">>> movetoBottomOfStack(){}".format(extraASDebug())) #Debug
   mute()
   deck = me.piles['R&D/Stack']
   card.moveToBottom(deck)
   notify ("{} moves a card to Bottom of their {}.".format(me,pileName(deck)))

def handtoArchives(card):
   debugNotify(">>> handtoArchives(){}".format(extraASDebug())) #Debug
   if ds == "runner": return
   mute()
   card.moveTo(me.piles['Heap/Archives(Face-up)'])
   notify ("{} moves a card to their face-up Archives.".format(me))

def handDiscard(card, scripted = False):
   debugNotify(">>> handDiscard(){}".format(extraASDebug())) #Debug
   mute()
   if not scripted: playDiscardHandCardSound()
   if ds == "runner":
      card.moveTo(me.piles['Heap/Archives(Face-up)'])
      if endofturn:
         if card.Type == 'Program': notify("{} has killed a hanging process ({}).".format(me,card))
         elif card.Type == 'Event': notify("{} has thrown away some notes ({}).".format(me,card))
         elif card.Type == 'Hardware': notify("{} has deleted some spam mail ({}).".format(me,card))
         elif card.Type == 'Resource': notify("{} has reconfigured some net protocols ({}).".format(me,card))
         else: notify("{} has power cycled some hardware.".format(me))
         if len(me.hand) == currentHandSize():
            notify("{} has now discarded down to their max handsize of {}".format(me, currentHandSize()))
            goToEndTurn(table, 0, 0)
      else: notify("{} discards {}.".format(me,card))
   else:
      card.moveTo(me.piles['Archives(Hidden)'])
      if endofturn:
         random = rnd(1, 5)
         if random == 1: notify("{}'s Internal Audit has corrected some tax book discrepancies.".format(me))
         if random == 2: notify("{} has downsized a department.".format(me))
         if random == 3: notify("{}'s Corporation has sent some hardware to secure recycling.".format(me))
         if random == 4: notify("{} has sold off some stock options".format(me))
         if random == 5: notify("{} has liquidated some assets.".format(me))
         if len(me.hand) == currentHandSize():
            notify("{} has now discarded down to their max handsize of {}".format(me, currentHandSize()))
            goToEndTurn(table, 0, 0)
      else: notify("{} discards a card.".format(me))

def handRandomDiscard(group, count = None, player = None, destination = None, silent = False):
   debugNotify(">>> handRandomDiscard(){}".format(extraASDebug())) #Debug
   mute()
   if not player: player = me
   if not destination:
      if ds == "runner": destination = player.piles['Heap/Archives(Face-up)']
      else: destination = player.piles['Archives(Hidden)']
   SSize = len(group)
   if SSize == 0: return 0
   if count == None: count = askInteger("Discard how many cards?", 1)
   if count == None: return 0
   if count > SSize :
      count = SSize
      whisper("You do not have enough cards in your hand to complete this action. Will discard as many as possible")
   for iter in range(count):
      debugNotify(" : handRandomDiscard() iter: {}".format(iter + 1), 3) # Debug
      card = group.random()
      if card == None: return iter + 1 # If we have no more cards, then return how many we managed to discard.
      card.moveTo(destination)
      if not silent: notify("{} discards {} at random.".format(player,card))
   debugNotify("<<< handRandomDiscard() with return {}".format(iter + 1), 2) #Debug
   return iter + 1 #We need to increase the iter by 1 because it starts iterating from 0

def showatrandom(group = None, count = 1, targetPL = None, silent = False, covered = False):
   debugNotify(">>> showatrandom(){}".format(extraASDebug())) #Debug
   mute()
   shownCards = []
   side = 1
   if not targetPL: targetPL = me
   if not group: group = targetPL.hand
   if targetPL != me: side = -1
   if len(group) == 0:
      whisper(":::WARNING::: {} had no cards in their hand!".format(targetPL))
      return shownCards
   elif count > len(group):
      whisper(":::WARNING::: {} has only {} cards in their hand.".format(targetPL,len(group)))
      count = len(group)
   # if group == targetPL.hand: # Disabling because it seems buggy and slow.
      # for c in group:  c.moveTo(targetPL.ScriptingPile)        
      # targetPL.ScriptingPile.shuffle()
      # for c in targetPL.ScriptingPile: c.moveTo(targetPL.hand)
   for iter in range(count):
      card = group.random()
      if card.controller != me: # If we're revealing a card from another player's hand, we grab its properties before we put it on the table, as as not to give away if we're scanning it right now or not.
         card.isFaceUp = True
         storeProperties(card, forced = False)
      time.sleep(1)
      if card == None:
         notify(":::Info:::{} has no more cards in their hand to reveal".format(targetPL))
         break
      if covered:
         cover = table.create("ac3a3d5d-7e3a-4742-b9b2-7f72596d9c1b",playerside * side * iter * cwidth(card) - (count * cwidth(card) / 2), 0 - yaxisMove(card) * side,1,False)
         cover.moveToTable(playerside * side * iter * cwidth(card) - (count * cwidth(card) / 2), 0 - yaxisMove(card) * side,False)
      card.moveToTable(playerside * side * iter * cwidth(card) - (count * cwidth(card) / 2), 0 - yaxisMove(card) * side, False)
      card.highlight = RevealedColor
      card.sendToBack()
      if not covered: loopChk(card) # A small delay to make sure we grab the card's name to announce
      shownCards.append(card) # We put the revealed cards in a list to return to other functions that call us
   if not silent: notify("{} reveals {} at random from their hand.".format(targetPL,card))
   debugNotify("<<< showatrandom() with return {}".format(card), 2) #Debug
   return shownCards

def groupToDeck (group = me.hand, player = me, silent = False):
   debugNotify(">>> groupToDeck(){}".format(extraASDebug())) #Debug
   mute()
   deck = player.piles['R&D/Stack']
   count = len(group)
   for c in group: c.moveTo(deck)
   if not silent: notify ("{} moves their whole {} to their {}.".format(player,pileName(group),pileName(deck)))
   if debugVerbosity >= 3: notify("<<< groupToDeck() with return:\n{}\n{}\n{}".format(pileName(group),pileName(deck),count)) #Debug
   else: return(pileName(group),pileName(deck),count) # Return a tuple with the names of the groups.

def mulligan(group):
   debugNotify(">>> mulligan(){}".format(extraASDebug())) #Debug
   if not confirm("Are you sure you want to take a mulligan?"): return
   notify("{} is taking a Mulligan...".format(me))
   groupToDeck(group,silent = True)
   resetAll()
   for i in range(1):
      rnd(1,10)
      shuffle(me.piles['R&D/Stack']) # We do a good shuffle this time.
      whisper("Shuffling...")
   drawMany(me.piles['R&D/Stack'], 5)
   executePlayScripts(Identity,'MULLIGAN')
   debugNotify("<<< mulligan()", 3) #Debug

#------------------------------------------------------------------------------
# Pile Actions
#------------------------------------------------------------------------------
def shuffle(group):
   debugNotify(">>> shuffle(){}".format(extraASDebug())) #Debug
   group.shuffle()

def draw(group):
   debugNotify(">>> draw(){}".format(extraASDebug())) #Debug
   global newturn
   mute()
   if len(group) == 0:
      if ds == 'corp':
         notify(":::ATTENTION::: {} cannot draw another card. {} loses the game!".format(me,me))
         reportGame('DeckDefeat')
      else:
         whisper(":::ERROR::: No more cards in your stack")
      return
   card = group.top()
   if ds == 'corp' and newturn:
      card.moveTo(me.hand)
      notify("--> {} performs the turn's mandatory draw.".format(me))
      newturn = False
   else:
      ClickCost = useClick()
      if ClickCost == 'ABORT': return
      changeCardGroup(card,me.hand)
      notify("{} to draw a card.".format(ClickCost))
      playClickDrawSound()
      autoscriptOtherPlayers('CardDrawnClicked',card)
   if len(group) <= 3 and ds == 'corp': notify(":::WARNING::: {} is about to be decked! R&D down to {} cards.".format(me,len(group)))
   storeProperties(card)

def drawMany(group, count = None, destination = None, silent = False):
   debugNotify(">>> drawMany(){}".format(extraASDebug())) #Debug
   debugNotify("source: {}".format(group.name), 2)
   if destination: debugNotify("destination: {}".format(destination.name), 2)
   mute()
   if destination == None: destination = me.hand
   SSize = len(group)
   if SSize == 0: return 0
   if count == None: count = askInteger("Draw how many cards?", 5)
   if count == None: return 0
   if count > SSize:
      if group.player == me and group == me.piles['R&D/Stack'] and destination == me.hand and ds == 'corp':
         if confirm("You do not have enough cards in your R&D to draw. Continuing with this action will lose you the game. Proceed?"):
            notify(":::ATTENTION::: {} cannot draw the full amount of cards. {} loses the game!".format(me,me))
            reportGame('DeckDefeat')
            return count
         else: 
            notify(":::WARNING::: {} canceled the card draw effect to avoid decking themselves".format(me))
            return 0
      else: 
         count = SSize
         whisper("You do not have enough cards in your deck to complete this action. Will draw as many as possible")
   for c in group.top(count):
      changeCardGroup(c,destination)
      #c.moveTo(destination)
   if not silent: notify("{} draws {} cards.".format(me, count))
   if len(group) <= 3 and group.player.getGlobalVariable('ds') == 'corp': notify(":::WARNING::: {} is about to be decked! R&D down to {} cards.".format(group.player,len(group)))
   debugNotify("<<< drawMany() with return: {}".format(count), 3)
   return count

def toarchives(group = me.piles['Archives(Hidden)']):
   debugNotify(">>> toarchives(){}".format(extraASDebug())) #Debug
   mute()
   Archives = me.piles['Heap/Archives(Face-up)']
   for c in group: c.moveTo(Archives)
   #Archives.shuffle()
   notify ("{} moves Hidden Archives to their Face-Up Archives.".format(me))

def archivestoStack(group, silent = False):
   debugNotify(">>> archivestoStack(){}".format(extraASDebug())) #Debug
   mute()
   deck = me.piles['R&D/Stack']
   for c in group: c.moveTo(deck)
   #Archives.shuffle()
   if not silent: notify ("{} moves their {} to {}.".format(me,pileName(group),pileName(deck)))
   else: return(pileName(group),pileName(deck))

def mill(group):
   debugNotify(">>> mill(){}".format(extraASDebug())) #Debug
   if len(group) == 0: return
   mute()
   count = askInteger("Mill how many cards?", 1)
   if count == None: return
   if ds == "runner": destination = me.piles['Heap/Archives(Face-up)']
   else: destination = me.piles['Archives(Hidden)']
   for c in group.top(count): c.moveTo(destination)
   notify("{} mills the top {} cards from their {} to {}.".format(me, count,pileName(group),pileName(destination)))

def moveXtopCardtoBottomStack(group):
   debugNotify(">>> moveXtopCardtoBottomStack(){}".format(extraASDebug())) #Debug
   mute()
   if len(group) == 0: return
   count = askInteger("Move how many cards?", 1)
   if count == None: return
   for c in group.top(count): c.moveToBottom(group)
   notify("{} moves the top {} cards from their {} to the bottom of {}.".format(me, count,pileName(group),pileName(group)))


########NEW FILE########
__FILENAME__ = autoscripts
    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the autoscripting of the game. These are the actions that trigger automatically
#  when the player plays a card, double-clicks on one, or goes to Start/End ot Turn/Run
# * [Play/Score/Rez/Trash trigger] is basically used when the a card enters or exist play in some way 
# * [Card Use trigger] is used when a card is being used while on the table. I.e. being double-clicked.
# * [Other Player trigger] is used when another player plays a card or uses an action. The other player basically do your card effect for you
# * [Start/End of Turn/Run trigger] is called at the start/end of turns or runs actions.
# * [Core Commands] is the primary place where all the autoscripting magic happens.
# * [Helper Commands] are usually shared by many Core Commands, or maybe used many times in one of them.
###=================================================================================================================###

import re

secretCred = None # Used to allow the player to spend credits in secret for some card abilities (e.g. Snowflake)
failedRequirement = True # A Global boolean that we set in case an Autoscript cost cannot be paid, so that we know to abort the rest of the script.
EscherUse = 0

#------------------------------------------------------------------------------
# Play/Score/Rez/Trash trigger
#------------------------------------------------------------------------------

def executePlayScripts(card, action):
   action = action.upper() # Just in case we passed the wrong case
   debugNotify(">>> executePlayScripts() for {} with action: {}".format(card,action)) #Debug
   debugNotify("AS dict entry = {}".format(CardsAS.get(card.model,'NULL')),4)
   debugNotify("card.model = {}".format(card.model),4)
   global failedRequirement
   if not Automations['Play, Score and Rez']: 
      debugNotify("Exiting because automations are off", 2)
      return
   if CardsAS.get(card.model,'NULL') == 'NULL': 
      debugNotify("Exiting because card has no autoscripts", 2)
      return
   failedRequirement = False
   X = 0
   Autoscripts = CardsAS.get(card.model,'').split('||') # When playing cards, the || is used as an "and" separator, rather than "or". i.e. we don't do choices (yet)
   autoScriptsSnapshot = list(Autoscripts) # Need to work on a snapshot, because we'll be modifying the list.
   for autoS in autoScriptsSnapshot: # Checking and removing any "AtTurnStart" clicks.
      if (autoS == '' or 
          re.search(r'atTurn(Start|End)', autoS) or 
          re.search(r'atRunStart', autoS) or 
          re.search(r'Reduce[0-9#X]Cost', autoS) or 
          re.search(r'whileRunning', autoS) or 
          re.search(r'atJackOut', autoS) or 
          re.search(r'atSuccessfulRun', autoS) or 
          re.search(r'onAccess', autoS) or 
          re.search(r'onHost', autoS) or 
          re.search(r'Placement', autoS) or 
          re.search(r'CaissaPlace', autoS) or 
          re.search(r'whileInPlay', autoS) or 
          re.search(r'ConstantAbility', autoS) or 
          re.search(r'onPay', autoS) or # onPay effects are only useful before we go to the autoscripts, for the cost reduction.
          re.search(r'triggerNoisy', autoS) or # Trigger Noisy are used automatically during action use.
          re.search(r'-isTrigger', autoS)): Autoscripts.remove(autoS)
      elif re.search(r'excludeDummy', autoS) and card.highlight == DummyColor: Autoscripts.remove(autoS)
      elif re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor: Autoscripts.remove(autoS)
      elif re.search(r'CustomScript', autoS): 
         CustomScript(card,action)
         Autoscripts.remove(autoS)
   if len(Autoscripts) == 0: return
   if debugVerbosity >= 2: notify ('Looking for multiple choice options') # Debug
   if action == 'PLAY': trigger = 'onPlay' # We figure out what can be the possible multiple choice trigger
   elif action == 'REZ': trigger = 'onRez'
   elif action == 'INSTALL': trigger = 'onInstall'
   elif action == 'SCORE': trigger = 'onScore'
   elif action == 'TRASH': trigger = 'onTrash'
   else: trigger = 'N/A'
   if debugVerbosity >= 2: notify ('trigger = {}'.format(trigger)) # Debug
   if trigger != 'N/A': # If there's a possibility of a multiple choice trigger, we do the check
      TriggersFound = [] # A List which will hold any valid abilities for this trigger
      for autoS in Autoscripts:
         if re.search(r'{}:'.format(trigger),autoS): # If the script has the appropriate trigger, we put it into the list.
            TriggersFound.append(autoS)
      if debugVerbosity >= 2: notify ('TriggersFound = {}'.format(TriggersFound)) # Debug
      if len(TriggersFound) > 1: # If we have more than one option for this trigger, we need to ask the player for which to use.
         if Automations['WinForms']: ChoiceTXT = "This card has multiple abilities that can trigger at this point.\nSelect the ones you would like to use."
         else: ChoiceTXT = "This card has multiple abilities that can trigger at this point.\nType the number of the one you would like to use."
         triggerInstructions = re.search(r'{}\[(.*?)\]'.format(trigger),card.Instructions) # If the card has multiple options, it should also have some card instructions to have nice menu options.
         if not triggerInstructions and debugVerbosity >= 1: notify("## Oops! No multiple choice instructions found and I expected some. Will crash prolly.") # Debug
         cardInstructions = triggerInstructions.group(1).split('|-|') # We instructions for trigger have a slightly different split, so as not to conflict with the instructions from AutoActions.
         choices = cardInstructions
         abilChoice = SingleChoice(ChoiceTXT, choices, type = 'button')
         if abilChoice == 'ABORT' or abilChoice == None: return # If the player closed the window, or pressed Cancel, abort.
         TriggersFound.pop(abilChoice) # What we do now, is we remove the choice we made, from the list of possible choices. We remove it because then we will remove all the other options from the main list "Autoscripts"
         for unchosenOption in TriggersFound:
            if debugVerbosity >= 4: notify (' Removing unused option: {}'.format(unchosenOption)) # Debug
            Autoscripts.remove(unchosenOption)
         if debugVerbosity >= 2: notify ('Final Autoscripts after choices: {}'.format(Autoscripts)) # Debug
   for autoS in Autoscripts:
      debugNotify("First Processing: {}".format(autoS), 2) # Debug
      effectType = re.search(r'(on[A-Za-z]+|while[A-Za-z]+):', autoS)
      if not effectType:
         debugNotify("no regeX match for playscripts. aborting",4)
         continue
      else: debugNotify("effectType.group(1)= {}".format(effectType.group(1)),4)
      if ((effectType.group(1) == 'onRez' and action != 'REZ') or # We don't want onPlay effects to activate onTrash for example.
          (effectType.group(1) == 'onPlay' and action != 'PLAY') or
          (effectType.group(1) == 'onInstall' and action != 'INSTALL') or
          (effectType.group(1) == 'onScore' and action != 'SCORE') or
          (effectType.group(1) == 'onStartup' and action != 'STARTUP') or
          (effectType.group(1) == 'onMulligan' and action != 'MULLIGAN') or
          (effectType.group(1) == 'whileScored' and ds != 'corp') or
          (effectType.group(1) == 'whileLiberated' and ds != 'runner') or
          (effectType.group(1) == 'onDamage' and action != 'DAMAGE') or
          (effectType.group(1) == 'onLiberation' and action != 'LIBERATE') or
          (effectType.group(1) == 'onTrash' and action != 'TRASH' and action!= 'UNINSTALL' and action != 'DEREZ') or
          (effectType.group(1) == 'onDerez' and action != 'DEREZ')): 
         debugNotify("Rejected {} because {} does not fit with {}".format(autoS,effectType.group(1),action))
         continue 
      if re.search(r'-isOptional', autoS):
         if not confirm("This card has an optional ability you can activate at this point. Do you want to do so?"): 
            notify("{} opts not to activate {}'s optional ability".format(me,card))
            return 'ABORT'
         else: notify("{} activates {}'s optional ability".format(me,card))
      selectedAutoscripts = autoS.split('$$')
      if debugVerbosity >= 2: notify ('selectedAutoscripts: {}'.format(selectedAutoscripts)) # Debug
      for activeAutoscript in selectedAutoscripts:
         debugNotify("Second Processing: {}".format(activeAutoscript), 2) # Debug
         if chkWarn(card, activeAutoscript) == 'ABORT': return
         if not ifHave(activeAutoscript): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if not ifVarSet(activeAutoscript): continue # If the script requires a shared AutoScript variable to be set to a specific value.
         if not checkOrigSpecialRestrictions(activeAutoscript,card): continue  
         if not chkRunStatus(activeAutoscript): continue
         if re.search(r'-ifAccessed', activeAutoscript) and ds != 'runner': 
            debugNotify("!!! Failing script because card is not being accessed")
            continue # These scripts are only supposed to fire from the runner (when they access a card)         
         if re.search(r'-ifActive', activeAutoscript):
            if card.highlight == InactiveColor or card.highlight == RevealedColor or card.group.name != 'Table':
               debugNotify("!!! Failing script because card is inactive. highlight == {}. group.name == {}".format(card.highlight,card.group.name))
               continue 
            else: debugNotify("Succeeded for -ifActive. highlight == {}. group.name == {}".format(card.highlight,card.group.name))
         else: debugNotify("No -ifActive Modulator")
         if re.search(r'-ifScored', activeAutoscript) and not card.markers[mdict['Scored']] and not card.markers[mdict['ScorePenalty']]:
            debugNotify("!!! Failing script because card is not scored")
            continue 
         if re.search(r'-ifUnscored', activeAutoscript) and (card.markers[mdict['Scored']] or card.markers[mdict['ScorePenalty']]):
            debugNotify("!!! Failing script because card is scored")
            continue 
         if re.search(r':Pass\b', activeAutoscript): continue # Pass is a simple command of doing nothing ^_^
         effect = re.search(r'\b([A-Z][A-Za-z]+)([0-9]*)([A-Za-z& ]*)\b([^:]?[A-Za-z0-9_&{}\|:,<>+ -]*)', activeAutoscript)
         if not effect: 
            whisper(":::ERROR::: In AutoScript: {}".format(activeAutoscript))
            continue
         debugNotify('effects: {}'.format(effect.groups()), 2) #Debug
         if effectType.group(1) == 'whileRezzed' or effectType.group(1) == 'whileInstalled' or effectType.group(1) == 'whileScored' or effectType.group(1) == 'whileLiberated':
            if action == 'STARTUP' or action == 'MULLIGAN': 
               debugNotify("Aborting while(Rezzed|Scored|etc) because we're on statup/mulligan")
               continue # We don't want to run whileRezzed events during startup
            else: debugNotify("not on statup/mulligan. proceeding")
            if effect.group(1) != 'Gain' and effect.group(1) != 'Lose': continue # The only things that whileRezzed and whileScored affect in execute Automations is GainX scripts (for now). All else is onTrash, onPlay etc
            if action == 'DEREZ' or ((action == 'TRASH' or action == 'UNINSTALL') and card.highlight != InactiveColor and card.highlight != RevealedColor): Removal = True
            else: Removal = False
         #elif action == 'DEREZ' or action == 'TRASH': continue # If it's just a one-off event, and we're trashing it, then do nothing.
         else: Removal = False
         targetC = findTarget(activeAutoscript)
         targetPL = ofwhom(activeAutoscript,card.owner) # So that we know to announce the right person the effect, affects.
         announceText = "{} uses {}'s ability to".format(targetPL,card)
         debugNotify(" targetC: {}".format(targetC), 3) # Debug
         if effect.group(1) == 'Gain' or effect.group(1) == 'Lose':
            if Removal: 
               if effect.group(1) == 'Gain': passedScript = "Lose{}{}".format(effect.group(2),effect.group(3))
               elif effect.group(1) == 'SetTo': passedScript = "SetTo{}{}".format(effect.group(2),effect.group(3))
               else: passedScript = "Gain{}{}".format(effect.group(2),effect.group(3))
            else: 
               if effect.group(1) == 'Gain': passedScript = "Gain{}{}".format(effect.group(2),effect.group(3))
               elif effect.group(1) == 'SetTo': passedScript = "SetTo{}{}".format(effect.group(2),effect.group(3))
               else: passedScript = "Lose{}{}".format(effect.group(2),effect.group(3))
            if effect.group(4): passedScript += effect.group(4)
            debugNotify("passedscript: {}".format(passedScript), 2) # Debug
            gainTuple = GainX(passedScript, announceText, card, targetC, notification = 'Quick', n = X, actionType = action)
            if gainTuple == 'ABORT': return
            X = gainTuple[1] 
         else: 
            passedScript = effect.group(0)
            debugNotify("passedscript: {}".format(passedScript), 2) # Debug
            if regexHooks['CreateDummy'].search(passedScript): 
               if CreateDummy(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['DrawX'].search(passedScript): 
               if DrawX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['TokensX'].search(passedScript): 
               if TokensX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['RollX'].search(passedScript): 
               rollTuple = RollX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if rollTuple == 'ABORT': return
               X = rollTuple[1] 
            elif regexHooks['RequestInt'].search(passedScript): 
               numberTuple = RequestInt(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if numberTuple == 'ABORT': return
               X = numberTuple[1] 
            elif regexHooks['DiscardX'].search(passedScript): 
               discardTuple = DiscardX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if discardTuple == 'ABORT': return
               X = discardTuple[1] 
            elif regexHooks['RunX'].search(passedScript): 
               if RunX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['TraceX'].search(passedScript): 
               if TraceX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['PsiX'].search(passedScript): 
               if PsiX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['ReshuffleX'].search(passedScript): 
               reshuffleTuple = ReshuffleX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if reshuffleTuple == 'ABORT': return
               X = reshuffleTuple[1]
            elif regexHooks['ShuffleX'].search(passedScript): 
               if ShuffleX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['ChooseKeyword'].search(passedScript): 
               if ChooseKeyword(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['InflictX'].search(passedScript): 
               if InflictX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['SetVarX'].search(passedScript): 
               if SetVarX(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['RetrieveX'].search(passedScript): 
               retrieveTuple = RetrieveX(passedScript, announceText, card, targetC, notification = 'Quick', n = X)
               if retrieveTuple == 'ABORT': return # Retrieve also returns the cards it found in a tuple. But we're not using those here.
               X = len(retrieveTuple[1])
            elif regexHooks['ModifyStatus'].search(passedScript): 
               if ModifyStatus(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': return
            elif regexHooks['UseCustomAbility'].search(passedScript):
               if UseCustomAbility(passedScript, announceText, card, targetC, notification = 'Quick', n = X) == 'ABORT': break
         if failedRequirement: break # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.
         debugNotify("Loop for scipt {} finished".format(passedScript), 2)

#------------------------------------------------------------------------------
# Card Use trigger
#------------------------------------------------------------------------------

def useAbility(card, x = 0, y = 0): # The start of autoscript activation.
   debugNotify(">>> useAbility(){}".format(extraASDebug())) #Debug
   mute()
   update() # Make sure all other effects have finished resolving.
   global failedRequirement,gatheredCardList
   AutoscriptsList = [] # An empty list which we'll put the AutoActions to execute.
   storeProperties(card) # Just in case
   failedRequirement = False # We set it to false when we start a new autoscript.
   debugNotify("Checking if Tracing card...", 4)
   if card.Type == 'Button': # The Special button cards.
      if card.name == 'Access Imminent': BUTTON_Access()
      elif card.name == 'No Rez': BUTTON_NoRez()
      elif card.name == 'Wait!': BUTTON_Wait()
      elif card.name == 'Start Turn': goToSot(0)
      elif card.name == 'End Turn': goToEndTurn(0)
      elif card.name == 'Grant Access': runSuccess(0)
      else:
          debugNotify("## Unknown button pressed, treating as OK",4)
          BUTTON_OK()
      return
   if (card._id in Stored_Type and fetchProperty(card, 'Type') == 'Tracing') or card.model == 'eb7e719e-007b-4fab-973c-3fe228c6ce20': # If the player double clicks on the Tracing card...
      debugNotify("+++ Confirmed tacting card. Checking Status...", 5)
      if card.isFaceUp and not card.markers[mdict['Credits']]: inputTraceValue(card, limit = 0)
      elif card.isFaceUp and card.markers[mdict['Credits']]: payTraceValue(card)
      elif not card.isFaceUp: card.isFaceUp = True
      return
   debugNotify("Not a tracing card. Checking highlight...", 4)
   if markerScripts(card): return # If there's a special marker, it means the card triggers to do something else with the default action
   if card.highlight == InactiveColor:
      accessRegex = re.search(r'onAccess:([^|]+)',CardsAS.get(card.model,''))
      if not accessRegex:
         whisper("You cannot use inactive cards. Please use the relevant card abilities to clear them first. Aborting")
         return
   debugNotify("Finished storing CardsAA.get(card.model,'')s. Checking Rez status", 4)
   if not card.isFaceUp:
      if re.search(r'onAccess',fetchProperty(card, 'AutoActions')) and confirm("This card has an ability that can be activated even when unrezzed. Would you like to activate that now?"): card.isFaceUp = True # Activating an on-access ability requires the card to be exposed, it it's no already.
      elif re.search(r'Hidden',fetchProperty(card, 'Keywords')): card.isFaceUp # If the card is a hidden resource, just turn it face up for its imminent use.
      elif fetchProperty(card, 'Type') == 'Agenda': 
         scrAgenda(card) # If the player double-clicks on an Agenda card, assume they wanted to Score it.
         return
      else: 
         intRez(card) # If card is face down or not rezzed assume they wanted to rez       
         return
   debugNotify("Card not unrezzed. Checking for automations switch...", 4)
   if not Automations['Play, Score and Rez'] or fetchProperty(card, 'AutoActions') == '':
      debugNotify("Going to useCard() because AA = {}".format(fetchProperty(card, 'AutoActions')))
      useCard(card) # If card is face up but has no autoscripts, or automation is disabled just notify that we're using it.
      return
   debugNotify("Automations active. Checking for CustomScript...", 4)
   if re.search(r'CustomScript', fetchProperty(card, 'AutoActions')): 
      if chkTargeting(card) == 'ABORT': return
      if CustomScript(card,'USE') == 'CLICK USED': autoscriptOtherPlayers('CardAction', card)  # Some cards just have a fairly unique effect and there's no use in trying to make them work in the generic framework.
      return
   debugNotify("+++ All checks done!. Starting Choice Parse...", 5)
   ### Checking if card has multiple autoscript options and providing choice to player.
   Autoscripts = fetchProperty(card, 'AutoActions').split('||')
   autoScriptSnapshot = list(Autoscripts)
   for autoS in autoScriptSnapshot: # Checking and removing any clickscripts which were put here in error.
      if (re.search(r'while(Rezzed|Scored)', autoS) 
         or re.search(r'on(Play|Score|Install)', autoS) 
         or re.search(r'AtTurn(Start|End)', autoS)
         or not card.isFaceUp and not re.search(r'onAccess', autoS) # If the card is still unrezzed and the ability does not have "onAccess" on it, it can't be used.
         or (re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor)
         or (re.search(r'(CreateDummy|excludeDummy)', autoS) and card.highlight == DummyColor)): # Dummies in general don't create new dummies
         Autoscripts.remove(autoS)
   debugNotify("Removed bad options", 2)
   if len(Autoscripts) == 0:
      useCard(card) # If the card had only "WhileInstalled"  or AtTurnStart effect, just announce that it is being used.
      return 
   if len(Autoscripts) > 1: 
      #abilConcat = "This card has multiple abilities.\nWhich one would you like to use?\
                #\n\n(Tip: You can put multiple abilities one after the the other (e.g. '110'). Max 9 at once)\n\n" # We start a concat which we use in our confirm window.
      if Automations['WinForms']: ChoiceTXT = "This card has multiple abilities.\nSelect the ones you would like to use, in order, and press the [Finish Selection] button"
      else: ChoiceTXT = "This card has multiple abilities.\nType the ones you would like to use, in order, and press the [OK] button"
      cardInstructions = card.Instructions.split('||')
      if len(cardInstructions) > 1: choices = cardInstructions
      else:
         choices = []
         for idx in range(len(Autoscripts)): # If a card has multiple abilities, we go through each of them to create a nicely written option for the player.
            debugNotify("Autoscripts {}".format(Autoscripts), 2) # Debug
            abilRegex = re.search(r"A([0-9]+)B([0-9]+)G([0-9]+)T([0-9]+):([A-Z][A-Za-z ]+)([0-9]*)([A-Za-z ]*)-?(.*)", Autoscripts[idx]) # This regexp returns 3-4 groups, which we then reformat and put in the confirm dialogue in a better readable format.
            debugNotify("Choice Regex is {}".format(abilRegex.groups()), 2) # Debug
            if abilRegex.group(1) != '0': abilCost = 'Use {} Clicks'.format(abilRegex.group(1))
            else: abilCost = '' 
            if abilRegex.group(2) != '0': 
               if abilCost != '': 
                  if abilRegex.group(3) != '0' or abilRegex.group(4) != '0': abilCost += ', '
                  else: abilCost += ' and '
               abilCost += 'Pay {} Credits'.format(abilRegex.group(2))
            if abilRegex.group(3) != '0': 
               if abilCost != '': 
                  if abilRegex.group(4) != '0': abilCost += ', '
                  else: abilCost += ' and '
               abilCost += 'Lose {} Agenda Points'.format(abilRegex.group(3))
            if abilRegex.group(4) != '0': 
               if abilCost != '': abilCost += ' and '
               if abilRegex.group(4) == '1': abilCost += 'Trash this card'
               else: abilCost += 'Use (Once per turn)'
            if abilRegex.group(1) == '0' and abilRegex.group(2) == '0' and abilRegex.group(3) == '0' and abilRegex.group(4) == '0':
               if not re.search(r'-isCost', Autoscripts[idx]): 
                  abilCost = 'Activate' 
                  connectTXT = ' to '
               else: 
                  abilCost = '' # If the ability claims to be a cost, then we need to put it as part of it, before the "to"
                  connectTXT = ''
            else:
               if not re.search(r'-isCost', Autoscripts[idx]): connectTXT = ' to ' # If there isn't an extra cost, then we connect with a "to" clause
               else: connectTXT = 'and ' 
            if abilRegex.group(6):
               if abilRegex.group(6) == '999': abilX = 'all'
               else: abilX = abilRegex.group(6)
            else: abilX = abilRegex.group(6)
            if re.search(r'-isSubroutine', Autoscripts[idx]): 
               if abilCost == 'Activate':  # IF there's no extra costs to the subroutine, we just use the "enter" glyph
                  abilCost = uniSubroutine()
                  connectTXT = ''
               else: abilCost = '{} '.format(uniSubroutine()) + abilCost # If there's extra costs to the subroutine, we prepend the "enter" glyph to the rest of the costs.
            #abilConcat += '{}: {}{}{} {} {}'.format(idx, abilCost, connectTXT, abilRegex.group(5), abilX, abilRegex.group(7)) # We add the first three groups to the concat. Those groups are always Gain/Hoard/Prod ## Favo/Solaris/Spice
            choices.insert(idx,'{}{}{} {} {}'.format(abilCost, connectTXT, abilRegex.group(5), abilX, abilRegex.group(7)))
            if abilRegex.group(5) == 'Put' or abilRegex.group(5) == 'Remove' or abilRegex.group(5) == 'Refill': choices[idx] += ' counter' # If it's putting a counter, we clarify that.
            debugNotify("About to check rest of choice regex", 3)
            if abilRegex.group(8): # If the autoscript has an 8th group, then it means it has subconditions. Such as "per Marker" or "is Subroutine"
               subconditions = abilRegex.group(8).split('$$') # These subconditions are always separated by dashes "-", so we use them to split the string
               for idx2 in range(len(subconditions)):
                  debugNotify(" Checking subcondition {}:{}".format(idx2,subconditions[idx2]), 4)
                  if re.search(r'isCost', Autoscripts[idx]) and idx2 == 1: choices[idx] += ' to' # The extra costs of an action are always at the first part (i.e. before the $$)
                  elif idx2 > 0: choices[idx] += ' and'
                  subadditions = subconditions[idx2].split('-')
                  for idx3 in range(len(subadditions)):
                     debugNotify(" Checking subaddition {}-{}:{}".format(idx2,idx3,subadditions[idx3]), 4)
                     if re.search(r'warn[A-Z][A-Za-z0-9 ]+', subadditions[idx3]): continue # Don't mention warnings.
                     if subadditions[idx3] in IgnoredModulators: continue # We ignore modulators which are internal to the engine.
                     choices[idx] += ' {}'.format(subadditions[idx3]) #  Then we iterate through each distinct subcondition and display it without the dashes between them. (In the future I may also add whitespaces between the distinct words)
            #abilConcat += '\n' # Finally add a newline at the concatenated string for the next ability to be listed.
      abilChoice = multiChoice(ChoiceTXT, choices,card) # We use the ability concatenation we crafted before to give the player a choice of the abilities on the card.
      if abilChoice == [] or abilChoice == 'ABORT' or abilChoice == None: return # If the player closed the window, or pressed Cancel, abort.
      #choiceStr = str(abilChoice) # We convert our number into a string
      for choice in abilChoice: 
         if choice < len(Autoscripts): AutoscriptsList.append(Autoscripts[choice].split('$$'))
         else: continue # if the player has somehow selected a number that is not a valid option, we just ignore it
      debugNotify("AutoscriptsList: {}".format(AutoscriptsList), 2) # Debug
   else: AutoscriptsList.append(Autoscripts[0].split('$$'))
   prev_announceText = 'NULL'
   multiCount = 0
   if len(AutoscriptsList): playUseSound(card)
   startingCreds = me.Credits # We store our starting credits so that we may see if we won or lost any after our action is complete, to announce.
   for iter in range(len(AutoscriptsList)):
      debugNotify("iter = {}".format(iter), 2)
      selectedAutoscripts = AutoscriptsList[iter]
      timesNothingDone = 0 # A variable that keeps track if we've done any of the autoscripts defined. If none have been coded, we just engage the card.
      X = 0 # Variable for special costs.
      if card.highlight == DummyColor: lingering = ' the lingering effect of' # A text that we append to point out when a player is using a lingering effect in the form of a dummy card.
      else: lingering = ''
      for activeAutoscript in selectedAutoscripts:
         #confirm("Active Autoscript: {}".format(activeAutoscript)) #Debug
         ### Checking if any of the card's effects requires one or more targets first
         if re.search(r'Targeted', activeAutoscript) and findTarget(activeAutoscript, dryRun = True) == []: return
      CardAction = False # A boolean which stores if the card's ability required a click or not.
      for activeAutoscript in selectedAutoscripts:
         debugNotify("Reached ifHave chk", 3)
         if not ifHave(activeAutoscript): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if re.search(r'onlyOnce',activeAutoscript) and oncePerTurn(card, silent = True) == 'ABORT': return
         if re.search(r'restrictionMarker',activeAutoscript) and chkRestrictionMarker(card, activeAutoscript, silent = True) == 'ABORT': continue
         targetC = findTarget(activeAutoscript)
         ### Warning the player in case we need to
         if chkWarn(card, activeAutoscript) == 'ABORT': return
         if chkTagged(activeAutoscript) == 'ABORT': return
         ### Checking the activation cost and preparing a relevant string for the announcement
         actionCost = re.match(r"A([0-9]+)B([0-9]+)G([0-9]+)T([0-9]+):", activeAutoscript) 
         # This is the cost of the card.  It starts with A which is the amount of Clicks needed to activate
         # After A follows B for Credit cost, then for aGenda cost.
         # T takes a binary value. A value of 1 means the card needs to be trashed.
         if actionCost: # If there's no match, it means we've already been through the cost part once and now we're going through the '$$' part.
            if actionCost.group(1) != '0': # If we need to use clicks
               Acost = useClick(count = num(actionCost.group(1)))
               if Acost == 'ABORT': return
               else: announceText = Acost
               CardAction = True
            else: announceText = '{}'.format(me) # A variable with the text to be announced at the end of the action.
            if actionCost.group(2) != '0': # If we need to pay credits
               reduction = reduceCost(card, 'USE', num(actionCost.group(2)))
               gatheredCardList = True # We set this to true, so that reduceCost doesn't scan the table for subsequent executions
               if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))  
               elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
               else: extraText = ''
               Bcost = payCost(num(actionCost.group(2)) - reduction)
               if Bcost == 'ABORT': # if they can't pay the cost afterall, we return them their clicks and abort.
                  me.Clicks += num(actionCost.group(1))
                  return
               if actionCost.group(1) != '0':
                  if actionCost.group(3) != '0' or actionCost.group(4) != '0': announceText += ', '
                  else: announceText += ' and '
               else: announceText += ' '
               announceText += 'pays {}{}'.format(uniCredit(num(actionCost.group(2)) - reduction),extraText)
            if actionCost.group(3) != '0': # If we need to pay agenda points...
               Gcost = payCost(actionCost.group(3), counter = 'AP')
               if Gcost == 'ABORT': 
                  me.Clicks += num(actionCost.group(1))
                  me.counters['Credits'].value += num(actionCost.group(2))
                  return
               if actionCost.group(1) != '0' or actionCost.group(2)  != '0':
                  if actionCost.group(4) != '0': announceText += ', '
                  else: announceText += ' and '
               else: announceText += ' '
               announceText += 'liquidates {} Agenda Points'.format(actionCost.group(3))
            if actionCost.group(4) != '0': # If the card needs to be trashed...
               if (actionCost.group(4) == '2' and oncePerTurn(card, silent = True) == 'ABORT') or (actionCost.group(4) == '1' and not confirm("This action will trash the card as a cost. Are you sure you want to continue?")):
                  # On trash cost, we confirm first to avoid double-click accidents
                  me.Clicks += num(actionCost.group(1))
                  me.counters['Credits'].value += num(actionCost.group(2))
                  me.counters['Agenda Points'].value += num(actionCost.group(3))
                  return
               if actionCost.group(1) != '0' or actionCost.group(2) != '0' or actionCost.group(3) != '0': announceText += ' and '
               else: announceText += ' '
               if actionCost.group(4) == '1': announceText += 'trashes {} to use its ability'.format(card)
               else: announceText += 'activates the once-per-turn ability of{} {}'.format(lingering,card)
            else: announceText += ' to activate{} {}'.format(lingering,card) # If we don't have to trash the card, we need to still announce the name of the card we're using.
            if actionCost.group(1) == '0' and actionCost.group(2) == '0' and actionCost.group(3) == '0' and actionCost.group(4) == '0':
               if card.Type == 'ICE': announceText = '{} activates {}'.format(me, card)
               else: announceText = '{} uses the ability of{} {}'.format(me, lingering, card)
            if re.search(r'-isSubroutine', activeAutoscript): announceText = '{} '.format(uniSubroutine()) + announceText # if we are in a subroutine, we use the special icon to make it obvious.
            announceText += ' in order to'
         elif not announceText.endswith(' in order to') and not announceText.endswith(' and'): announceText += ' and'
         debugNotify("Entering useAbility() Choice with Autoscript: {}".format(activeAutoscript), 2) # Debug
         ### Calling the relevant function depending on if we're increasing our own counters, the hoard's or putting card markers.
         if regexHooks['GainX'].search(activeAutoscript): 
            gainTuple = GainX(activeAutoscript, announceText, card, targetC, n = X)
            if gainTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = gainTuple[0] 
               X = gainTuple[1] 
         elif regexHooks['CreateDummy'].search(activeAutoscript): announceText = CreateDummy(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ReshuffleX'].search(activeAutoscript): 
            reshuffleTuple = ReshuffleX(activeAutoscript, announceText, card) # The reshuffleX() function is special because it returns a tuple.
            announceText = reshuffleTuple[0] # The first element of the tuple contains the announceText string
            X = reshuffleTuple[1] # The second element of the tuple contains the number of cards that were reshuffled from the hand in the deck.
         elif regexHooks['RetrieveX'].search(activeAutoscript): 
            retrieveTuple = RetrieveX(activeAutoscript, announceText, card, targetC, n = X)
            if retrieveTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = retrieveTuple[0] # The first element of the tuple contains the announceText string
               X = len(retrieveTuple[1]) # The second element of the tuple contains the cards which were retrieved. by countring them we have the X
         elif regexHooks['RollX'].search(activeAutoscript): 
            rollTuple = RollX(activeAutoscript, announceText, card) # Returns like reshuffleX()
            announceText = rollTuple[0] 
            X = rollTuple[1] 
         elif regexHooks['RequestInt'].search(activeAutoscript): 
            numberTuple = RequestInt(activeAutoscript, announceText, card) # Returns like reshuffleX()
            if numberTuple == 'ABORT': announceText == 'ABORT'
            else:
               announceText = numberTuple[0] 
               X = numberTuple[1] 
         elif regexHooks['DiscardX'].search(activeAutoscript): 
            discardTuple = DiscardX(activeAutoscript, announceText, card, targetC, n = X) # Returns like reshuffleX()
            announceText = discardTuple[0] 
            X = discardTuple[1] 
         elif regexHooks['TokensX'].search(activeAutoscript):           announceText = TokensX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['TransferX'].search(activeAutoscript):         announceText = TransferX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['DrawX'].search(activeAutoscript):             announceText = DrawX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ShuffleX'].search(activeAutoscript):          announceText = ShuffleX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['RunX'].search(activeAutoscript):              announceText = RunX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['TraceX'].search(activeAutoscript):            announceText = TraceX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['InflictX'].search(activeAutoscript):          announceText = InflictX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ModifyStatus'].search(activeAutoscript):      announceText = ModifyStatus(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['SimplyAnnounce'].search(activeAutoscript):    announceText = SimplyAnnounce(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['ChooseKeyword'].search(activeAutoscript):     announceText = ChooseKeyword(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['UseCustomAbility'].search(activeAutoscript):  announceText = UseCustomAbility(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['PsiX'].search(activeAutoscript):              announceText = PsiX(activeAutoscript, announceText, card, targetC, n = X)
         elif regexHooks['SetVarX'].search(activeAutoscript):           SetVarX(activeAutoscript, announceText, card, targetC, n = X) # Setting a variable does not change the announcement text.
         else: timesNothingDone += 1
         debugNotify("<<< useAbility() choice. TXT = {}".format(announceText), 3) # Debug
         if announceText == 'ABORT': 
            autoscriptCostUndo(card, selectedAutoscripts[0]) # If nothing was done, try to undo. The first item in selectedAutoscripts[] contains the cost.
            gatheredCardList = False
            return
         if failedRequirement: break # If part of an AutoAction could not pay the cost, we stop the rest of it.
      if announceText.endswith(' in order to'): # If our text annouce ends with " to", it means that nothing happened. Try to undo and inform player.
         autoscriptCostUndo(card, selectedAutoscripts[0])
         notify("{} but there was nothing to do.".format(announceText[:-len(' in order to')]))
      elif announceText.endswith(' and'):
         announceText = announceText[:-len(' and')] # If for some reason we end with " and" (say because the last action did nothing), we remove it.
      else: # If we did something and everything finished as expected, then take the costs.
         if re.search(r"T1:", selectedAutoscripts[0]): intTrashCard(card, fetchProperty(card,'Stat'), "free", silent = True)
      if me.Credits != startingCreds: announceText = announceText + " (New total: {})".format(uniCredit(me.Credits)) # If we spent money during this script execution, we want to point out the new player's credit total.
      if iter == len(AutoscriptsList) - 1: # If this is the last script in the list, then we always announce the script we're running (We reduce by 1 because iterators always start as '0')
         debugNotify("Entering last notification", 2)
         if prev_announceText == 'NULL': # If it's NULL it's the only  script we run in this loop, so we just announce.
            notify("{}.".format(announceText)) # Finally announce what the player just did by using the concatenated string.
         else: # If it's not NULL, then there was a script run last time, so we check to see if it's a duplicate
            if prev_announceText == announceText: # If the previous script had the same notification output as the current one, we merge them.
               multiCount += 1
               notify("({}x) {}.".format(multiCount,announceText))
            else: # If the previous script did not have the same output as the current one, we announce them both together.
               if multiCount > 1: notify("({}x) {}.".format(multiCount,prev_announceText)) # If there were multiple versions of the last script used, announce them along with how many there were
               else: notify("{}.".format(prev_announceText))
               notify("{}.".format(announceText)) # Finally we announce the current script's concatenated notification.
      else: #if it's not the last script we run, then we just check if we should announce the previous script or just add another replication.
         debugNotify("Entering notification grouping check", 2)
         if prev_announceText == 'NULL': # If it's null, it's the first script we run in this loop...
            multiCount += 1 # ...so we don't announce but rather increase a counter and and just move to the next script, in case it's a duplicate announcement.
            prev_announceText = announceText # We also set the variable we're going to check in the next iteration, to see if it's a duplicate announcement.
         else:
            if prev_announceText == announceText: # If the previous script had the same notification output as the current one...
               multiCount += 1 # ...we merge them and continue without announcing.
            else: # If the previous script did not have the same notification output as the current one, we announce the previous one.
               if multiCount > 1: notify("({}x) {}.".format(multiCount,prev_announceText)) # If there were multiple versions of the last script used, announce them along with how many there were
               else: notify("{}.".format(prev_announceText)) 
               multiCount = 1 # We reset the counter so that we start counting how many duplicates of the current script we're going to have in the future.
               prev_announceText = announceText # And finally we reset the variable holding the previous script.
      chkNoisy(card)
      gatheredCardList = False  # We set this variable to False, so that reduceCost() calls from other functions can start scanning the table again.
      if announceText != 'ABORT' and CardAction: autoscriptOtherPlayers('CardAction', card)

#------------------------------------------------------------------------------
# Other Player trigger
#------------------------------------------------------------------------------
   
def autoscriptOtherPlayers(lookup, origin_card = Identity, count = 1): # Function that triggers effects based on the opponent's cards.
# This function is called from other functions in order to go through the table and see if other players have any cards which would be activated by it.
# For example a card that would produce credits whenever a trace was attempted. 
   if not Automations['Triggers']: return
   debugNotify(">>> autoscriptOtherPlayers() with lookup: {}".format(lookup)) #Debug
   debugNotify("origin_card = {}".format(origin_card), 3) #Debug
   if not Automations['Play, Score and Rez']: return # If automations have been disabled, do nothing.
   for card in table:
      debugNotify('Checking {}'.format(card), 2) # Debug
      if not card.isFaceUp: continue # Don't take into accounts cards that are not rezzed.
      if card.highlight == InactiveColor: continue # We don't take into account inactive cards.
      costText = '{} activates {} to'.format(card.controller, card) 
      Autoscripts = CardsAS.get(card.model,'').split('||')
      debugNotify("{}'s AS: {}".format(card,Autoscripts), 4) # Debug
      autoScriptSnapshot = list(Autoscripts)
      for autoS in autoScriptSnapshot: # Checking and removing anything other than whileRezzed or whileScored.
         if not re.search(r'while(Rezzed|Scored|Running|Installed|InPlay)', autoS): 
            debugNotify("Card does not have triggered ability while in play. Aborting", 2) #Debug
            Autoscripts.remove(autoS)
         if not chkRunningStatus(autoS): Autoscripts.remove(autoS) # If the script only works while running a specific server, and we're not, then abort.
      if len(Autoscripts) == 0: continue
      for autoS in Autoscripts:
         debugNotify('Checking autoS: {}'.format(autoS), 2) # Debug
         if not re.search(r'{}'.format(lookup), autoS): 
            debugNotify("lookup: {} not found in CardScript. Aborting".format(lookup))
            continue # Search if in the script of the card, the string that was sent to us exists. The sent string is decided by the function calling us, so for example the ProdX() function knows it only needs to send the 'GeneratedSpice' string.
         if chkPlayer(autoS, card.controller,False) == 0: continue # Check that the effect's origninator is valid.
         if not ifHave(autoS,card.controller,silent = True): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if re.search(r'whileScored',autoS) and card.controller.getGlobalVariable('ds') != 'corp': continue # If the card is only working while scored, then its controller has to be the corp.
         if chkTagged(autoS, True) == 'ABORT': continue
         if not chkRunStatus(autoS): continue
         if not checkCardRestrictions(gatherCardProperties(origin_card), prepareRestrictions(autoS, 'type')): continue #If we have the '-type' modulator in the script, then need ot check what type of property it's looking for
         if not checkSpecialRestrictions(autoS,origin_card): continue #If we fail the special restrictions on the trigger card, we also abort.
         if re.search(r'onlyOnce',autoS) and oncePerTurn(card, silent = True, act = 'automatic') == 'ABORT': continue # If the card's ability is only once per turn, use it or silently abort if it's already been used
         if re.search(r'onTriggerCard',autoS): targetCard = [origin_card] # if we have the "-onTriggerCard" modulator, then the target of the script will be the original card (e.g. see Grimoire)
         elif re.search(r'AutoTargeted',autoS): targetCard = findTarget(autoS)
         else: targetCard = None
         debugNotify("Automatic Autoscripts: {}".format(autoS), 2) # Debug
         #effect = re.search(r'\b([A-Z][A-Za-z]+)([0-9]*)([A-Za-z& ]*)\b([^:]?[A-Za-z0-9_&{} -]*)', autoS)
         #passedScript = "{}".format(effect.group(0))
         #confirm('effects: {}'.format(passedScript)) #Debug
         if regexHooks['CustomScript'].search(autoS):
            customScriptResult = CustomScript(card,'USE',origin_card, lookup)
            if customScriptResult == 'CLICK USED': autoscriptOtherPlayers('CardAction', card)  # Some cards just have a fairly unique effect and there's no use in trying to make them work in the generic framework.
            if customScriptResult == 'ABORT': break
         elif regexHooks['GainX'].search(autoS):
            gainTuple = GainX(autoS, costText, card, targetCard, notification = 'Automatic', n = count)
            if gainTuple == 'ABORT': break
         elif regexHooks['TokensX'].search(autoS): 
            if TokensX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['TransferX'].search(autoS): 
            if TransferX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['InflictX'].search(autoS): 
            remoteCall(fetchCorpPL(),'InflictX',[autoS, costText, card, targetCard, 'Automatic', count]) # We always have the corp itself do the damage
            #if InflictX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['DrawX'].search(autoS):
            if DrawX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['ModifyStatus'].search(autoS):
            if ModifyStatus(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['SetVarX'].search(autoS):
            if SetVarX(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
         elif regexHooks['UseCustomAbility'].search(autoS):
            if UseCustomAbility(autoS, costText, card, targetCard, notification = 'Automatic', n = count) == 'ABORT': break
   debugNotify("<<< autoscriptOtherPlayers()", 3) # Debug

#------------------------------------------------------------------------------
# Start/End of Turn/Run trigger
#------------------------------------------------------------------------------
   
def atTimedEffects(Time = 'Start'): # Function which triggers card effects at the start or end of the turn.
   mute()
   debugNotify(">>> atTimedEffects() at time: {}".format(Time)) #Debug
   global failedRequirement
   failedRequirement = False
   if not Automations['Start/End-of-Turn']: return
   TitleDone = False
   AlternativeRunResultUsed = False # Used for SuccessfulRun effects which replace the normal effect of running a server. If set to True, then no more effects on that server will be processed (to avoid 2 bank jobs triggering at the same time for example).
   X = 0
   tableCards = sortPriority([card for card in table if card.highlight != InactiveColor and card.highlight != RevealedColor])
   inactiveCards = [card for card in table if card.highlight == InactiveColor or card.highlight == RevealedColor]
   # tableCards.extend(inactiveCards) # Nope, we don't check inactive cards anymore. If they were inactive at the start of the turn, they won't trigger (See http://boardgamegeek.com/article/11686680#11686680)
   for card in tableCards:
      #if card.controller != me: continue # Obsoleted. Using the chkPlayer() function below
      if card.highlight == InactiveColor or card.highlight == RevealedColor: 
         debugNotify("Rejecting {} Because highlight == {}".format(card, card.highlight), 4)
         continue
      if not card.isFaceUp: continue
      Autoscripts = CardsAS.get(card.model,'').split('||')
      for autoS in Autoscripts:
         debugNotify("Processing {} Autoscript: {}".format(card, autoS), 3)
         if Time == 'Run': effect = re.search(r'at(Run)Start:(.*)', autoS) # Putting Run in a group, only to retain the search results groupings later
         elif Time == 'JackOut': effect = re.search(r'at(JackOut):(.*)', autoS) # Same as above
         elif Time == 'SuccessfulRun': effect = re.search(r'at(SuccessfulRun):(.*)', autoS) # Same as above
         elif Time == 'PreStart' or Time == 'PreEnd': effect = re.search(r'atTurn(PreStart|PreEnd):(.*)', autoS)
         else: effect = re.search(r'atTurn(Start|End):(.*)', autoS) #Putting "Start" or "End" in a group to compare with the Time variable later
         if not effect: 
            debugNotify("Not effect Regex found. Aborting")
            continue
         debugNotify("Time maches. Script triggers on: {}".format(effect.group(1)), 3)
         if re.search(r'-ifSuccessfulRun', autoS):
            if Time == 'SuccessfulRun' or (Time == 'JackOut' and getGlobalVariable('SuccessfulRun') == 'True'): #If we're looking only for successful runs, we need the Time to be a successful run or jackout period.
               requiredTarget = re.search(r'-ifSuccessfulRun([A-Za-z&]+)', autoS) # We check what the script requires to be the successful target
               if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
               else: 
                  currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
                  currentRunTarget = currentRunTargetRegex.group(1)
               if debugVerbosity >= 2: 
                  if requiredTarget and currentRunTargetRegex: notify("!!! Regex requiredTarget: {}\n!!! currentRunTarget: {}".format(requiredTarget.groups(),currentRunTarget))
                  else: notify ("No requiredTarget or currentRunTarget regex match :(")
               if requiredTarget.group(1) == 'Any': pass # -ifSuccessfulRunAny means we run the script on any successful run (e.g. Desperado)
               elif requiredTarget.group(1) == currentRunTarget: pass # If the card requires a successful run on a server that the global variable points that we were running at, we can proceed.
               else: continue # If none of the above, it means the card script is not triggering for this server.
               debugNotify("All checked OK", 3)
            else: continue
         if re.search(r'-ifUnsuccessfulRun', autoS):
            if Time == 'JackOut' and getGlobalVariable('SuccessfulRun') != 'True': #If we're looking only for unsuccessful runs, we need the Time to be a jackout without a successful run shared var..
               requiredTarget = re.search(r'-ifUnsuccessfulRun([A-Za-z&]+)', autoS) # We check what the script requires to be the unsuccessful target
               if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
               else: 
                  currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
                  currentRunTarget = currentRunTargetRegex.group(1)
               if debugVerbosity >= 2: 
                  if requiredTarget and currentRunTargetRegex: notify("!!! Regex requiredTarget: {}\n!!! currentRunTarget: {}".format(requiredTarget.groups(),currentRunTarget))
                  else: notify ("No requiredTarget or currentRunTarget regex match :(")
               if requiredTarget.group(1) == 'Any': pass # -ifSuccessfulRunAny means we run the script on any successful run (e.g. Desperado)
               elif requiredTarget.group(1) == currentRunTarget: pass # If the card requires a successful run on a server that the global variable points that we were running at, we can proceed.
               else: continue # If none of the above, it means the card script is not triggering for this server.
               debugNotify("All checked OK", 3)
            else: continue
         if chkPlayer(effect.group(2), card.controller,False) == 0: continue # Check that the effect's origninator is valid. 
         if not ifHave(autoS,card.controller,silent = True): continue # If the script requires the playet to have a specific counter value and they don't, do nothing.
         if not checkOrigSpecialRestrictions(autoS,card): continue
         if not chkRunStatus(autoS): continue
         if chkTagged(autoS, True) == 'ABORT': continue
         if effect.group(1) != Time: continue # If the effect trigger we're checking (e.g. start-of-run) does not match the period trigger we're in (e.g. end-of-turn)
         debugNotify("split Autoscript: {}".format(autoS), 3)
         if debugVerbosity >= 2 and effect: notify("!!! effects: {}".format(effect.groups()))
         if re.search(r'excludeDummy', autoS) and card.highlight == DummyColor: continue
         if re.search(r'onlyforDummy', autoS) and card.highlight != DummyColor: continue
         if re.search(r'isAlternativeRunResult', effect.group(2)) and AlternativeRunResultUsed: continue # If we're already used an alternative run result and this card has one as well, ignore it
         if re.search(r'onlyOnce',autoS) and oncePerTurn(card, silent = True, act = 'dryRun') == 'ABORT': continue
         if re.search(r'restrictionMarker',autoS) and chkRestrictionMarker(card, autoS, silent = True, act = 'dryRun') == 'ABORT': continue
         if re.search(r'isOptional', effect.group(2)):
            extraCountersTXT = '' 
            for cmarker in card.markers: # If the card has any markers, we mention them do that the player can better decide which one they wanted to use (e.g. multiple bank jobs)
               extraCountersTXT += " {}x {}\n".format(card.markers[cmarker],cmarker[0])
            if extraCountersTXT != '': extraCountersTXT = "\n\nThis card has the following counters on it\n" + extraCountersTXT
            if not confirm("{} can have its optional ability take effect at this point. Do you want to activate it?{}".format(fetchProperty(card, 'name'),extraCountersTXT)): continue         
         if re.search(r'isAlternativeRunResult', effect.group(2)): AlternativeRunResultUsed = True # If the card has an alternative result to the normal access for a run, mark that we've used it.         
         if re.search(r'onlyOnce',autoS) and oncePerTurn(card, silent = True, act = 'automatic') == 'ABORT': continue
         if re.search(r'restrictionMarker',autoS) and chkRestrictionMarker(card, autoS, silent = True, act = 'automatic') == 'ABORT': continue
         splitAutoscripts = effect.group(2).split('$$')
         for passedScript in splitAutoscripts:
            targetC = findTarget(passedScript)
            if re.search(r'Targeted', passedScript) and len(targetC) == 0: 
               debugNotify("Needed target but have non. Aborting")
               continue # If our script requires a target and we can't find any, do nothing.
            if not TitleDone: 
               debugNotify("Preparing Title")
               title = None
               if Time == 'Run': title = "{}'s Start-of-Run Effects".format(me)
               elif Time == 'JackOut': title = "{}'s Jack-Out Effects".format(me)
               elif Time == 'SuccessfulRun': title = "{}'s Successful Run Effects".format(me)
               elif Time != 'PreStart' and Time != 'PreEnd': title = "{}'s {}-of-Turn Effects".format(me,effect.group(1))
               if title: notify("{:=^36}".format(title))
            TitleDone = True
            debugNotify("passedScript: {}".format(passedScript), 2)
            if card.highlight == DummyColor: announceText = "{}'s lingering effects:".format(card)
            else: announceText = "{} triggers to".format(card)
            if regexHooks['GainX'].search(passedScript):
               gainTuple = GainX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if gainTuple == 'ABORT': break
               X = gainTuple[1] 
            elif regexHooks['TransferX'].search(passedScript):
               if TransferX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['DrawX'].search(passedScript):
               if DrawX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['RollX'].search(passedScript):
               rollTuple = RollX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if rollTuple == 'ABORT': break
               X = rollTuple[1] 
            elif regexHooks['TokensX'].search(passedScript):
               if TokensX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['InflictX'].search(passedScript):
               if InflictX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['RetrieveX'].search(passedScript):
               retrieveTuple = RetrieveX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if retrieveTuple == 'ABORT': return
               X = len(retrieveTuple[1])
            elif regexHooks['ModifyStatus'].search(passedScript):
               if ModifyStatus(passedScript, announceText, card, targetC, notification = 'Automatic', n = X) == 'ABORT': break
            elif regexHooks['DiscardX'].search(passedScript): 
               discardTuple = DiscardX(passedScript, announceText, card, targetC, notification = 'Automatic', n = X)
               if discardTuple == 'ABORT': break
               X = discardTuple[1] 
            elif regexHooks['RequestInt'].search(passedScript): 
               numberTuple = RequestInt(passedScript, announceText, card) # Returns like reshuffleX()
               if numberTuple == 'ABORT': break
               X = numberTuple[1] 
            elif regexHooks['SimplyAnnounce'].search(passedScript):
               SimplyAnnounce(passedScript, announceText, card, notification = 'Automatic', n = X)
            elif regexHooks['SetVarX'].search(passedScript):
               SetVarX(passedScript, announceText, card, notification = 'Automatic', n = X)
            elif regexHooks['CustomScript'].search(passedScript): 
               customScriptResult = CustomScript(card, Time, original_action = Time)
               if customScriptResult == 'CLICK USED': autoscriptOtherPlayers('CardAction', card)   # Some cards (I.e. Collective) just have a fairly unique effect and there's no use in trying to make them work in the generic framework.
               if customScriptResult == 'ABORT': break
               if customScriptResult == 'ALTERNATIVE RUN': AlternativeRunResultUsed = True # Custom scripts might introduce alt-run results which need to stop normal access.
            if failedRequirement: break # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.
   markerEffects(Time) 
   ASVarEffects(Time) 
   CustomEffects(Time)
   if me.counters['Credits'].value < 0: 
      if Time == 'Run': notify(":::Warning::: {}'s Start-of-run effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      elif Time == 'JackOut': notify(":::Warning::: {}'s Jacking-Out effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      elif Time == 'SuccessfulRun': notify(":::Warning::: {}'s Successful Run effects cost more Credits than {} had in their Credit Pool!".format(me,me))
      else: notify(":::Warning::: {}'s {}-of-turn effects cost more Credits than {} had in their Credit Pool!".format(me,Time,me))
   if ds == 'corp' and Time =='Start': draw(me.piles['R&D/Stack'])
   if Time == 'SuccessfulRun' and not AlternativeRunResultUsed: # If we have a successful Run and no alternative effect was used, we ask the user if they want to automatically use one of the standard ones.
      if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
      else: 
         currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
         currentRunTarget = currentRunTargetRegex.group(1)
      if currentRunTarget == 'HQ' and confirm("Rerouting to auth.level 9 corporate grid...OK\
                                             \nAuthenticating secure credentials...OK\
                                             \nDecrypting Home Folder...OK\
                                           \n\nAccess to HQ Granted!\
                                             \nWelcome back Err:::[Segmentation Fault]. Would you like to see today's priority item? \
                                           \n\n============================\
                                             \nAccess HQ? Y/n:"):
         HQaccess(silent = True)
      if currentRunTarget == 'R&D' and confirm("Processing Security Token...OK.\
                                              \nAccess to R&D files authorized for user {}.\
                                            \n\n============================\
                                              \nProceed to R&D files? Y/n:".format(me.name)):
         RDaccessX()
      if currentRunTarget == 'Archives' and confirm("Authorization for user {} processed.\
                                                   \nDecrypting Archive Store...OK.\
                                                 \n\n============================\
                                                   \nRetrieve Archives? Y/n:".format(me.name)):
         ARCscore()
   if TitleDone: notify(":::{:=^30}:::".format('='))   
   debugNotify("<<< atTimedEffects()", 3) # Debug

#------------------------------------------------------------------------------
# Post-Trace/Psi Trigger
#------------------------------------------------------------------------------

def executePostEffects(card,Autoscript,count = 0,type = 'Trace'):
   debugNotify(">>> executePostEffects(){}".format(extraASDebug(Autoscript))) #Debug
   global failedRequirement
   failedRequirement = False
   X = count # The X Starts as the "count" passed variable, which in traces is the difference between the corp's trace and the runner's link
   Autoscripts = Autoscript.split('||')
   for autoS in Autoscripts:
      selectedAutoscripts = autoS.split('++')
      if debugVerbosity >= 2: notify ('selectedAutoscripts: {}'.format(selectedAutoscripts)) # Debug
      for passedScript in selectedAutoscripts: X = redirect(passedScript, card, "{}'s {} succeeds to".format(card,type), 'Quick', X)
      if failedRequirement: break # If one of the Autoscripts was a cost that couldn't be paid, stop everything else.
         
#------------------------------------------------------------------------------
# Remote player script execution
#------------------------------------------------------------------------------
      
def remoteAutoscript(card = None, Autoscript = ''):
   debugNotify('>>> remoteAutoscript')
   debugNotify("Autoscript sent: {}".format(Autoscript))
   mute()
   if card: storeProperties(card, True)
   if re.search(r'-isOptional', Autoscript):
      if not confirm("The runner has accessed {} and you can choose to activate it at this point. Do you want to do so?".format(fetchProperty(card, 'name'))):
         notify("{} opts not to activate {}'s optional ability".format(me,card))
         return 'ABORT'
      else: notify("{} activates {}'s ability".format(me,card))
   selectedAutoscripts = Autoscript.split('$$')
   debugNotify ('selectedAutoscripts: {}'.format(selectedAutoscripts)) # Debug
   X = 0
   for passedScript in selectedAutoscripts: 
      X = redirect(passedScript, card, "{} triggers to".format(card), 'Quick', X)
      if X == 'ABORT': return
   debugNotify('<<< remoteAutoscript')

#------------------------------------------------------------------------------
# Core Commands redirect
#------------------------------------------------------------------------------
      
def redirect(Autoscript, card, announceText = None, notificationType = 'Quick', X = 0):
   debugNotify(">>> redirect(){}".format(extraASDebug(Autoscript))) #Debug
   if re.search(r':Pass\b', Autoscript): return X # Pass is a simple command of doing nothing ^_^
   targetC = findTarget(Autoscript)
   debugNotify("card.owner = {}".format(card.owner),2)
   targetPL = ofwhom(Autoscript,card.owner) # So that we know to announce the right person the effect, affects.
   if not announceText: announceText = "{} uses {}'s ability to".format(targetPL,card) 
   debugNotify(" targetC: {}. Notification Type = {}".format(targetC,notificationType), 3) # Debug
   if regexHooks['GainX'].search(Autoscript):
      gainTuple = GainX(Autoscript, announceText, card, notification = notificationType, n = X)
      if gainTuple == 'ABORT': return 'ABORT'
      X = gainTuple[1] 
   elif regexHooks['CreateDummy'].search(Autoscript): 
      if CreateDummy(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['DrawX'].search(Autoscript): 
      if DrawX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['TokensX'].search(Autoscript): 
      if TokensX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['RollX'].search(Autoscript): 
      rollTuple = RollX(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
      if rollTuple == 'ABORT': return 'ABORT'
      X = rollTuple[1] 
   elif regexHooks['RequestInt'].search(Autoscript): 
      numberTuple = RequestInt(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
      if numberTuple == 'ABORT': return 'ABORT'
      X = numberTuple[1] 
   elif regexHooks['DiscardX'].search(Autoscript): 
      discardTuple = DiscardX(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
      if discardTuple == 'ABORT': return 'ABORT'
      X = discardTuple[1] 
   elif regexHooks['RunX'].search(Autoscript): 
      if RunX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['TraceX'].search(Autoscript): 
      if TraceX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['ReshuffleX'].search(Autoscript): 
      reshuffleTuple = ReshuffleX(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
      if reshuffleTuple == 'ABORT': return 'ABORT'
      X = reshuffleTuple[1]
   elif regexHooks['ShuffleX'].search(Autoscript): 
      if ShuffleX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['ChooseKeyword'].search(Autoscript): 
      if ChooseKeyword(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['InflictX'].search(Autoscript): 
      if InflictX(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['ModifyStatus'].search(Autoscript): 
      if ModifyStatus(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   elif regexHooks['SimplyAnnounce'].search(Autoscript):
      SimplyAnnounce(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
   elif regexHooks['SetVarX'].search(Autoscript):
      SetVarX(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
   elif regexHooks['PsiX'].search(Autoscript):
      PsiX(Autoscript, announceText, card, targetC, notification = notificationType, n = X)
   elif regexHooks['UseCustomAbility'].search(Autoscript):
      if UseCustomAbility(Autoscript, announceText, card, targetC, notification = notificationType, n = X) == 'ABORT': return 'ABORT'
   else: debugNotify(" No regexhook match! :(") # Debug
   debugNotify("Loop for scipt {} finished".format(Autoscript), 2)
   debugNotify("<<< redirect with X = {}".format(X))
   return X

#------------------------------------------------------------------------------
# Core Commands
#------------------------------------------------------------------------------
   
def GainX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0, actionType = 'USE'): # Core Command for modifying counters or global variables
   debugNotify(">>> GainX(){}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("notification = {}".format(notification), 3)
   if targetCards is None: targetCards = []
   global lastKnownNrClicks
   gain = 0
   extraText = ''
   reduction = 0
   exactFail = False # A Variable that changes the notification if the cost needs to be paid exact, but the target player does not have enough counters.
   action = re.search(r'\b(Gain|Lose|SetTo)([0-9]+)([A-Z][A-Za-z &]+)-?', Autoscript)
   debugNotify("action groups: {}. Autoscript: {}".format(action.groups(0),Autoscript), 2) # Debug
   actiontypeRegex = re.search(r'actiontype([A-Z]+)',Autoscript) # This is used by some scripts so that they do not use the triggered action as the type of action that triggers the effect. For example, Draco's ability is not a "Rez" action and thus its cost is not affected by card that affect ICE rez costs, like Project Braintrust
   if actiontypeRegex: actionType = actiontypeRegex.group(1)
   gain += num(action.group(2))
   targetPL = ofwhom(Autoscript, card.owner)
   if targetPL != me: 
      otherTXT = ' force {} to'.format(targetPL)
      if action.group(1) == 'Lose': actionType = 'Force'
   else: otherTXT = ''
   if re.search(r'ifTagged', Autoscript) and targetPL.Tags == 0:
      whisper("Your opponent needs to be tagged to use this action")
      return 'ABORT'
   multiplier = per(Autoscript, card, n, targetCards) # We check if the card provides a gain based on something else, such as favour bought, or number of dune fiefs controlled by rivals.
   debugNotify("GainX() after per", 3) #Debug
   if action.group(1) == 'Lose': 
      if action.group(3) == 'Credits' or action.group(3) == 'Agenda Points' or action.group(3) == 'Clicks' or action.group(3) == 'MU' or action.group(3) == 'Base Link' or action.group(3) == 'Bad Publicity' or action.group(3) == 'Tags' or action.group(3) == 'Hand Size':
         overcharge = (gain * multiplier) - targetPL.counters[action.group(3)].value  # we use this to calculate how much of the requested LoseX was used.
         debugNotify(" We have an overcharge of {}".format(overcharge), 4)
         if overcharge < 0: overcharge = 0 # But if the overcharge is 0 or less, it means that all the loss could be taken out.
      else: overcharge = 0
      gain *= -1
      debugNotify(" overcharge = {}\n#### Gain = {}.\n #### Multiplier = {}.".format(overcharge,gain,multiplier), 2)
   if re.search(r'ifNoisyOpponent', Autoscript) and targetPL.getGlobalVariable('wasNoisy') != '1': return announceText # If our effect only takes place when our opponent has been noisy, and they haven't been, don't do anything. We return the announcement so that we don't crash the parent function expecting it
   gainReduce = findCounterPrevention(gain * multiplier, action.group(3), targetPL) # If we're going to gain counter, then we check to see if we have any markers which might reduce the cost.
   #confirm("multiplier: {}, gain: {}, reduction: {}".format(multiplier, gain, gainReduce)) # Debug
   if re.match(r'Credits', action.group(3)): # Note to self: I can probably comprress the following, by using variables and by putting the counter object into a variable as well.
      if action.group(1) == 'SetTo': targetPL.counters['Credits'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      if gain == -999: targetPL.counters['Credits'].value = 0
      else: 
         debugNotify(" Checking Cost Reduction", 2)
         reversePlayer = actionType == 'Force' # If the loss is forced on another player, we reverse the recude cost player checking effects, to check for their reduction effects and not ours
         if re.search(r'isCost', Autoscript) and action.group(1) == 'Lose':
            reduction = reduceCost(card, actionType, gain * multiplier, reversePlayer = reversePlayer)
         elif action.group(1) == 'Lose':
            if targetPL == me: actionType = 'None' # If we're losing money from a card effect that's not a cost, we considered a 'use' cost.
            reduction = reduceCost(card, actionType, gain * multiplier, reversePlayer = reversePlayer) # If the loss is not a cost, we still check for generic reductions such as BP
         if action.group(1) == 'Lose' and re.search(r'isExact', Autoscript) and targetPL.counters['Credits'].value < abs((gain * multiplier) + reduction): 
            exactFail = True
         else: 
            targetPL.counters['Credits'].value += (gain * multiplier) + reduction
            if reduction > 0: extraText = ' (Reduced by {})'.format(uniCredit(reduction))
            elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      if targetPL.counters['Credits'].value < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         elif re.search(r'isPenalty', Autoscript): pass #If an action is marked as penalty, it means that the value can go negative and the player will have to recover that amount.
         else: targetPL.counters['Credits'].value = 0
   elif re.match(r'Agenda Points', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.counters['Agenda Points'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      if gain == -999: targetPL.counters['Agenda Points'].value = 0
      else: targetPL.counters['Agenda Points'].value += (gain * multiplier) - gainReduce
      if me.counters['Agenda Points'].value >= 7 or (getSpecial('Identity',fetchCorpPL()).name == "Harmony Medtech" and me.counters['Agenda Points'].value >= 6): 
         notify("{} wins the game!".format(me))
         reportGame()      
      if targetPL.counters['Agenda Points'].value < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         #Agenda Points can go negative
   elif re.match(r'Clicks', action.group(3)): 
      if action.group(1) == 'SetTo': 
         targetPL.Clicks = 0 # If we're setting to a specific value, we wipe what it's currently.
         lastKnownNrClicks = 0
      if gain == -999: 
         targetPL.Clicks = 0
         lastKnownNrClicks = 0
      else: 
         if action.group(1) == 'Lose' and re.search(r'isExact', Autoscript) and targetPL.Clicks < abs((gain * multiplier) - gainReduce): 
            exactFail = True
         else:
            debugNotify("Proceeding to gain/lose clicks. Had {} Clicks. Modification is {}".format(targetPL.Clicks,(gain * multiplier) - gainReduce), 2)
            targetPL.Clicks += (gain * multiplier) - gainReduce
            lastKnownNrClicks += (gain * multiplier) - gainReduce # We also increase the offset, to make sure we announce the correct current action.
   elif re.match(r'MU', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.MU = 0 # If we're setting to a specific value, we wipe what it's currently.
      else: targetPL.MU += (gain * multiplier) - gainReduce
      if targetPL.MU < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         elif re.search(r'isPenalty', Autoscript): pass #If an action is marked as penalty, it means that the value can go negative and the player will have to recover that amount.
         else: targetPL.MU = 0
   elif re.match(r'Base Link', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.counters['Base Link'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      else: targetPL.counters['Base Link'].value += (gain * multiplier) - gainReduce
      if targetPL.counters['Base Link'].value < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         elif re.search(r'isPenalty', Autoscript): pass #If an action is marked as penalty, it means that the value can go negative and the player will have to recover that amount.
         else: targetPL.counters['Base Link'].value = 0
      chkCloud() # After we modify player link, we check for enabled cloud connections.
   elif re.match(r'Bad Publicity', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.counters['Bad Publicity'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      if gain == -999: targetPL.counters['Bad Publicity'].value = 0
      else: 
         if action.group(1) == 'Lose' and re.search(r'isExact', Autoscript) and targetPL.counters['Bad Publicity'].value < abs((gain * multiplier)) - gainReduce: 
            exactFail = True
         else:
            targetPL.counters['Bad Publicity'].value += (gain * multiplier) - gainReduce
      if targetPL.counters['Bad Publicity'].value < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         elif re.search(r'isPenalty', Autoscript): pass #If an action is marked as penalty, it means that the value can go negative and the player will have to recover that amount.
         else: targetPL.counters['Bad Publicity'].value = 0
   elif re.match(r'Tags', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.Tags = 0 # If we're setting to a specific value, we wipe what it's currently.
      if gain == -999: targetPL.Tags = 0
      else: 
         if action.group(1) == 'Lose' and re.search(r'isExact', Autoscript) and targetPL.Tags < abs((gain * multiplier) - gainReduce): 
            exactFail = True
         else:
            targetPL.Tags += (gain * multiplier) - gainReduce
      if targetPL.Tags < 0: 
         if re.search(r'isCost', Autoscript): notify(":::Warning:::{} did not have enough {} to pay the cost of this action".format(targetPL,action.group(3)))
         elif re.search(r'isPenalty', Autoscript): pass #If an action is marked as penalty, it means that the value can go negative and the player will have to recover that amount.
         else: targetPL.Tags = 0
   elif re.match(r'Max Click', action.group(3)): 
      if action.group(1) == 'SetTo': modType = 'set to' 
      else: modType = 'increment' 
      modClicks(targetPL = targetPL, count = gain * multiplier, action = modType)
   elif re.match(r'Hand Size', action.group(3)): 
      if action.group(1) == 'SetTo': targetPL.counters['Hand Size'].value = 0 # If we're setting to a specific value, we wipe what it's currently.
      targetPL.counters['Hand Size'].value += gain * multiplier
   else: 
      whisper("Gain what?! (Bad autoscript)")
      return 'ABORT'
   debugNotify("Gainx() Finished counter manipulation", 2)
   if notification != 'Automatic': # Since the verb is in the middle of the sentence, we want it lowercase.
      if action.group(1) == 'Gain': 
         verb = 'gain'
      elif action.group(1) == 'Lose': 
         if re.search(r'isCost', Autoscript): verb = 'pay'
         else: verb = 'lose'
      else: 
         verb = 'set to'
   else: 
      verb = action.group(1) # Automatic notifications start with the verb, so it needs to be capitaliszed. 
   if abs(gain) == abs(999): total = 'all' # If we have +/-999 as the count, then this mean "all" of the particular counter.
   elif action.group(1) == 'Lose' and re.search(r'isCost', Autoscript): total = abs(gain * multiplier)
   elif action.group(1) == 'Lose' and not re.search(r'isPenalty', Autoscript): total = abs(gain * multiplier) - overcharge - reduction
   else: total = abs(gain * multiplier) - reduction# Else it's just the absolute value which we announce they "gain" or "lose"
   closureTXT = ASclosureTXT(action.group(3), total)
   if re.match(r'Credits', action.group(3)): 
      finalCounter = ' (new total: {})'.format(uniCredit(targetPL.Credits))
   else: 
      finalCounter = ''
   debugNotify("Gainx() about to announce", 2)
   if notification == 'Quick': 
      if exactFail: announceString = ":::WARNING::: {}'s ability failed to work because {} didn't have exactly {} {} to lose".format(card, targetPL, action.group(2), action.group(3))
      else: announceString = "{}{} {} {}{}{}".format(announceText, otherTXT, verb, closureTXT,extraText,finalCounter)
   else: 
      if exactFail: 
         announceString = announceText
         notify(":::WARNING::: {}'s ability failed to work because {} didn't have exactly {} {} to lose".format(card, targetPL, action.group(2), action.group(3)))
      else: announceString = "{}{} {} {}{}".format(announceText, otherTXT, verb, closureTXT,extraText)
   debugNotify("notification = {}".format(notification), 4)
   if notification and multiplier > 0: notify('--> {}.'.format(announceString))
   debugNotify("<<< Gain() total: {}".format(total), 3)
   return (announceString,total)
   
def TransferX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for converting tokens to counter values
   debugNotify(">>> TransferX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   #breakadd = 1
   total = 0
   totalReduce = 0
   targetCardlist = '' # A text field holding which cards are going to get tokens.
   if len(targetCards) == 0: targetCards.append(card) # If there's been to target card given, assume the target is the card itself.
   for targetCard in targetCards: targetCardlist += '{},'.format(targetCard)
   targetCardlist = targetCardlist.strip(',') # Re remove the trailing comma
   action = re.search(r'\bTransfer([0-9]+)([A-Za-z ]+)-?', Autoscript)
   if re.search(r'Credit',action.group(2)): destGroup = me.counters['Credits']
   elif re.search(r'Click',action.group(2)): destGroup = me.counters['Clicks']
   else:
      whisper(":::WARNING::: Not a valid transfer. Aborting!")
      return 'ABORT'
   debugNotify("!!! regex groups: {}".format(action.groups()), 3) #Debug   
   multiplier = per(Autoscript, card, n, targetCards, notification)   
   count = num(action.group(1)) * multiplier
   for targetCard in targetCards:
      foundMarker = findMarker(targetCard, action.group(2))
      if not foundMarker: 
         whisper("There was nothing to transfer from {}.".format(targetCard))
         continue
      if action.group(1) == '999':
         if targetCard.markers[foundMarker]: count = targetCard.markers[foundMarker]
         else: count = 0
      if targetCard.markers[foundMarker] < count: 
         if re.search(r'isCost', Autoscript):
            whisper("You must have at least {} {} on the card to take this action".format(action.group(1),action.group(2)))
            return 'ABORT'
         elif targetCard.markers[foundMarker] == 0 and notification: return 'ABORT'
      for transfer in range(count):
         if targetCard.markers[foundMarker] > 0: 
            transferReduce = findCounterPrevention(1, action.group(2), me) 
            targetCard.markers[foundMarker] -= 1
            if transferReduce: totalReduce += 1
            total += 1 - totalReduce
            destGroup.value += 1 - transferReduce
         else:
            #breakadd -= 1 # We decrease the transfer variable by one, to make sure we announce the correct total.
            break # If there's no more tokens to transfer, break out of the loop.
   #confirm("total: {}".format(total)) # Debug
   if total == 0 and totalReduce == 0: return 'ABORT' # If both totals are 0, it means nothing was generated, so there's no need to mention anything.
   if totalReduce: reduceTXT = " ({} forfeited)".format(totalReduce)
   else: reduceTXT = ''
   closureTXT = ASclosureTXT(action.group(2), total)
   if notification == 'Quick': announceString = "{} takes {}{}".format(announceText, closureTXT, reduceTXT)
   elif notification == 'Automatic': announceString = "{} Transfer {} to {}{}".format(announceText, closureTXT, me, reduceTXT)
   else: announceString = "{} take {} from {}{}".format(announceText, closureTXT, targetCardlist,reduceTXT)
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< TransferX()", 3)
   return announceString   

def TokensX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for adding tokens to cards
   debugNotify(">>> TokensX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   if len(targetCards) == 0: targetCards.append(card) # If there's been to target card given, assume the target is the card itself.
   #confirm("TokensX List: {}".format(targetCardlist)) # Debug
   foundKey = False # We use this to see if the marker used in the AutoAction is already defined.
   action = re.search(r'\b(Put|Remove|Refill|Use|Infect)([0-9]+)([A-Za-z: ]+)-?', Autoscript)
   #confirm("{}".format(action.group(3))) # Debug
   if action.group(3) in mdict: token = mdict[action.group(3)]
   else: # If the marker we're looking for it not defined, then either create a new one with a random color, or look for a token with the custom name we used above.
      if targetCards[0].markers:
         for key in targetCards[0].markers:
            #confirm("Key: {}\n\naction.group(3): {}".format(key[0],action.group(3))) # Debug
            if key[0] == action.group(3):
               foundKey = True
               token = key
      if not foundKey: # If no key is found with the name we seek, then create a new one with a random colour.
         #counterIcon = re.search(r'-counterIcon{([A-Za-z]+)}', Autoscript) # Not possible at the moment
         #if counterIcon and counterIcon.group(1) == 'plusOne':             # See https://github.com/kellyelton/OCTGN/issues/446
         #   token = ("{}".format(action.group(3)),"aa261722-e12a-41d4-a475-3cc1043166a7")         
         #else:
         rndGUID = rnd(1,8)
         token = ("{}".format(action.group(3)),"00000000-0000-0000-0000-00000000000{}".format(rndGUID)) #This GUID is one of the builtin ones
   debugNotify("Token = {}".format(token))
   count = num(action.group(2))
   multiplier = per(Autoscript, card, n, targetCards, notification)
   modtokens = count * multiplier
   if re.search(r'isCost', Autoscript): # If we remove tokens as a cost, then we do a dry run to see if we have enough tokens on the targeted cards available
                                        # This way we can stop the execution without actually removing any tokens
      dryRunAmount = 0 # We reset for the next loop
      for targetCard in targetCards: # First we do a dry-run for removing tokens.
         if targetCard.markers[token]: dryRunAmount += targetCard.markers[token]
         debugNotify("Added {} tokens to the pool ({}) from {} at pos {}".format(targetCard.markers[token],dryRunAmount,targetCard,targetCard.position))
      if dryRunAmount < modtokens and not (num(action.group(2)) == 999 and dryRunAmount > 0):
         debugNotify("Found {} tokens. Required {}. Aborting".format(dryRunAmount,modtokens))
         if notification != 'Automatic': delayed_whisper ("No enough tokens to remove. Aborting!") #Some end of turn effect put a special counter and then remove it so that they only run for one turn. This avoids us announcing that it doesn't have markers every turn.
         return 'ABORT'
   tokenAmount = 0  # We count the amount of token we've manipulated, to be used with the -isExactAmount modulator.
   modifiedCards = [] # A list which holds the cards whose tokens we modified ,so that we can announce only the right names.
   for targetCard in targetCards:
      for iter in range(modtokens): # We're removng the tokens 1 by 1, so we can stop once we reached an exact amount that we want.
         if (re.search(r'isExactAmount', Autoscript) or re.search(r'isCost', Autoscript)) and tokenAmount == modtokens: 
            debugNotify("Aborting loop because tokenAmount reached ({})".format(tokenAmount))
            break 
         # If we're modifying the tokens by an exact amount (cost is always this way), then we will stop manipulating tokens on all cards as soon as this amount it reached.
         # If we've accumulated the amount of tokens we need to manipulate, we stop removing any more.
         if action.group(1) == 'Remove':
            if not targetCard.markers[token]:
               #if not re.search(r'isSilent', Autoscript): delayed_whisper("There was nothing to remove.") 
               break
            else: targetCard.markers[token] -= 1 
         else:
            if action.group(1) == 'Refill' and targetCard.markers[token] and targetCard.markers[token] >= modtokens: break # If we're refilling the tokens and we've already exceeded that amount, we don't add more
            targetCard.markers[token] += 1
         tokenAmount += 1
         if targetCard not in modifiedCards: modifiedCards.append(targetCard)
   debugNotify("tokenAmount = {}".format(tokenAmount))
   if len(modifiedCards) == 1 and modifiedCards[0] == card: targetCardlist = ' on it'
   else: 
      targetCardlist = ' on' # A text field holding which cards are going to get tokens.
      for targetCard in modifiedCards:
         targetCardlist += ' {},'.format(targetCard)
   if num(action.group(2)) == 999: total = 'all'
   else: total = modtokens
   if re.search(r'isPriority', Autoscript): card.highlight = PriorityColor
   if action.group(1) == 'Refill': 
      if token[0] == 'Credit': 
         announceString = "{} {} to {}".format(announceText, action.group(1), uniRecurring(count * multiplier)) # We need a special announcement for refill, since it always needs to point out the max.
      else: 
         announceString = "{} {} to {} {}".format(announceText, action.group(1), count * multiplier, token[0]) # We need a special announcement for refill, since it always needs to point out the max.
   elif re.search(r'forfeitCounter:',action.group(3)):
      counter = re.search(r'forfeitCounter:(\w+)',action.group(3))
      if not victim or victim == me: announceString = '{} forfeit their next {} {}'.format(announceText,total,counter.group(1)) # If we're putting on forfeit counters, we don't announce it as an infection.
      else: announceString = '{} force {} to forfeit their next {} {}'.format(announceText, victim, total,counter.group(1))
   else: announceString = "{} {} {} {} counters{}".format(announceText, action.group(1).lower(), total, token[0],targetCardlist)
   if notification and modtokens != 0 and not re.search(r'isSilent', Autoscript): notify('--> {}.'.format(announceString))
   debugNotify("TokensX() String: {}".format(announceString), 2) #Debug
   debugNotify("<<< TokensX()", 3)
   if re.search(r'isSilent', Autoscript): return announceText # If it's a silent marker, we don't want to announce anything. Returning the original announceText will be processed by any receiving function as having done nothing.
   else: return announceString
 
def DrawX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> DrawX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   destiVerb = 'draw'
   action = re.search(r'\bDraw([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.owner)
   if targetPL != me: destiVerb = 'move'
   if re.search(r'-fromTrash', Autoscript): source = targetPL.piles['Heap/Archives(Face-up)']
   else: source = targetPL.piles['R&D/Stack']
   if re.search(r'-toStack', Autoscript): 
      destination = targetPL.piles['R&D/Stack']
      destiVerb = 'move'
   elif re.search(r'-toTrash', Autoscript):
      if targetPL.getGlobalVariable('ds') == 'corp': destination = targetPL.piles['Archives(Hidden)']
      else: destination = targetPL.piles['Heap/Archives(Face-up)']
      destiVerb = 'trash'   
   else: destination = targetPL.hand
   if destiVerb == 'draw' and ModifyDraw > 0 and not confirm("You have a card effect in play that modifies the amount of cards you draw. Do you want to continue as normal anyway?\n\n(Answering 'No' will abort this action so that you can prepare for the special changes that happen to your draw."): return 'ABORT'
   draw = num(action.group(1))
   if draw == 999:
      multiplier = 1
      if currentHandSize(targetPL) >= len(targetPL.hand): # Otherwise drawMany() is going to try and draw "-1" cards which somehow draws our whole deck except one card.
         count = drawMany(source, currentHandSize(targetPL) - len(targetPL.hand), destination, True) # 999 means we refresh our hand
      else: count = 0 
      #confirm("cards drawn: {}".format(count)) # Debug
   else: # Any other number just draws as many cards.
      multiplier = per(Autoscript, card, n, targetCards, notification)
      count = drawMany(source, draw * multiplier, destination, True)
   if targetPL == me:
      if destiVerb != 'trash': destPath = " to their {}".format(destination.name)
      else: destPath = ''
   else: 
      if destiVerb != 'trash': destPath = " to {}'s {}".format(targetPL,destination.name)
      else: destPath = ''
   debugNotify("About to announce.", 2)
   if count == 0: return announceText # If there are no cards, then we effectively did nothing, so we don't change the notification.
   if notification == 'Quick': announceString = "{} draws {} cards".format(announceText, count)
   elif targetPL == me: announceString = "{} {} {} cards from their {}{}".format(announceText, destiVerb, count, pileName(source), destPath)
   else: announceString = "{} {} {} cards from {}'s {}".format(announceText, destiVerb, count, targetPL, pileName(source), destPath)
   if notification and multiplier > 0: notify('--> {}.'.format(announceString))
   debugNotify("<<< DrawX()", 3)
   return announceString

def DiscardX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> DiscardX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bDiscard([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.owner)
   if targetPL != me: otherTXT = ' force {} to'.format(targetPL)
   else: otherTXT = ''
   discardNR = num(action.group(1))
   if discardNR == 999:
      multiplier = 1
      discardNR = len(targetPL.hand) # 999 means we discard our whole hand
   if re.search(r'-isRandom',Autoscript): # Any other number just discard as many cards at random.
      multiplier = per(Autoscript, card, n, targetCards, notification)
      count = handRandomDiscard(targetPL.hand, discardNR * multiplier, targetPL, silent = True)
      if re.search(r'isCost', Autoscript) and count < discardNR:
         whisper("You do not have enough cards in your hand to discard")
         return ('ABORT',0)
   else: # Otherwise we just discard the targeted cards from hand  
      multiplier = 1
      count = len(targetCards)
      if re.search(r'isCost', Autoscript) and count < discardNR:
         whisper("You do not have enough cards in your hand to discard")
         return ('ABORT',0)
      for targetC in targetCards: handDiscard(targetC, True)
      debugNotify("Finished discarding targeted cards from hand")
   if count == 0: 
      debugNotify("Exiting because count == 0")
      return (announceText,count) # If there are no cards, then we effectively did nothing, so we don't change the notification.
   if notification == 'Quick': announceString = "{} discards {} cards ({})".format(announceText, count, [c.name for c in targetCards])
   else: announceString = "{}{} discard {} cards ({}) from their hand".format(announceText,otherTXT, count,[c.name for c in targetCards])
   if notification and multiplier > 0: notify('--> {}.'.format(announceString))
   debugNotify("<<< DiscardX()", 3)
   return (announceString,count)
         
def ReshuffleX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # A Core Command for reshuffling a pile into the R&D/Stack and replenishing the pile with the same number of cards.
   debugNotify(">>> ReshuffleX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   mute()
   X = 0
   targetPL = ofwhom(Autoscript, card.owner)
   action = re.search(r'\bReshuffle([A-Za-z& ]+)', Autoscript)
   debugNotify("!!! regex: {}".format(action.groups())) # Debug
   if action.group(1) == 'HQ' or action.group(1) == 'Stack':
      namestuple = groupToDeck(targetPL.hand, targetPL , True) # We do a silent hand reshuffle into the deck, which returns a tuple
      X = namestuple[2] # The 3rd part of the tuple is how many cards were in our hand before it got shuffled.
   elif action.group(1) == 'Archives' or action.group(1) == 'Heap':
      if targetPL.getGlobalVariable('ds') == "corp": groupToDeck(targetPL.piles['Archives(Hidden)'], targetPL , True)
      namestuple = groupToDeck(targetPL.piles['Heap/Archives(Face-up)'], targetPL, True)    
   else: 
      whisper("Wat Group? [Error in autoscript!]")
      return 'ABORT'
   shuffle(targetPL.piles['R&D/Stack'])
   if notification == 'Quick': announceString = "{} shuffles their {} into their {}".format(announceText, namestuple[0], namestuple[1])
   else: announceString = "{} shuffle their {} into their {}".format(announceText, namestuple[0], namestuple[1])
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< ReshuffleX() return with X = {}".format(X), 3)
   return (announceString, X)

def ShuffleX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # A Core Command for shuffling a pile into the R&D/Stack
   debugNotify(">>> ShuffleX(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   mute()
   action = re.search(r'\bShuffle([A-Za-z& ]+)', Autoscript)
   targetPL = ofwhom(Autoscript, card.owner)
   if action.group(1) == 'Trash' or action.group(1) == 'Archives': pile = targetPL.piles['Heap/Archives(Face-up)']
   elif action.group(1) == 'Stack' or action.group(1) == 'R&D': pile = targetPL.piles['R&D/Stack']
   elif action.group(1) == 'Hidden Archives': pile = targetPL.piles['Archives(Hidden)']
   random = rnd(10,100) # Small wait (bug workaround) to make sure all animations are done.
   shuffle(pile)
   if notification == 'Quick': announceString = "{} shuffles their {}".format(announceText, pileName(pile))
   elif targetPL == me: announceString = "{} shuffle their {}".format(announceText, pileName(pile))
   else: announceString = "{} shuffle {}' {}".format(announceText, targetPL, pileName(pile))
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< ShuffleX()", 3)
   return announceString
   
def RollX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for rolling a Die
   debugNotify(">>> RollX(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   d6 = 0
   d6list = []
   result = 0
   action = re.search(r'\bRoll([0-9]+)Dice(-chk)?([1-6])?', Autoscript)
   multiplier = per(Autoscript, card, n, targetCards, notification)
   count = num(action.group(1)) * multiplier 
   for d in range(count):
      if d == 2: whisper("-- Please wait. Rolling {} dice...".format(count))
      if d == 8: whisper("-- A little while longer...")
      d6 = rolld6(silent = True)
      d6list.append(d6)
      if action.group(3): # If we have a chk modulator, it means we only increase our total if we hit a specific number.
         if num(action.group(3)) == d6: result += 1
      else: result += d6 # Otherwise we add all totals together.
      debugNotify("iter:{} with roll {} and total result: {}".format(d,d6,result), 2)
   if notification == 'Quick': announceString = "{} rolls {} on {} dice".format(announceText, d6list, count)
   else: announceString = "{} roll {} dice with the following results: {}".format(announceText,count, d6list)
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< RollX() with result: {}".format(result), 3)
   return (announceString, result)

def RequestInt(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> RequestInt(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bRequestInt(-Min)?([0-9]*)(-div)?([0-9]*)(-Max)?([0-9]*)(-Msg)?\{?([A-Za-z0-9?$&\(\) ]*)\}?', Autoscript)
   if debugVerbosity >= 2:
      if action: notify('!!! regex: {}'.format(action.groups()))
      else: notify("!!! No regex match :(")
   debugNotify("Checking for Min", 2)
   if action.group(2): 
      min = num(action.group(2))
      minTXT = ' (minimum {})'.format(min)
   else: 
      min = 0
      minTXT = ''
   debugNotify("Checking for Max", 2)
   if action.group(6): 
      max = num(action.group(6))
      minTXT += ' (maximum {})'.format(max)
   else: 
      max = None
   debugNotify("Checking for div", 2)
   if action.group(4): 
      div = num(action.group(4))
      minTXT += ' (must be a multiple of {})'.format(div)
   else: div = 1
   debugNotify("Checking for Msg", 2)
   if action.group(8): 
      message = action.group(8)
   else: message = "{}:\nThis effect requires that you provide an 'X'. What should that number be?{}".format(fetchProperty(card, 'name'),minTXT)
   number = min - 1
   debugNotify("About to ask", 2)
   while number < min or number % div or (max and number > max):
      number = askInteger(message,min)
      if number == None: 
         whisper("Aborting Function")
         return 'ABORT'
   debugNotify("<<< RequestInt() with return into = {}".format(number), 3)
   return (announceText, number) # We do not modify the announcement with this function.
   
def RunX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> RunX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bRun([A-Z][A-Za-z& ]+)', Autoscript)
   if debugVerbosity >= 2: 
      if action: notify("!!! Regex results: {}".format(action.groups()))
      else: notify("!!! No Regex match :(")
   if action.group(1) == 'End':
      playCorpEndSound()
      jackOut(silent = True)
      if notification == 'Quick': announceString = "{} end the run".format(announceText)
      else: announceString = "{} end the run".format(announceText)
   else:
      if action.group(1) == 'Generic':
         targets = findTarget('Targeted-atServer-isMutedTarget')
         if targets == []: # If the player has not targeted a server, then we ask them what they're targeting.
            debugNotify("No targets found. Asking", 3)
            choice = SingleChoice("Which server are you going to run at?\
                              \n\n(In the future you can target a server before you start a run and we will automatically pick that as the target)",\
                                  ['Remote Server','HQ','R&D','Archives'])
            if choice != None: # Just in case the player didn't just close the askInteger window.
               if choice == 0: targetServer = 'Remote'
               elif choice == 1: targetServer = 'HQ'
               elif choice == 2: targetServer = 'R&D'
               elif choice == 3: targetServer = 'Archives'
               else: return 'ABORT'
            else: return 'ABORT'
         else: # If the player has targeted a server before playing/using their card, then we just use that one
            debugNotify("Targeted Server found!", 3)
            if targets[0].name == 'Remote Server': targetServer = 'Remote'
            else: targetServer = targets[0].name
      else: 
         targetServer = action.group(1)
         if targetServer == 'Remote' and card.name == 'Remote Server': card.target(True) # If the player double clicked the remote server to start a run, then we target it, in order to allow an arrow to be painted.
      feint = re.search(r'-feintTo([A-Za-z&]+)', Autoscript)
      if feint:
         setGlobalVariable('feintTarget',feint.group(1)) # If the card script is feinting to a different fort, set a shared variable so that the corp knows it.
      runTarget = ' on {}'.format(targetServer)
      if intRun(0,targetServer,True) == 'ABORT': return 'ABORT'
      if notification == 'Quick': announceString = "{} starts a run{}".format(announceText, runTarget)
      else: announceString = "{} start a run{}".format(announceText, runTarget)
   if notification and not re.search(r'isSilent', Autoscript): notify('--> {}.'.format(announceString))
   debugNotify("<<< RunX()", 3)
   if re.search(r'isSilent', Autoscript): return announceText
   else: return announceString

def SimplyAnnounce(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> SimplyAnnounce(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bSimplyAnnounce{([A-Za-z0-9&,\. ]+)}', Autoscript)
   if debugVerbosity >= 2: #Debug
      if action: notify("!!! regex: {}".format(action.groups())) 
      else: notify("!!! regex failed :(") 
   if re.search(r'break',Autoscript) and re.search(r'subroutine',Autoscript): penaltyNoisy(card)
   if notification == 'Quick': announceString = "{} {}".format(announceText, action.group(1))
   else: announceString = "{} {}".format(announceText, action.group(1))
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< SimplyAnnounce()", 3)
   return announceString

def SetVarX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> SetVarX(){}".format(extraASDebug())) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bSetVar([A-Za-z0-9 ]+)-To([A-Za-z0-9 ]+)', Autoscript)
   if debugVerbosity >= 2: #Debug
      if action: notify("!!! regex: {}".format(action.groups()))
      else: notify("!!! regex failed :(") 
   ASVars = eval(getGlobalVariable('AutoScript Variables'))
   ASVars[action.group(1)] = action.group(2)
   setGlobalVariable('AutoScript Variables',str(ASVars))
   debugNotify("ASVars = {}".format(str(ASVars)),4)
   debugNotify("<<< SetVarX()", 3)
   return ''

def CreateDummy(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for creating dummy cards.
   debugNotify(">>> CreateDummy(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   global Stored_Name, Stored_Type, Stored_Cost, Stored_Keywords, Stored_AutoActions, Stored_autoScripts
   dummyCard = None
   action = re.search(r'\bCreateDummy[A-Za-z0-9_ -]*(-with)(?!onOpponent|-doNotTrash|-nonUnique)([A-Za-z0-9_ -]*)', Autoscript)
   if debugVerbosity >= 3 and action: notify('clicks regex: {}'.format(action.groups())) # debug
   targetPL = ofwhom(Autoscript, card.owner)
   for c in table:
      if c.model == card.model and c.controller == targetPL and c.highlight == DummyColor: dummyCard = c # We check if already have a dummy of the same type on the table.
   if not dummyCard or re.search(r'nonUnique',Autoscript): #Some create dummy effects allow for creating multiple copies of the same card model.
      if getSetting('Dummywarn',True) and re.search('onOpponent',Autoscript):
         if not confirm("This action creates an effect for your opponent and a way for them to remove it.\
                       \nFor this reason we've created a dummy card on the table and marked it with a special highlight so that you know that it's just a token.\
                     \n\nYou opponent can activate any abilities meant for them on the Dummy card. If this card has one, they can activate it by double clicking on the dummy. Very often, this will often remove the dummy since its effect will disappear.\
                     \n\nOnce the   dummy card is on the table, please right-click on it and select 'Pass control to {}'\
                     \n\nDo you want to see this warning again?".format(targetPL)): setSetting('Dummywarn',False)
      elif getSetting('Dummywarn',True):
         if not confirm("This card's effect requires that you trash it, but its lingering effects will only work automatically while a copy is in play.\
                       \nFor this reason we've created a dummy card on the table and marked it with a special highlight so that you know that it's just a token.\
                     \n\nSome cards provide you with an ability that you can activate after they're been trashed. If this card has one, you can activate it by double clicking on the dummy. Very often, this will often remove the dummy since its effect will disappear.\
                     \n\nDo you want to see this warning again?"): setSetting('Dummywarn',False)
      dummyCard = table.create(card.model, -680, 200 * playerside, 1) # This will create a fake card like the one we just created.
      dummyCard.highlight = DummyColor
      storeProperties(dummyCard)
      if re.search(r'onOpponent', Autoscript): passCardControl(dummyCard,findOpponent())
   #confirm("Dummy ID: {}\n\nList Dummy ID: {}".format(dummyCard._id,passedlist[0]._id)) #Debug
   if not re.search(r'doNotTrash',Autoscript):
      debugNotify("Did not find string 'doNotTrash' in {}. Trashing Card".format(Autoscript))
      card.moveTo(card.owner.piles['Heap/Archives(Face-up)'])
   if action: announceString = TokensX('Put{}'.format(action.group(2)), announceText,dummyCard, n = n) # If we have a -with in our autoscript, this is meant to put some tokens on the dummy card.
   else: announceString = announceText + 'create a lingering effect for {}'.format(targetPL)
   debugNotify("<<< CreateDummy()", 3)
   return announceString # Creating a dummy isn't usually announced.

def ChooseKeyword(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for marking cards to be of a different keyword than they are
   debugNotify(">>> ChooseKeyword(){}".format(extraASDebug(Autoscript))) #Debug
   #confirm("Reached ChooseKeyword") # Debug
   choiceTXT = ''
   targetCardlist = ''
   existingKeyword = None
   if targetCards is None: targetCards = []
   if len(targetCards) == 0: targetCards.append(card) # If there's been to target card given, assume the target is the card itself.
   for targetCard in targetCards: targetCardlist += '{},'.format(targetCard)
   targetCardlist = targetCardlist.strip(',') # Re remove the trailing comma
   if re.search(r'-simpleAnnounce', Autoscript): simpleAnnounce = True # This is needed for cards which select a keyword but it's not meant to assign it to themselves exactly, but we just recycle this function.
   else: simpleAnnounce = False
   action = re.search(r'\bChooseKeyword{([A-Za-z\| ]+)}', Autoscript)
   keywords = action.group(1).split('|')
   if len(keywords) == 1: choice = 0
   else:
      if simpleAnnounce: choiceTXT = 'Please choose keyword'
      else: choiceTXT = 'Choose one of the following keywords to assign to this card'
      choice = SingleChoice(choiceTXT, keywords, type = 'button', default = 0)
      if choice == None: return 'ABORT'
   for targetCard in targetCards:
      if targetCard.markers:
         for key in targetCard.markers:
            if re.search('Keyword:',key[0]):
               existingKeyword = key
      if re.search(r'{}'.format(keywords[choice]),targetCard.Keywords): 
         if existingKeyword: targetCard.markers[existingKeyword] = 0
         else: pass # If the keyword is anyway the same printed on the card, and it had no previous keyword, there is nothing to do
      elif existingKeyword:
         debugNotify("Searching for {} in {}".format(keywords[choice],existingKeyword[0])) # Debug               
         if re.search(r'{}'.format(keywords[choice]),existingKeyword[0]): pass # If the keyword is the same as is already there, do nothing.
         else: 
            targetCard.markers[existingKeyword] = 0 
            TokensX('Put1Keyword:{}'.format(keywords[choice]), '', targetCard)
      else: TokensX('Put1Keyword:{}'.format(keywords[choice]), '', targetCard)
   if notification == 'Quick': 
      if simpleAnnounce: announceString = "{} selects {} for {}".format(announceText, keywords[choice], targetCardlist)
      else: announceString = "{} marks {} as being {} now".format(announceText, targetCardlist, keywords[choice])
   else: 
      if simpleAnnounce: announceString = "{} select {} for {}".format(announceText, keywords[choice], targetCardlist)
      else: announceString = "{} mark {} as being {} now".format(announceText, targetCardlist, keywords[choice])
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< ChooseKeyword()", 3)
   return announceString
            
def TraceX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for drawing X Cards from the house deck to your hand.
   debugNotify(">>> TraceX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bTrace([0-9]+)', Autoscript)
   multiplier = per(Autoscript, card, n, targetCards)
   TraceStrength = num(action.group(1)) * multiplier
   reinforcement = inputTraceValue(card,silent = True)
   if reinforcement == 'ABORT': return 'ABORT'
   if reinforcement: reinforceTXT =  "and reinforced by {} (Total: {})".format(uniCredit(reinforcement),TraceStrength + reinforcement)
   else: reinforceTXT = "(Not reinforced)"
   setGlobalVariable('CorpTraceValue',str(TraceStrength + reinforcement))
   traceEffects = re.search(r'-traceEffects<(.*?),(.*?)>', Autoscript)
   debugNotify("Checking for Trace Effects", 2) #Debug
   if traceEffects:
      traceEffectTuple = (card._id,traceEffects.group(1),traceEffects.group(2))
      debugNotify("TraceEffectsTuple: {}".format(traceEffectTuple), 2) #Debug
      setGlobalVariable('CurrentTraceEffect',str(traceEffectTuple))
   if notification == 'Quick': announceString = "{} starts a Trace with a base strength of {} {}".format(announceText, TraceStrength, reinforceTXT)
   else: announceString = "{} start a trace with a base strength of {} {}".format(announceText, TraceStrength, reinforceTXT)
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< TraceX()", 3)
   return announceString

def PsiX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for setting up a Psi Struggle.
   debugNotify(">>> PsiX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bPsi', Autoscript)
   psiEffects = re.search(r'-psiEffects<(.*?),(.*?)>', Autoscript)
   debugNotify("Checking for Psi Effects", 2) #Debug
   if psiEffects:
      psiEffectTuple = (psiEffects.group(1),psiEffects.group(2))
      debugNotify("psiEffectsTuple: {}".format(psiEffectTuple), 2) #Debug
      setGlobalVariable('CurrentPsiEffect',str(psiEffectTuple))
   else: psiEffectTuple = None
   barNotifyAll('#000000',"{} is initiating a Psi struggle...".format(me))
   playPsiStartSound()
   secretCred = askInteger("How many credits do you want to secretly spend for the Psi effect of {}?".format(fetchProperty(card, 'Name')),0)
   while secretCred and (secretCred - reduceCost(card, 'PSI', secretCred, dryRun = True) > me.Credits) or (secretCred > 2):
      if secretCred - reduceCost(card, 'PSI', secretCred, dryRun = True) > me.Credits and confirm("You do not have that many credits to spend. Bypass?"): break
      if secretCred > 2: warn = ":::ERROR::: You cannot spend more than 2 credits!\n"
      else: warn = ''
      secretCred = askInteger("{}How many credits do you want to secretly spend?".format(warn),0)
   if secretCred != None: 
      notify("{} has spent a hidden amount of credits for {}.".format(me,fetchProperty(card, 'Name')))
      remoteCall(findOpponent(),'runnerPsi',[secretCred,psiEffectTuple,card,me])
   else: return 'ABORT'
   if notification == 'Quick': announceString = "{} sets their hidden Psi value".format(announceText)
   else: announceString = "{} set their hidden Psi value".format(announceText)
   if notification: notify('--> {}.'.format(announceString))
   debugNotify("<<< PsiX()", 3)
   return announceString

def runnerPsi(CorpPsiCount,psiEffectTuple,card,corpPlayer):
   debugNotify(">>> runnerPsi()") #Debug
   mute()
   barNotifyAll('#000000',"{} is guessing the correct Psi value.".format(me))
   secretCred = askInteger("How many credits do you want to spend for the Psi effect of {}?".format(fetchProperty(card, 'Name')),0)
   while secretCred and (secretCred - reduceCost(card, 'PSI', secretCred, dryRun = True) > me.Credits) or (secretCred > 2):
      if secretCred - reduceCost(card, 'PSI', secretCred, dryRun = True) > me.Credits and confirm("You do not have that many credits to spend. Bypass?"): break
      if secretCred > 2: warn = ":::ERROR::: You cannot spend more than 2 credits!\n"
      else: warn = ''
      secretCred = askInteger("{}How many credits do you want to spend?".format(warn),0)
   if secretCred == None: secretCred = 0
   me.Credits -= secretCred - reduceCost(card, 'PSI', secretCred)
   corpPlayer.Credits -= CorpPsiCount - reduceCost(card, 'PSI', CorpPsiCount, reversePlayer = True)
   autoscriptOtherPlayers('RevealedPSI', card)
   if psiEffectTuple: # If the tuple is None, then there's no effects specified for this psi effect.
      debugNotify("Found currentPsiEffectTuple")
      if secretCred != CorpPsiCount:
         notify("-- {} has failed the Psi struggle!\n   ({}: {} VS {}: {})".format(Identity,corpPlayer,uniCredit(CorpPsiCount),me,uniCredit(secretCred)))
         if psiEffectTuple[0] != 'None': executePostEffects(card,psiEffectTuple[0], 0,'Psi')
      else:
         notify("-- {} has succeeded the Psi struggle!\n   ({}: {} VS {}: {})".format(Identity,corpPlayer,uniCredit(CorpPsiCount),me,uniCredit(secretCred)))
         if psiEffectTuple[1] != 'None': executePostEffects(card,psiEffectTuple[1], 0,'Psi')
   pauseRecovery = eval(getGlobalVariable('Paused Runner'))
   if pauseRecovery:
      if pauseRecovery[0] == 'R&D': remoteCall(fetchRunnerPL(),"RDaccessX",[table,0,0,0])
      elif  pauseRecovery[0] == 'HQ': remoteCall(fetchRunnerPL(),"HQaccess",[table,0,0])
   debugNotify("<<< runnerPsi()") #Debug

def ModifyStatus(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for modifying the status of a card on the table.
   debugNotify(">>> ModifyStatus(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   targetCardlist = '' # A text field holding which cards are going to get tokens.
   extraText = ''
   action = re.search(r'\b(Rez|Derez|Expose|Trash|Uninstall|Possess|Exile|Rework|Install|Score|Rehost)(Target|Host|Multi|Myself)[-to]*([A-Z][A-Za-z&_ ]+)?', Autoscript)
   if action.group(2) == 'Myself': 
      del targetCards[:] # Empty the list, just in case.
      targetCards.append(card)
   if action.group(2) == 'Host': 
      del targetCards[:] # Empty the list, just in case.
      debugNotify("Finding Host")
      host = fetchHost(card)
      if host: targetCards = [host]
      else: 
         debugNotify("No Host Found? Aborting!")
         return 'ABORT'      
   if action.group(3): dest = action.group(3)
   else: dest = 'hand'
   for targetCard in targetCards: 
      if action.group(1) == 'Derez': 
         targetCardlist += '{},'.format(fetchProperty(targetCard, 'name')) # Derez saves the name because by the time we announce the action, the card will be face down.
      else: targetCardlist += '{},'.format(targetCard)
   targetCardlist = targetCardlist.strip(',') # Re remove the trailing comma
   for targetCard in targetCards:
      if re.search(r'-ifEmpty',Autoscript):
         debugNotify("Checking if card with {} credits and {} power is empty".format(targetCard.markers[mdict['Credits']],targetCard.markers[mdict['Power']]))
         if targetCard.markers[mdict['Credits']] or targetCard.markers[mdict['Power']]:
            debugNotify("Card is not Empty")
            if len(targetCards) > 1: continue #If the modification only happens when the card runs out of credits or power, then we abort if it still has any
            else: return announceText # If there's only 1 card and it's not supposed to be trashed yet, do nothing.
      if action.group(1) == 'Rez':
         if re.search(r'-payCost',Autoscript): # This modulator means the script is going to pay for the card normally
            preReducRegex = re.search(r'-reduc([0-9])',Autoscript) # this one means its going to reduce the cost a bit.
            if preReducRegex: preReduc = num(preReducRegex.group(1))
            else: preReduc = 0
            intRez(targetCard, cost = 'not free', preReduction = preReduc)
         else: 
            preReduc = 0
            intRez(targetCard, cost = 'free', silent = True)
      elif action.group(1) == 'Derez' and derez(targetCard, silent = True) != 'ABORT': pass
      elif action.group(1) == 'Expose': 
         exposeResult = expose(targetCard, silent = True)
         if exposeResult == 'ABORT': return 'ABORT'
         elif exposeResult == 'COUNTERED': extraText = " (Countered!)"
      elif action.group(1) == 'Uninstall' and uninstall(targetCard, destination = dest, silent = True) != 'ABORT': pass
      elif action.group(1) == 'Possess':
         if re.search(r'-forceHost',Autoscript):
            if possess(card, targetCard, silent = True, force = True) == 'ABORT': return 'ABORT'
         elif possess(card, targetCard, silent = True) == 'ABORT': return 'ABORT'
      elif action.group(1) == 'Rehost':
         if re.search(r'Caissa', targetCard.Keywords): newHost = chkHostType(targetCard,'DemiAutoTargeted', caissa = True)
         else: newHost = chkHostType(targetCard,'DemiAutoTargeted')
         if not newHost: 
            delayed_whisper("Not a card that {} can rehost on. Bad script?!".format(targetCard))
            return 'ABORT'
         else:
            try:
               if newHost == 'ABORT':
                  delayed_whisper("Please target an appropriate card to host {}".format(targetCard))
                  return 'ABORT'
            except: hostMe(targetCard,newHost)
      elif action.group(1) == 'Trash':
         trashResult = intTrashCard(targetCard, fetchProperty(targetCard,'Stat'), "free", silent = True)
         if trashResult == 'ABORT': return 'ABORT'
         elif trashResult == 'COUNTERED': extraText = " (Countered!)"
      elif action.group(1) == 'Exile' and exileCard(targetCard, silent = True) != 'ABORT': pass
      elif action.group(1) == 'Rework': # Rework puts a card on top of R&D (usually shuffling afterwards)
         changeCardGroup(targetCard,targetCard.controller.piles['R&D/Stack'])
         #targetCard.moveTo(targetCard.controller.piles['R&D/Stack'])
      elif action.group(1) == 'Install': # Install simply plays a cast on the table unrezzed without paying any costs.
         if re.search(r'-payCost',Autoscript): # This modulator means the script is going to pay for the card normally
            preReducRegex = re.search(r'-reduc([0-9])',Autoscript) # this one means its going to reduce the cost a bit.
            if preReducRegex: preReduc = num(preReducRegex.group(1))
            else: preReduc = 0
            payCost = 'not free'
         else: 
            preReduc = 0
            payCost = 'free'         
         intPlay(targetCard, payCost, True, preReduc)
         extraTokens = re.search(r'-with([0-9][A-Z][A-Za-z&_ ]+)', Autoscript)
         if extraTokens: TokensX('Put{}'.format(extraTokens.group(1)), '',targetCard) # If we have a -with in our autoscript, this is meant to put some tokens on the installed card.
      elif action.group(1) == 'Score': # Score takes a card and claims it as an agenda
         targetPL = ofwhom(Autoscript, targetCard.owner)
         grabCardControl(targetCard)
         if targetPL.getGlobalVariable('ds') == 'corp': scoreType = 'scoredAgenda'
         else: scoreType = 'liberatedAgenda'
         placeCard(targetCard, 'SCORE', type = scoreType)
         #rnd(1,100)
         update()
         card.highlight = None
         card.isFaceUp = True
         update()
         if targetCard.Type == 'Agenda': 
            targetCard.markers[mdict['Scored']] += 1
            targetPL.counters['Agenda Points'].value += num(fetchProperty(targetCard,'Stat'))
            if targetPL.getGlobalVariable('ds') == 'corp': autoscriptOtherPlayers('AgendaScored',card)
            else: autoscriptOtherPlayers('AgendaLiberated',card)
         debugNotify("Current card group before scoring = {}".format(targetCard.group.name))
         grabCardControl(targetCard,targetPL)
         # We do not autoscript other players (see http://boardgamegeek.com/thread/914076/personal-evolution-and-notoriety)
         if targetPL.counters['Agenda Points'].value >= 7 or (getSpecial('Identity',fetchCorpPL()).name == "Harmony Medtech" and targetPL.counters['Agenda Points'].value >= 6):
            notify("{} wins the game!".format(targetPL))
            if targetPL == me: reportGame()         
            else: reportGame('AgendaDefeat')
      else: return 'ABORT'
      if action.group(2) != 'Multi': break # If we're not doing a multi-targeting, abort after the first run.
   if notification == 'Quick': announceString = "{} {} {}{}".format(announceText, action.group(1), targetCardlist,extraText)
   else: announceString = "{} {} {}{}".format(announceText, action.group(1), targetCardlist, extraText)
   if notification and not re.search(r'isSilent', Autoscript): notify('--> {}.'.format(announceString))
   debugNotify("<<< ModifyStatus()", 3)
   if re.search(r'isSilent', Autoscript): return announceText
   else: return announceString
         
def InflictX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for inflicting Damage to players (even ourselves)
   debugNotify(">>> InflictX(){}".format(extraASDebug(Autoscript))) #Debug
   mute()
   if targetCards is None: targetCards = []
   global failedRequirement
   localDMGwarn = True #A variable to check if we've already warned the player during this damage dealing.
   action = re.search(r'\b(Inflict)([0-9]+)(Meat|Net|Brain)Damage', Autoscript) # Find out what kind of damage we're going
   multiplier = per(Autoscript, card, n, targetCards)
   enhancer = findEnhancements(Autoscript) #See if any of our cards increases damage we deal
   debugNotify("card.owner = {}".format(card.owner),3)
   targetPL = fetchRunnerPL() #Damage always goes to the runner
   if enhancer > 0: enhanceTXT = ' (Enhanced: +{})'.format(enhancer) #Also notify that this is the case
   else: enhanceTXT = ''
   if multiplier == 0 or num(action.group(2)) == 0: DMG = 0 # if we don't do any damage, we don't enhance it
   else: DMG = (num(action.group(2)) * multiplier) + enhancer #Calculate our damage
   preventTXT = ''
   if DMG and Automations['Damage']: #The actual effects happen only if the Damage automation switch is ON. It should be ON by default.
      if getSetting('DMGwarn',True) and localDMGwarn:
         localDMGwarn = False # We don't want to warn the player for every point of damage.
         if targetPL != me: notify(":::ATTENTION::: {} is about to inflict {} {} Damage to {}!".format(me,DMG,action.group(3),targetPL))
         if not confirm(":::Warning::: You are about to inflict automatic damage!\
                       \nBefore you do that, please make sure that your target is not currently manipulating their hand or this might cause the game to crash.\
                     \n\nImportant: Before proceeding, ask your target to activate any cards they want that add protection against this type of damage. If this is yourself, please make sure you do this before you activate damage effects.\
                     \n\nDo you want this warning message will to appear again next time you do damage? (Recommended)"): setSetting('DMGwarn',False)
      if re.search(r'nonPreventable', Autoscript): 
         DMGprevented = 0
         preventTXT = ' (Unpreventable)'
      else: DMGprevented = findDMGProtection(DMG, action.group(3), targetPL)
      if DMGprevented == 'ABORT': return 'ABORT'
      elif DMGprevented > 0:
         preventTXT = ' ({} prevented)'.format(DMGprevented)
         DMG -= DMGprevented
      if DMG:
         specialReduction = chkDmgSpecialEffects(action.group(3),DMG)
         finalDMG = DMG - specialReduction[0] # We check if any effect hijacks the normal damage effect, but we don't want to change the number of damage we announce is being done.
         if specialReduction[1]: DMG = 0 
         remoteCall(targetPL, 'intdamageDiscard',[finalDMG])
         if action.group(3) == 'Brain': applyBrainDmg(targetPL, DMG)
      if DMG: 
         autoscriptOtherPlayers('{}DMGInflicted'.format(action.group(3)),getSpecial('Identity',targetPL),DMG) # We also trigger any script for damage
         playDMGSound(action.group(3))
   if targetPL == me: targetPL = 'theirself' # Just changing the announcement to fit better.
   if re.search(r'isRequirement', Autoscript) and DMG < 1: failedRequirement = True # Requirement means that the cost is still paid but other clicks are not going to follow.
   if notification == 'Quick': announceString = "{} suffer {} {} damage{}".format(announceText,DMG,action.group(3),preventTXT)
   else: announceString = "{} inflict {} {} damage{} to {}{}".format(announceText,DMG,action.group(3),enhanceTXT,targetPL,preventTXT)
   if notification and DMG > 0: notify('--> {}.'.format(announceString))
   debugNotify("<<< InflictX()", 3)
   return announceString

def RetrieveX(Autoscript, announceText, card, targetCards = None, notification = None, n = 0): # Core Command for finding a specific card from a pile and putting it in hand or trash pile
   debugNotify(">>> RetrieveX(){}".format(extraASDebug(Autoscript))) #Debug
   if targetCards is None: targetCards = []
   action = re.search(r'\bRetrieve([0-9]+)Card', Autoscript)
   targetPL = ofwhom(Autoscript, card.owner)
   debugNotify("Setting Source", 2)
   if re.search(r'-fromTrash', Autoscript) or re.search(r'-fromArchives', Autoscript) or re.search(r'-fromHeap', Autoscript):
      source = targetPL.piles['Heap/Archives(Face-up)']
   else: 
      debugNotify("Moving R&D/Stack to the scripting Pile", 2)
      for c in targetPL.piles['R&D/Stack']: c.moveToBottom(me.ScriptingPile) # If the source is the R&D/Stack, then we move everything to the scripting pile in order to be able to read their properties. We move each new card to the bottom to preserve card order
      source = me.ScriptingPile # # Then we change the source to that pile so that the rest of the script can process the right location.
      rnd(1,10) # We give a delay to allow OCTGN to read the card properties before we proceed with checking them
   if source == me.ScriptingPile: sourcePath =  "from their {}".format(pileName(targetPL.piles['R&D/Stack']))
   else: sourcePath =  "from their {}".format(pileName(source))
   if sourcePath == "from their Face-up Archives": sourcePath = "from their Archives"
   debugNotify("Setting Destination", 2)
   if re.search(r'-toTable', Autoscript):
      destination = table
      if re.search(r'-grab.*?(Event|Operation)',Autoscript): destiVerb = 'play'   
      else: destiVerb = 'install'   
   elif re.search(r'-toDeck', Autoscript):
      destination = targetPL.piles['R&D/Stack']
      destiVerb = 'rework'
   else: 
      destination = targetPL.hand
      destiVerb = 'retrieve'
   debugNotify("Fething Script Variables", 2)
   count = num(action.group(1))
   multiplier = per(Autoscript, card, n, targetCards, notification)
   restrictions = prepareRestrictions(Autoscript, seek = 'retrieve')
   cardList = []
   countRestriction = re.search(r'-onTop([0-9]+)Cards', Autoscript)
   if countRestriction: topCount = num(countRestriction.group(1))
   else: topCount = len(source)
   for c in source.top(topCount):
      debugNotify("Checking card: {}".format(c), 4)
      if checkCardRestrictions(gatherCardProperties(c), restrictions) and checkSpecialRestrictions(Autoscript,c):
         cardList.append(c)
         if re.search(r'-isTopmost', Autoscript) and len(cardList) == count: break # If we're selecting only the topmost cards, we select only the first matches we get.         
   if re.search(r'-fromArchives', Autoscript) and not re.search(r'-faceUpOnly', Autoscript): # If the card is being retrieved from archives, we need to also check hidden archives.
      for c in targetPL.piles['Archives(Hidden)']:
         debugNotify("Checking Hidden Arc card: {}".format(c), 4)
         if checkCardRestrictions(gatherCardProperties(c), restrictions) and checkSpecialRestrictions(Autoscript,c):
            cardList.append(c)
            if re.search(r'-isTopmost', Autoscript) and len(cardList) == count: break # If we're selecting only the topmost cards, we select only the first matches we get.     
   debugNotify("cardList: {}".format([c.name for c in cardList]), 3)
   chosenCList = []
   abortedRetrieve = False
   if len(cardList) > count or re.search(r'upToAmount',Autoscript):
      cardChoices = []
      cardTexts = []
      if count > len(cardList): count = len(cardList) # To avoid crashing if the pile has less cards than the amount we want to retrieve.
      notify(":> {} starts retrieving cards with {}...".format(me,card,count))
      for iter in range(count):
         del cardChoices[:]
         del cardTexts[:]
         for c in cardList:
            if (c.Rules,c.group.name) not in cardTexts: # we don't want to provide the player with a the same card as a choice twice, so we check if the a card in this group was already an option.
               debugNotify("Appending card", 4)
               cardChoices.append(c)
               cardTexts.append((c.Rules,c.group.name))
         if re.search(r'upToAmount',Autoscript): cancelButtonName = 'Done'
         else: cancelButtonName = 'Cancel'
         if re.search(r'-fromArchives', Autoscript): showGroup = True # If the card comes from the archives, then we want to inform the player from which group the card is coming from, so that they know to select from Hidden or Face-up Archives
         else: showGroup = False
         choice = SingleChoice("Choose card to retrieve{}".format({1:''}.get(count,' {}/{}'.format(iter + 1,count))), makeChoiceListfromCardList(cardChoices, includeGroup = showGroup), type = 'button', cancelName = cancelButtonName)
         if choice == None:
            if not re.search(r'upToAmount',Autoscript): abortedRetrieve = True # If we have the upToAmount, it means the retrieve can get less cards than the max amount, so cancel does not work as a cancel necessarily.            
            break
         else:
            chosenCList.append(cardChoices[choice])
            cardList.remove(cardChoices[choice])
            if iter + 1 != count: notify(":-> {} out of {} chosen...".format(iter + 1,count))
   else: chosenCList = cardList
   debugNotify("Generating cardNames", 2)
   if re.search(r'doNotReveal',Autoscript): # If we do not reveal the cards, we still want to tell which cards from the face-up archives were taken
      if re.search(r'-fromArchives', Autoscript):
         debugNotify(str(["{} in {}".format(c.name, c.group.name) for c in chosenCList]))
         shownArcCards = [c.name for c in chosenCList if c.group == targetPL.piles['Heap/Archives(Face-up)']]
         debugNotify("shownArcCards = {}".format(shownArcCards))
         hiddenArcCards = [c.name for c in chosenCList if c.group == targetPL.piles['Archives(Hidden)']]
         debugNotify("hiddenArcCards = {}".format(hiddenArcCards))
         if len(shownArcCards) and len(hiddenArcCards): cardNames = "{} and {} hidden card(s)".format(shownArcCards,len(hiddenArcCards))
         elif len(shownArcCards): cardNames = str(shownArcCards)
         else: cardNames = "{} hidden cards".format(len(chosenCList))
      else: cardNames = "{} cards".format(len(chosenCList))
   else: cardNames = str([c.name for c in chosenCList])
   debugNotify("About to move {} to {}".format([c for c in chosenCList],destination.name))
   if not abortedRetrieve:
      for c in chosenCList:
         if destination == table: 
            if re.search(r'-payCost',Autoscript): # This modulator means the script is going to pay for the card normally
               preReducRegex = re.search(r'-reduc([0-9]+)',Autoscript) # this one means its going to reduce the cost a bit.
               if preReducRegex: preReduc = num(preReducRegex.group(1))
               else: preReduc = 0
               payCost = 'not free'
            else: 
               preReduc = 0
               payCost = 'free'         
            intPlay(c, payCost, True, preReduc)
         else: c.moveTo(destination)
         tokensRegex = re.search(r'-with([A-Za-z0-9: ]+)', Autoscript) # If we have a -with in our autoscript, this is meant to put some tokens on the retrieved card.
         if tokensRegex: TokensX('Put{}'.format(tokensRegex.group(1)), announceText,c, n = n) 
   debugNotify("About to restore pile.", 2)
   if source == me.ScriptingPile: # If our source was the scripting pile, we know we just checked the R&D,
      for c in source: c.moveToBottom(targetPL.piles['R&D/Stack']) # So we return cards to their original location
   if abortedRetrieve: #If the player canceled a retrieve effect from R&D / Stack, we make sure to shuffle their pile as well.
      notify("{} has aborted the retrieval effect from {}".format(me,card))
      if source == me.ScriptingPile: shuffle(targetPL.piles['R&D/Stack'])
      return 'ABORT'
   debugNotify("About to announce.", 2)
   if len(chosenCList) == 0: announceString = "{} attempts to {} a card {}, but there were no valid targets.".format(announceText, destiVerb, sourcePath)
   else: announceString = "{} {} {} {}".format(announceText, destiVerb, cardNames, sourcePath)
   if notification and multiplier > 0: notify(':> {}.'.format(announceString))
   debugNotify("<<< RetrieveX()", 3)
   return (announceString,chosenCList) # We also return which cards we've retrieved
      

#------------------------------------------------------------------------------
# Helper Functions
#------------------------------------------------------------------------------
   
def chkNoisy(card): # Check if the player successfully used a noisy icebreaker, and if so, give them the consequences...
   debugNotify(">>> chkNoisy()") #Debug
   if re.search(r'Noisy', fetchProperty(card, 'Keywords')) and re.search(r'Icebreaker', fetchProperty(card, 'Keywords')): 
      me.setGlobalVariable('wasNoisy', '1') # First of all, let all players know of this fact.
      debugNotify("Noisy credit Set!", 2) #Debug
   debugNotify("<<< chkNoisy()", 3) #Debug

def penaltyNoisy(card):
   debugNotify(">>> penaltyNoisy()") #Debug
   if re.search(r'Noisy', fetchProperty(card, 'Keywords')) and re.search(r'Icebreaker', fetchProperty(card, 'Keywords')): 
      NoisyCost = re.search(r'triggerNoisy([0-9]+)',CardsAS.get(card.model,''))
      if debugVerbosity >= 2: 
         if NoisyCost: notify("Noisy Trigger Found: {}".format(NoisyCost.group(1))) #Debug      
         else: notify("Noisy Trigger not found. AS was: {}".format(CardsAS.get(card.model,''))) #Debug      
      if NoisyCost: 
         total = 0
         cost = num(NoisyCost.group(1))
         stealthCards = [c for c in table 
                        if c.controller == me
                        and c.isFaceUp
                        and re.search(r'Stealth',getKeywords(c))
                        and c.markers[mdict['Credits']]]
         debugNotify("{} cards found".format(len(stealthCards)), 2)
         for Scard in sortPriority(stealthCards):
            debugNotify("Removing from {}".format(Scard), 3)
            while cost > 0 and Scard.markers[mdict['Credits']] > 0:
               Scard.markers[mdict['Credits']] -= 1
               cost -= 1
               total += 1
      notify("--> {}'s {} has destroyed a total of {} credits on stealth cards".format(me,card,total))
   debugNotify("<<< penaltyNoisy()", 3) #Debug
   
def autoscriptCostUndo(card, Autoscript): # Function for undoing the cost of an autoscript.
   debugNotify(">>> autoscriptCostUndo(){}".format(extraASDebug(Autoscript))) #Debug
   delayed_whisper("--> Undoing action...")
   actionCost = re.match(r"A([0-9]+)B([0-9]+)G([0-9]+)T([0-9]+):", Autoscript)
   me.Clicks += num(actionCost.group(1))
   me.counters['Credits'].value += num(actionCost.group(2))
   me.counters['Agenda Points'].value += num(actionCost.group(3))
   if re.search(r"T2:", Autoscript):
      random = rnd(10,5000) # A little wait...
      card.orientation = Rot0

def findTarget(Autoscript, fromHand = False, card = None, dryRun = False): # Function for finding the target of an autoscript
   debugNotify(">>> findTarget(){}".format(extraASDebug(Autoscript))) #Debug
   try:
      if fromHand == True or re.search(r'-fromHand',Autoscript): 
         if re.search(r'-targetOpponents',Autoscript): group = findOpponent().hand
         else: group = me.hand
      else: group = table
      foundTargets = []
      if re.search(r'Targeted', Autoscript):
         requiredAllegiances = []
         targetGroups = prepareRestrictions(Autoscript)
         debugNotify("About to start checking all targeted cards.\n### targetGroups:{}".format(targetGroups), 2) #Debug
         for targetLookup in group: # Now that we have our list of restrictions, we go through each targeted card on the table to check if it matches.
            if (targetLookup.targetedBy and targetLookup.targetedBy == me) or (re.search(r'AutoTargeted', Autoscript) and targetLookup.highlight != DummyColor and targetLookup.highlight != RevealedColor and targetLookup.highlight != InactiveColor):
            # OK the above target check might need some decoding:
            # Look through all the cards on the group and start checking only IF...
            # * Card is targeted and targeted by the player OR target search has the -AutoTargeted modulator and it is NOT highlighted as a Dummy, Inactive or Revealed.
            # * The player who controls this card is supposed to be me or the enemy.
               debugNotify("Checking {}".format(targetLookup), 2)
               if not checkSpecialRestrictions(Autoscript,targetLookup): continue
               if re.search(r'-onHost',Autoscript): 
                  debugNotify("Looking for Host", 2)
                  if not card: continue # If this targeting script targets only a host and we have not passed what the attachment is, we cannot find the host, so we abort.
                  debugNotify("Attachment is: {}".format(card), 2)
                  hostCards = eval(getGlobalVariable('Host Cards'))
                  isHost = False
                  for attachment in hostCards:
                     if attachment == card._id and hostCards[attachment] == targetLookup._id: 
                        debugNotify("Host found! {}".format(targetLookup), 2)
                        isHost = True
                  if not isHost: continue
               if checkCardRestrictions(gatherCardProperties(targetLookup,Autoscript), targetGroups): 
                  if not targetLookup in foundTargets: 
                     debugNotify("About to append {}".format(targetLookup), 3) #Debug
                     foundTargets.append(targetLookup) # I don't know why but the first match is always processed twice by the for loop.
               else: debugNotify("findTarget() Rejected {}".format(targetLookup), 3)# Debug
         debugNotify("Finished seeking. foundTargets List = {}".format([T.name for T in foundTargets]), 2)
         if re.search(r'DemiAutoTargeted', Autoscript):
            debugNotify("Checking DemiAutoTargeted switches", 2)# Debug
            targetNRregex = re.search(r'-choose([1-9])',Autoscript)
            targetedCards = 0
            foundTargetsTargeted = []
            debugNotify("About to count targeted cards", 2)# Debug
            for targetC in foundTargets:
               if targetC.targetedBy and targetC.targetedBy == me: foundTargetsTargeted.append(targetC)
            if targetNRregex:
               debugNotify("!!! targetNRregex exists", 2)# Debug
               if num(targetNRregex.group(1)) > len(foundTargetsTargeted): pass # Not implemented yet. Once I have choose2 etc I'll work on this
               else: # If we have the same amount of cards targeted as the amount we need, then we just select the targeted cards
                  foundTargets = foundTargetsTargeted # This will also work if the player has targeted more cards than they need. The later choice will be simply between those cards.
            else: # If we do not want to choose, then it's probably a bad script. In any case we make sure that the player has targeted something (as the alternative it giving them a random choice of the valid targets)
               del foundTargets[:]
         if len(foundTargets) == 0 and not re.search(r'(?<!Demi)AutoTargeted', Autoscript): 
            targetsText = ''
            mergedList = []
            for posRestrictions in targetGroups: 
               debugNotify("About to notify on restrictions", 2)# Debug
               if targetsText == '': targetsText = '\n -- You need: '
               else: targetsText += ', or '
               del mergedList[:]
               mergedList += posRestrictions[0]
               if len(mergedList) > 0: targetsText += "{} and ".format(mergedList)  
               del mergedList[:]
               mergedList += posRestrictions[1]
               if len(mergedList) > 0: targetsText += "not {}".format(mergedList)
               if targetsText.endswith(' and '): targetsText = targetsText[:-len(' and ')]
            debugNotify("About to chkPlayer()", 2)# Debug
            if not chkPlayer(Autoscript, targetLookup.controller, False, True): 
               allegiance = re.search(r'by(Opponent|Me)', Autoscript)
               requiredAllegiances.append(allegiance.group(1))
            if len(requiredAllegiances) > 0: targetsText += "\n00 Valid Target Allegiance: {}.".format(requiredAllegiances)
            if re.search(r'isRezzed',Autoscript): targetsText += "\n -- Card Status: Rezzed"
            if re.search(r'isUnrezzed',Autoscript): targetsText += "\n -- Card Status: Unrezzed"
            if not re.search(r'isMutedTarget', Autoscript): delayed_whisper(":::ERROR::: You need to target a valid card before using this action{}.".format(targetsText))
         elif len(foundTargets) >= 1 and re.search(r'-choose',Autoscript):
            if dryRun: pass # In dry runs we just want to check we have valid targets
            else:
               debugNotify("Going for a choice menu", 2)# Debug
               choiceType = re.search(r'-choose([0-9]+)',Autoscript)
               targetChoices = makeChoiceListfromCardList(foundTargets)
               if not card: choiceTitle = "Choose one of the valid targets for this effect"
               else: choiceTitle = "Choose one of the valid targets for {}".format(fetchProperty(card, 'name'))
               debugNotify("Checking for SingleChoice", 2)# Debug
               if choiceType.group(1) == '1':
                  if len(foundTargets) == 1: choice = 0 # If we only have one valid target, autoselect it.
                  else: choice = SingleChoice(choiceTitle, targetChoices, type = 'button', default = 0)
                  if choice == 'ABORT': del foundTargets[:]
                  else: foundTargets = [foundTargets.pop(choice)] # if we select the target we want, we make our list only hold that target
         elif re.search(r'-randomTarget',Autoscript): # This modulator randomly selects one card from the valid cards as the single target. Usually paired with AutoTargeted
            debugNotify("Going for a random choice menu")# Debug
            rndChoice = rnd(0,len(foundTargets) - 1)
            foundTargets = [foundTargets[rndChoice]]
      if debugVerbosity >= 3: # Debug
         tlist = [] 
         for foundTarget in foundTargets: tlist.append(foundTarget.name) # Debug
         notify("<<< findTarget() by returning: {}".format(tlist))
      return foundTargets
   except: notify("!!!ERROR!!! on findTarget()")   
   
def gatherCardProperties(card,Autoscript = ''):
   debugNotify(">>> gatherCardProperties()") #Debug     
   cardProperties = []
   if storeProperties(card) != 'ABORT': # We store the card properties so that we don't start flipping the cards over each time.
      debugNotify("Appending name", 4) #Debug
      cName = fetchProperty(card, 'Name')
      cardProperties.append(cName.replace('-','_')) # We are going to check its name. We replace all dashes to underscores to avoid messing up our lookup in prepareRestrictions() 
      debugNotify("Appending Type", 4) #Debug                
      cardProperties.append(fetchProperty(card, 'Type')) # We are going to check its Type
      debugNotify("Appending Keywords", 4) #Debug                
      cardSubkeywords = getKeywords(card).split('-') # And each individual keyword. keywords are separated by " - "
      for cardSubkeyword in cardSubkeywords:
         strippedCS = cardSubkeyword.strip() # Remove any leading/trailing spaces between keywords. We need to use a new variable, because we can't modify the loop iterator.
         if strippedCS: cardProperties.append(strippedCS) # If there's anything left after the stip (i.e. it's not an empty string anymrore) add it to the list.
      debugNotify("<<< gatherCardProperties() with Card Properties: {}".format(cardProperties), 3) #Debug
   return cardProperties

def prepareRestrictions(Autoscript, seek = 'target'):
# This is a function that takes an autoscript and attempts to find restrictions on card keywords/types/names etc. 
# It goes looks for a specific working and then gathers all restrictions into a list of tuples, where each tuple has a negative and a positive entry
# The positive entry (position [0] in the tuple) contains what card properties a card needs to have to be a valid selection
# The negative entry (position [1] in the tuple) contains what card properties a card needs to NOT have to be a vaid selection.
   debugNotify(">>> prepareRestrictions() {}".format(extraASDebug(Autoscript))) #Debug
   validTargets = [] # a list that holds any type that a card must be, in order to be a valid target.
   targetGroups = []
   if seek == 'type': whatTarget = re.search(r'\b(type)([A-Za-z0-9_{},& ]+)[-]?', Autoscript) # seek of "type" is used by autoscripting other players, and it's separated so that the same card can have two different triggers (e.g. see Darth Vader)
   elif seek == 'retrieve': whatTarget = re.search(r'\b(grab)([A-Za-z0-9_{},& ]+)[-]?', Autoscript) # seek of "retrieve" is used when checking what types of cards to retrieve from one's deck or discard pile
   elif seek == 'reduce': whatTarget = re.search(r'\b(affects)([A-Za-z0-9_{},& ]+)[-]?', Autoscript) # seek of "reduce" is used when checking for what types of cards to recuce the cost.
   else: whatTarget = re.search(r'\b(at)([A-Za-z0-9_{},& ]+)[-]?', Autoscript) # We signify target restrictions keywords by starting a string with "or"
   if whatTarget: 
      debugNotify("whatTarget = {}".format(whatTarget.groups()))
      debugNotify("Splitting on _or_", 2) #Debug
      validTargets = whatTarget.group(2).split('_or_') # If we have a list of valid targets, split them into a list, separated by the string "_or_". Usually this results in a list of 1 item.
      ValidTargetsSnapshot = list(validTargets) # We have to work on a snapshot, because we're going to be modifying the actual list as we iterate.
      for iter in range(len(ValidTargetsSnapshot)): # Now we go through each list item and see if it has more than one condition (Eg, non-desert fief)
         debugNotify("Creating empty list tuple", 2) #Debug            
         targetGroups.insert(iter,([],[])) # We create a tuple of two list. The first list is the valid properties, the second the invalid ones
         multiConditionTargets = ValidTargetsSnapshot[iter].split('_and_') # We put all the mutliple conditions in a new list, separating each element.
         debugNotify("Splitting on _and_ & _or_ ", 2) #Debug
         debugNotify("multiConditionTargets is: {}".format(multiConditionTargets), 4) #Debug
         for chkCondition in multiConditionTargets:
            debugNotify("Checking: {}".format(chkCondition), 4) #Debug
            regexCondition = re.search(r'(no[nt]){?([A-Za-z,& ]+)}?', chkCondition) # Do a search to see if in the multicondition targets there's one with "non" in front
            if regexCondition and (regexCondition.group(1) == 'non' or regexCondition.group(1) == 'not'):
               debugNotify("Invalid Target", 4) #Debug
               if regexCondition.group(2) not in targetGroups[iter][1]: targetGroups[iter][1].append(regexCondition.group(2)) # If there is, move it without the "non" into the invalidTargets list.
            else: 
               debugNotify("Valid Target", 4) #Debug
               targetGroups[iter][0].append(chkCondition) # Else just move the individual condition to the end if validTargets list
   else: debugNotify("No restrictions regex", 2) #Debug 
   debugNotify("<<< prepareRestrictions() by returning: {}.".format(targetGroups), 3)
   return targetGroups

def checkCardRestrictions(cardPropertyList, restrictionsList):
   debugNotify(">>> checkCardRestrictions()") #Debug
   debugNotify("cardPropertyList = {}".format(cardPropertyList), 2) #Debug
   debugNotify("restrictionsList = {}".format(restrictionsList), 2) #Debug
   validCard = True
   for restrictionsGroup in restrictionsList: 
   # We check each card's properties against each restrictions group of valid + invalid properties.
   # Each Restrictions group is a tuple of two lists. First list (tuple[0]) is the valid properties, and the second list is the invalid properties
   # We check if all the properties from the valid list are in the card properties
   # And then we check if no properties from the invalid list are in the properties
   # If both of these are true, then the card is a valid choice for our action.
      validCard = True # We need to set it here as well for further loops
      debugNotify("restrictionsGroup checking: {}".format(restrictionsGroup), 3)
      if len(restrictionsList) > 0 and len(restrictionsGroup[0]) > 0: 
         for validtargetCHK in restrictionsGroup[0]: # look if the card we're going through matches our valid target checks
            debugNotify("Checking for valid match on {}".format(validtargetCHK), 4) #Debug
            if not validtargetCHK in cardPropertyList: 
               debugNotify("{} not found in {}".format(validtargetCHK,cardPropertyList), 4) #Debug
               validCard = False
      else: debugNotify("No positive restrictions", 4)
      if len(restrictionsList) > 0 and len(restrictionsGroup[1]) > 0: # If we have no target restrictions, any selected card will do as long as it's a valid target.
         for invalidtargetCHK in restrictionsGroup[1]:
            debugNotify("Checking for invalid match on {}".format(invalidtargetCHK), 4) #Debug
            if invalidtargetCHK in cardPropertyList: validCard = False
      else: debugNotify("No negative restrictions", 4)
      if validCard: break # If we already passed a restrictions check, we don't need to continue checking restrictions 
   debugNotify("<<< checkCardRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def checkSpecialRestrictions(Autoscript,card):
# Check the autoscript for special restrictions of a valid card
# If the card does not validate all the restrictions included in the autoscript, we reject it
   debugNotify(">>> checkSpecialRestrictions() {}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("Card: {}".format(card)) #Debug
   validCard = True
   if not chkPlayer(Autoscript, card.controller, False, True): validCard = False
   if re.search(r'isICE',Autoscript) and card.orientation != Rot90: 
      debugNotify("Rejecting because it isn't an ICE")
      validCard = False # We made a special check for ICE, because some cards must be able target face-down ICE without being able to read its properties.
   if re.search(r'isRezzed',Autoscript) and not card.isFaceUp: 
      debugNotify("Rejecting because it's not unrezzed")
      validCard = False
   if re.search(r'isUnrezzed',Autoscript) and card.isFaceUp: 
      debugNotify("Rejecting because it's not rezzed")
      validCard = False
   if re.search(r'isScored',Autoscript) and not card.markers[mdict['Scored']] and not card.markers[mdict['ScorePenalty']]:
      debugNotify("Rejecting because it's not a scored agenda")
      validCard = False
   markerName = re.search(r'-hasMarker{([\w ]+)}',Autoscript) # Checking if we need specific markers on the card.
   if markerName: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      debugNotify("Checking marker restrictions", 2)# Debug
      debugNotify("Marker Name: {}".format(markerName.group(1)), 2)# Debug
      marker = findMarker(card, markerName.group(1))
      if not marker: 
         debugNotify("Rejecting because marker not found")
         validCard = False
   markerNeg = re.search(r'-hasntMarker{([\w ]+)}',Autoscript) # Checking if we need to not have specific markers on the card.
   if markerNeg: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      debugNotify("Checking negative marker restrictions", 2)# Debug
      debugNotify("Marker Name: {}".format(markerNeg.group(1)), 2)# Debug
      marker = findMarker(card, markerNeg.group(1))
      if marker: 
         debugNotify("Rejecting because marker was found")
         validCard = False
   else: debugNotify("No marker restrictions.", 4)
   propertyReq = re.search(r'-hasProperty{([\w ]+)}(eq|le|ge|gt|lt)([0-9])',Autoscript) 
   # Checking if the target needs to have a property at a certiain value. 
   # eq = equal, le = less than/equal, ge = greater than/equal, lt = less than, gt = greater than.
   if propertyReq:
      if propertyReq.group(2) == 'eq' and card.properties[propertyReq.group(1)] != propertyReq.group(3): validCard = False
      if propertyReq.group(2) == 'le' and num(card.properties[propertyReq.group(1)]) > num(propertyReq.group(3)): validCard = False
      if propertyReq.group(2) == 'ge' and num(card.properties[propertyReq.group(1)]) < num(propertyReq.group(3)): validCard = False
      if propertyReq.group(2) == 'lt' and num(card.properties[propertyReq.group(1)]) >= num(propertyReq.group(3)): validCard = False
      if propertyReq.group(2) == 'gt' and num(card.properties[propertyReq.group(1)]) <= num(propertyReq.group(3)): validCard = False
   debugNotify("<<< checkSpecialRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def checkOrigSpecialRestrictions(Autoscript,card):
# Check the autoscript for special restrictions of a originator card
# If the card does not validate all the restrictions included in the autoscript, we reject it
   debugNotify(">>> checkOrigSpecialRestrictions() {}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("Card: {}".format(card)) #Debug
   validCard = True
   markerName = re.search(r'-hasOrigMarker{([\w ]+)}',Autoscript) # Checking if we need specific markers on the card.
   if markerName: #If we're looking for markers, then we go through originator's markers any relevant ones
      debugNotify("Checking marker restrictions", 2)# Debug
      debugNotify("Marker Name: {}".format(markerName.group(1)), 2)# Debug
      marker = findMarker(card, markerName.group(1))
      if not marker: 
         debugNotify("Rejecting Originator because marker not found")
         validCard = False
   markerNeg = re.search(r'-hasntOrigMarker{([\w ]+)}',Autoscript) # Checking if we need to not have specific markers on the card.
   if markerNeg: #If we're looking for markers, then we go through each targeted card and check if it has any relevant markers
      debugNotify("Checking negative marker restrictions", 2)# Debug
      debugNotify("Marker Name: {}".format(markerNeg.group(1)), 2)# Debug
      marker = findMarker(card, markerNeg.group(1))
      if marker: 
         debugNotify("Rejecting Originator because marker was found")
         validCard = False
   else: debugNotify("No marker restrictions.", 4)
   debugNotify("<<< checkOrigSpecialRestrictions() with return {}".format(validCard)) #Debug
   return validCard

def makeChoiceListfromCardList(cardList,includeText = False, includeGroup = False):
# A function that returns a list of strings suitable for a choice menu, out of a list of cards
# Each member of the list includes a card's name, traits, resources, markers and, if applicable, combat icons
   debugNotify(">>> makeChoiceListfromCardList()")
   debugNotify("cardList: {}".format([c.name for c in cardList]), 2)
   targetChoices = []
   debugNotify("About to prepare choices list.", 2)# Debug
   for T in cardList:
      debugNotify("Checking {}".format(T), 4)# Debug
      markers = 'Counters:'
      if T.markers[mdict['Advancement']] and T.markers[mdict['Advancement']] >= 1: markers += " {} Advancement,".format(T.markers[mdict['Advancement']])
      if T.markers[mdict['Credits']] and T.markers[mdict['Credits']] >= 1: markers += " {} Credits,".format(T.markers[mdict['Credits']])
      if T.markers[mdict['Power']] and T.markers[mdict['Power']] >= 1: markers += " {} Power.".format(T.markers[mdict['Power']])
      if T.markers[mdict['Virus']] and T.markers[mdict['Virus']] >= 1: markers += " {} Virus.".format(T.markers[mdict['Virus']])
      if T.markers[mdict['Agenda']] and T.markers[mdict['Agenda']] >= 1: markers += " {} Agenda.".format(T.markers[mdict['Agenda']])
      if T.markers[mdict['DaemonMU']] and T.markers[mdict['DaemonMU']] >= 1: markers += " {} Daemon MU.".format(T.markers[mdict['DaemonMU']])
      if markers != 'Counters:': markers += '\n'
      else: markers = ''
      debugNotify("Finished Adding Markers. Adding stats...", 4)# Debug               
      stats = ''
      stats += "Cost: {}. ".format(fetchProperty(T, 'Cost'))
      cStat = fetchProperty(T, 'Stat')
      cType = fetchProperty(T, 'Type')
      if cType == 'ICE': stats += "Strength: {}.".format(cStat)
      if cType == 'Program': stats += "MU: {}.".format(fetchProperty(T, 'Requirement'))
      if cType == 'Agenda': stats += "Agenda Points: {}.".format(cStat)
      if cType == 'Asset' or cType == 'Upgrade': stats += "Trash Cost: {}.".format(cStat)
      if includeText: cText = '\n' + fetchProperty(T, 'Rules')
      else: cText = ''
      hostCards = eval(getGlobalVariable('Host Cards'))
      attachmentsList = [Card(cID).name for cID in hostCards if hostCards[cID] == T._id]
      if len(attachmentsList) >= 1: cAttachments = '\nAttachments:' + str(attachmentsList)
      else: cAttachments = ''
      if includeGroup: cGroup = '\n' + pileName(T.group) # Include group is used to inform the player where the card resides in cases where they're selecting cards from multiple groups.
      else: cGroup = ''
      debugNotify("Finished Adding Stats. Going to choice...", 4)# Debug               
      choiceTXT = "{}\n{}\n{}\n{}{}{}{}{}".format(fetchProperty(T, 'name'),cType,getKeywords(T),markers,stats,cAttachments,cText,cGroup)
      targetChoices.append(choiceTXT)
   return targetChoices
   debugNotify("<<< makeChoiceListfromCardList()", 3)
   
def chkWarn(card, Autoscript): # Function for checking that an autoscript announces a warning to the player
   debugNotify(">>> chkWarn(){}".format(extraASDebug(Autoscript))) #Debug
   warning = re.search(r'warn([A-Z][A-Za-z0-9 ]+)-?', Autoscript)
   if debugVerbosity >= 2:  notify("About to check warning")
   if warning:
      if warning.group(1) == 'Discard': 
         if not confirm("This action requires that you discard some cards. Have you done this already?"):
            whisper("--> Aborting action. Please discard the necessary amount of cards and run this action again")
            return 'ABORT'
      if warning.group(1) == 'ReshuffleOpponent': 
         if not confirm("This action will reshuffle your opponent's pile(s). Are you sure?\n\n[Important: Please ask your opponent not to take any clicks with their piles until this clicks is complete or the game might crash]"):
            whisper("--> Aborting action.")
            return 'ABORT'
      if warning.group(1) == 'GiveToOpponent': confirm('This card has an effect which if meant for your opponent. Please use the menu option "pass control to" to give them control.')
      if warning.group(1) == 'Reshuffle': 
         if not confirm("This action will reshuffle your piles. Are you sure?"):
            whisper("--> Aborting action.")
            return 'ABORT'
      if warning.group(1) == 'Workaround':
         notify(":::Note:::{} is using a workaround autoscript".format(me))
      if warning.group(1) == 'LotsofStuff': 
         if not confirm("This card performs a lot of complex clicks that will very difficult to undo. Are you sure you want to proceed?"):
            whisper("--> Aborting action.")
            return 'ABORT'
   debugNotify("<<< chkWarn() gracefully", 3) 
   return 'OK'

def ASclosureTXT(string, count): # Used by Gain and Transfer, to return unicode credits, link etc when it's used in notifications
   debugNotify(">>> ASclosureTXT(). String: {}. Count: {}".format(string, count)) #Debug
 # function that returns a special string with the ANR unicode characters, based on the string and count that we provide it. 
 # So if it's provided with 'Credits', 2, it will return 2 [credits] (where [credits] is either the word or its symbol, depending on the unicode switch.
   if string == 'Base Link': closureTXT = '{} {}'.format(count,uniLink())
   elif string == 'Clicks' or string == 'Click': closureTXT = '{} {}'.format(count,uniClick())
   elif string == 'Credits' or string == 'Credit': 
      if count == 'all': closureTXT = 'all Credits'
      else: closureTXT = uniCredit(count)
   elif string == 'MU': closureTXT = uniMU(count)
   else: closureTXT = "{} {}".format(count,string)
   debugNotify("<<< ASclosureTXT() returning: {}".format(closureTXT), 3)
   return closureTXT
   
def ofwhom(Autoscript, controller = me): 
   debugNotify(">>> ofwhom(){}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("Controller = {}".format(controller),2) #Debug
   if re.search(r'o[fn]Opponent', Autoscript):
      if debugVerbosity >= 2:  notify("Autoscript requirement found!")
      if len(players) > 1:
         if controller == me: # If we're the current controller of the card who's scripts are being checked, then we look for our opponent
            targetPL = None # First we Null the variable, to make sure it is filled.
            for player in players:
               if player.getGlobalVariable('ds') == '': continue # This is a spectator 
               elif player != me and player.getGlobalVariable('ds') != ds:
                  targetPL = player # Opponent needs to be not us, and of a different type. 
                                    # In the future I'll also be checking for teams by using a global player variable for it and having players select their team on startup.
            if not targetPL: # If the variable was not filled, it means the opponent may not have set up their side first. In that case, we try and guess who it is
               for player in players:
                  if len(player.hand) > 0: targetPL = player # If they have at least loaded a deck, we assume they're the opponent, as spectators shouldn't be loading up decks
               if not targetPL: # If we still don't have a probable opponent, we just choose the second player (but there's a chance we'll grab a spectator)
                  targetPL = players[1]
         else: targetPL = me # if we're not the controller of the card we're using, then we're the opponent of the player (i.e. we're trashing their card)
      else: 
         if debugVerbosity >= 1: whisper("There's no valid Opponents! Selecting myself.")
         targetPL = me
   else: 
      if debugVerbosity >= 2:  notify("No autoscript requirement found")
      if len(players) > 1:
         if controller != me: targetPL = controller         
         else: targetPL = me
      else: targetPL = me
   if debugVerbosity >= 3:  notify("<<< ofwhom() returning {}".format(targetPL.name))
   return targetPL
   
def per(Autoscript, card = None, count = 0, targetCards = None, notification = None): # This function goes through the autoscript and looks for the words "per<Something>". Then figures out what the card multiplies its effect with, and returns the appropriate multiplier.
   debugNotify(">>> per(){}".format(extraASDebug(Autoscript))) #Debug
   debugNotify("per() passwd vars: card = {}. count = {}".format(card,count),4)
   div = 1
   ignore = 0
   max = 0 # A maximum of 0 means no limit   
   per = re.search(r'\b(per|upto)(Target|Host|Every)?([A-Z][^-]*)-?', Autoscript) # We're searching for the word per, and grabbing all after that, until the first dash "-" as the variable. 
   if per and not re.search(r'<.*?(per|upto).*?>',Autoscript): # If the  search was successful...
                                                               # We ignore "per" between <> as these are trace effects and are not part of the same script
      debugNotify("per Regex groups: {}".format(per.groups()),3)
      multiplier = 0
      if per.group(2) and (per.group(2) == 'Target' or per.group(2) == 'Every'): # If we're looking for a target or any specific type of card, we need to scour the requested group for targets.
         debugNotify("Checking for Targeted per", 2)
         perTargetRegex = re.search(r'\bper(Target|Every).*?-at(.*)', Autoscript)
         debugNotify("perTargetRegex = {}".format(perTargetRegex.groups()))
         if perTargetRegex.group(1) == 'Target': targetCards = findTarget('Targeted-at{}'.format(perTargetRegex.group(2)))
         else: targetCards = findTarget('AutoTargeted-at{}'.format(perTargetRegex.group(2)))
         if len(targetCards) == 0: pass # If we were expecting some targeted cards but found none, we return a multiplier of 0
         else:
            debugNotify("Looping through {} targetCards".format(len(targetCards)))
            for perCard in targetCards:
               debugNotify("perCard = {}".format(perCard), 2)
               if re.search(r'Marker',per.group(3)):
                  debugNotify("Counting Markers on Card")
                  markerName = re.search(r'Marker{([\w ]+)}',per.group(3)) # I don't understand why I had to make the curly brackets optional, but it seens atTurnStart/End completely eats them when it parses the CardsAS.get(card.model,'')
                  marker = findMarker(perCard, markerName.group(1))
                  if marker: multiplier += perCard.markers[marker]
               elif re.search(r'Property',per.group(3)):
                  debugNotify("Counting Property stat on Card")
                  property = re.search(r'Property{([\w ]+)}',per.group(3))
                  multiplier += num(perCard.properties[property.group(1)])
               else: 
                  multiplier += 1 # If there's no special conditions, then we just add one multiplier per valid (auto)target.
                  debugNotify("Increasing Multiplier by 1 to {}".format(multiplier))
      else: #If we're not looking for a particular target, then we check for everything else.
         debugNotify("Doing no table lookup", 2) # Debug.
         if per.group(3) == 'X': multiplier = count # Probably not needed and the next elif can handle alone anyway.
         elif re.search(r'Marker',per.group(3)):
            markerName = re.search(r'Marker{([\w ]+)}',per.group(3)) # I don't understand why I had to make the curly brackets optional, but it seens atTurnStart/End completely eats them when it parses the CardsAS.get(card.model,'')
            debugNotify("found per Marker requirement: {}".format(markerName.group(1)),4)
            marker = findMarker(card, markerName.group(1))
            if marker:
               debugNotify("found {} Marker(s)".format(card.markers[marker]),4)
               multiplier = card.markers[marker]
            else: 
               debugNotify("Didn't find any relevant Markers",4)
               multiplier = 0
         elif re.search(r'Property',per.group(3)):
            property = re.search(r'Property{([\w ]+)}',per.group(3))
            multiplier = num(card.properties[property.group(1)])
         elif re.search(r'Counter',per.group(3)):
            debugNotify("Checking perCounter", 2) # Debug.   
            counter = re.search(r'Counter{([\w ]+)}',per.group(3))
            if re.search(r'MyCounter',per.group(3)): 
               if card.controller == me: player = me
               else: player = findOpponent()
            else:
               if card.controller == me: player = findOpponent()
               else: player = me
            multiplier = player.counters[counter.group(1)].value
         elif count: multiplier = num(count) * chkPlayer(Autoscript, card.controller, False) # All non-special-rules per<somcething> requests use this formula.
                                                                                              # Usually there is a count sent to this function (eg, number of favour purchased) with which to multiply the end result with
                                                                                              # and some cards may only work when a rival owns or does something.
      debugNotify("Checking ignore", 2) # Debug.            
      ignS = re.search(r'-ignore([0-9]+)',Autoscript)
      if ignS: ignore = num(ignS.group(1))
      debugNotify("Checking div", 2) # Debug.            
      divS = re.search(r'-div([0-9]+)',Autoscript)
      if divS: div = num(divS.group(1))
      debugNotify("Checking max") # Debug.            
      maxS = re.search(r'-max([0-9]+)',Autoscript)
      if maxS: max = num(maxS.group(1))
   else: 
      debugNotify("no per")
      multiplier = 1
   finalMultiplier = (multiplier - ignore) / div
   if max and finalMultiplier > max: 
      debugNotify("Reducing Multiplier to Max",2)
      finalMultiplier = max
   debugNotify("<<< per() with Multiplier: {}".format((multiplier - ignore) / div), 2) # Debug
   return finalMultiplier

def ifHave(Autoscript,controller = me,silent = False):
# A functions that checks if a player has a specific property at a particular level or not and returns True/False appropriately
   debugNotify(">>> ifHave(){}".format(extraASDebug(Autoscript))) #Debug
   Result = True
   if re.search(r'isSilentHaveChk',Autoscript): silent = True
   ifHave = re.search(r"\bif(I|Opponent)(Have|Hasnt)([0-9]+)([A-Za-z ]+)",Autoscript)
   if ifHave:
      debugNotify("ifHave groups: {}".format(ifHave.groups()), 3)
      if ifHave.group(1) == 'I':
         if controller == me: player = me
         else: player = findOpponent()
      else: 
         if controller == me: player = findOpponent()
         else: player = me
      count = num(ifHave.group(3))
      property = ifHave.group(4)
      if ifHave.group(2) == 'Have': # 'Have' means that we're looking for a counter value that is equal or higher than the count
         if not player.counters[property].value >= count: 
            Result = False # If we're looking for the player having their counter at a specific level and they do not, then we return false
            if not silent: delayed_whisper(":::ERROR::: You need at least {} {} to use this effect".format(property,count))
      else: # Having a 'Hasn't' means that we're looking for a counter value that is lower than the count.
         if not player.counters[property].value < count: 
            Result = False
            if not silent: delayed_whisper(":::ERROR::: You need at least {} {} to use this effect".format(property,count))
   debugNotify("<<< ifHave() with Result: {}".format(Result), 3) # Debug
   return Result # If we don't have an ifHave clause, then the result is always True      
      
def ifVarSet(Autoscript):
# A functions that checks if a shared variable has been set to a certain value before allowing a script to proceed.
   debugNotify(">>> ifVarSet(){}".format(extraASDebug(Autoscript))) #Debug
   Result = True
   ifVar = re.search(r"\bifVar([0-9A-Za-z ]+)_SetTo_([0-9A-Za-z ]+)",Autoscript)
   if ifVar:
      debugNotify("ifVar groups: {}".format(ifVar.groups()), 3)
      ASVars = eval(getGlobalVariable('AutoScript Variables'))
      if ASVars.get(ifVar.group(1),'NULL') != ifVar.group(2): Result = False
   debugNotify("<<< ifVarSet() with Result: {}".format(Result), 3) # Debug
   return Result # If we don't have an ifHave clause, then the result is always True      
      
def chkRunningStatus(autoS): # Checks a script to see if it requires a run to be in progress and returns True or False if it passes the check.
   debugNotify(">>> chkRunningStatus() with autoS = {}".format(autoS)) #Debug
   Result = True
   runRegex = re.search(r'whileRunning([A-Za-z&]+)?', autoS)
   if runRegex:
      if debugVerbosity >= 2:
         try: notify("runRegex group(1) = {}".format(runRegex.group(1)))
         except: notify(":::ERROR::: while checking runRegex.group(1)")
      statusRegex = re.search(r'running([A-Za-z&]+)',getGlobalVariable('status')) # This global variable holds the status of the game. I.e. if there's a run ongoing or not.
      if not statusRegex: Result = False # Some autoscripted abilities only work while a run is in progress (e.g. Spinal Modem.)
      elif runRegex.group(1) and runRegex.group(1) != statusRegex.group(1): Result = False # If the script only works while running a specific server, and we're not, then abort.
   debugNotify("<<< chkRunningStatus() with Result: {}".format(Result), 3) # Debug
   return Result
   
def chkPlayer(Autoscript, controller, manual, targetChk = False, reversePlayerChk = False): # Function for figuring out if an autoscript is supposed to target an opponent's cards or ours.
# Function returns 1 if the card is not only for rivals, or if it is for rivals and the card being activated it not ours.
# This is then multiplied by the multiplier, which means that if the card activated only works for Rival's cards, our cards will have a 0 gain.
# This will probably make no sense when I read it in 10 years...
   debugNotify(">>> chkPlayer(). Controller is: {}".format(controller)) #Debug
   try:
      if targetChk: # If set to true, it means we're checking from the findTarget() function, which needs a different keyword in case we end up with two checks on a card's controller on the same script
         byOpponent = re.search(r'targetOpponents', Autoscript)
         byMe = re.search(r'targetMine', Autoscript)
      else:
         byOpponent = re.search(r'(byOpponent|duringOpponentTurn|forOpponent)', Autoscript)
         byMe = re.search(r'(byMe|duringMyTurn|forMe)', Autoscript)
      if manual or len(players) == 1: # If there's only one player, we always return true for debug purposes.
         debugNotify("Succeeded at Manual/Debug", 2)
         validPlayer = 1 #manual means that the clicks was called by a player double clicking on the card. In which case we always do it.
      elif not byOpponent and not byMe: 
         debugNotify("Succeeded at Neutral", 2)   
         validPlayer = 1 # If the card has no restrictions on being us or a rival.
      elif byOpponent and controller != me: 
         debugNotify("Succeeded at byOpponent", 2)   
         validPlayer =  1 # If the card needs to be played by a rival.
      elif byMe and controller == me: 
         debugNotify("Succeeded at byMe", 2)   
         validPlayer =  1 # If the card needs to be played by us.
      else: 
         debugNotify("Failed all checks", 2) # Debug
         validPlayer =  0 # If all the above fail, it means that we're not supposed to be triggering, so we'll return 0 whic
      if not reversePlayerChk: 
         debugNotify("<<< chkPlayer() (not reversed)", 3) # Debug
         return validPlayer
      else: # In case reversePlayerChk is set to true, we want to return the opposite result. This means that if a scripts expect the one running the effect to be the player, we'll return 1 only if the one running the effect is the opponent. See Decoy at Dantoine for a reason
         debugNotify("<<< chkPlayer() (reversed)", 3) # Debug      
         if validPlayer == 0: return 1
         else: return 0
   except: 
      notify("!!!ERROR!!! Null value on chkPlayer()")
      return 0
   
def chkTagged(Autoscript, silent = False):
### Check if the action needs the player or his opponent to be targeted
   debugNotify(">>> chkTagged(). Autoscript is: {}".format(Autoscript))
   if ds == 'corp': runnerPL = findOpponent()
   else: runnerPL = me
   regexTag = re.search(r'ifTagged([0-9]+)', Autoscript)
   if regexTag and runnerPL.Tags < num(regexTag.group(1)) and not re.search(r'doesNotBlock', Autoscript): #See if the target needs to be tagged a specific number of times.
      if not silent:
         if regexTag.group(1) == '1': whisper("The runner needs to be tagged for you to use this action")
         else: whisper("The Runner needs to be tagged {} times for you to to use this action".format(regexTag.group(1)))
      return 'ABORT'
   return 'OK'

def chkRunStatus(Autoscript): # Function for figuring out if an autoscript is supposed to work only when a central or remote was run or not.
   debugNotify(">>> chkRunStatus(). Autoscript is: {}".format(Autoscript)) #Debug
   runCentral = getGlobalVariable('Central Run')
   runRemote = getGlobalVariable('Remote Run')
   debugNotify("runCentral = {}, runRemote = {}".format(runCentral,runRemote))
   validCard = True
   if re.search(r'-ifHasRunAny',Autoscript) and runCentral == 'False' and runRemote == 'False': 
      debugNotify("Rejecting because no server was run")
      validCard = False
   if re.search(r'-ifHasRunCentral',Autoscript) and runCentral == 'False': 
      debugNotify("Rejecting because Central Server not run")
      validCard = False
   if re.search(r'-ifHasRunRemote',Autoscript) and runRemote == 'False': 
      debugNotify("Rejecting because Remote Server not run")
      validCard = False
   if re.search(r'-ifHasSucceededAny',Autoscript) and runCentral != 'Success' and runRemote != 'Success': 
      debugNotify("Rejecting because no server was run successfully")
      validCard = False
   if re.search(r'-ifHasSucceededCentral',Autoscript) and runCentral != 'Success': 
      debugNotify("Rejecting because Central Server not run successfully")
      validCard = False
   if re.search(r'-ifHasSucceededRemote',Autoscript) and runRemote != 'Success': 
      debugNotify("Rejecting because Remote Server not run successfully")
      validCard = False
   if re.search(r'-ifHasnotRunAny',Autoscript) and (runCentral != 'False' or runRemote != 'False'): 
      debugNotify("Rejecting because any server was run")
      validCard = False
   if re.search(r'-ifHasnotRunCentral',Autoscript) and runCentral != 'False': 
      debugNotify("Rejecting because Central Server was run")
      validCard = False
   if re.search(r'-ifHasnotRunRemote',Autoscript) and runRemote != 'False': 
      debugNotify("Rejecting because Remote Server was run")
      validCard = False
   if re.search(r'-ifHasnotSucceededAny',Autoscript) and (runCentral == 'Success' or runRemote == 'Success'): 
      debugNotify("Rejecting because any server was run successfully")
      validCard = False
   if re.search(r'-ifHasnotSucceededCentral',Autoscript) and runCentral == 'Success': 
      debugNotify("Rejecting because Central Server was run successfully")
      validCard = False
   if re.search(r'-ifHasnotSucceededRemote',Autoscript) and runRemote == 'Success': 
      debugNotify("Rejecting because Remote Server was run successfully")
      validCard = False
   debugNotify("<<< chkRunStatus(). validCard is: {}".format(validCard)) #Debug
   return validCard
   
########NEW FILE########
__FILENAME__ = CardScripts
### ANR CARD SCRIPTS ###
# 5 Equal Signs (=) signifiies a break between the description (what you're currently reading) and the code
# 5 Dashes  (-) signifies a break between the card name, the GUID and the card scripts. The card name is ignored by the code, only the GUID and Scripts are used.
# 5 Plus Signs (+) signifies a break between AutoActions and AutoScripts for the same card
# 5 Dots (.) signifies a break between different cards.
# Do not edit below the line
ScriptsLocal = '''
=====
Virus Scan
-----
23473bd3-f7a5-40be-8c66-7d35796b6031
-----

+++++
A3B0G0T0:CustomScript
.....
HQ
-----
81cba950-9703-424f-9a6f-af02e0203762
-----

+++++
A1B0G0T0:RunEnd-isSilent$$RunHQ
.....
R&D
-----
fbb865c9-fccc-4372-9618-ae83a47101a2
-----

+++++
A1B0G0T0:RunEnd-isSilent$$RunR&D
.....
Archives
-----
47597fa5-cc0c-4451-943b-9a14417c2007
-----

+++++
A1B0G0T0:RunEnd-isSilent$$RunArchives
.....
Remote Server
-----
d59fc50c-c727-4b69-83eb-36c475d60dcb
-----

+++++
A1B0G0T0:RunEnd-isSilent$$RunRemote
.....
Accelerated Beta Test
-----
bc0f047c-01b1-427f-a439-d451eda01055
-----
onScore:CustomScript
+++++
	
.....
Access to Globalsec
-----
bc0f047c-01b1-427f-a439-d451eda01052
-----
whileInstalled:Gain1Base Link
+++++
	
.....
Account Siphon
-----
bc0f047c-01b1-427f-a439-d451eda01018
-----
onPlay:RunHQ||atSuccessfulRun:Lose5Credits-ofOpponent-isOptional-isAlternativeRunResult$$Gain2Credits-perX$$Gain2Tags||atJackOut:TrashMyself-isSilent
+++++
	
.....
Adonis Campaign
-----
bc0f047c-01b1-427f-a439-d451eda01056
-----
onRez:Put12Credits||atTurnStart:Transfer3Credits-byMe$$TrashMyself-ifEmpty
+++++
	
.....
Aesop's Pawnshop
-----
bc0f047c-01b1-427f-a439-d451eda01047
-----

+++++
A0B0G0T2:TrashTarget-Targeted-targetMine$$Gain3Credits	
.....
Aggressive Negotiation
-----
bc0f047c-01b1-427f-a439-d451eda01097
-----

+++++
	
.....
Aggressive Secretary
-----
bc0f047c-01b1-427f-a439-d451eda01057
-----
onAccess:UseCustomAbility-ifInstalled-isOptional-pauseRunner
+++++
A0B2G0T0:TrashMulti-Targeted-atProgram-onAccess
.....
Akamatsu Mem Chip
-----
bc0f047c-01b1-427f-a439-d451eda01038
-----
whileInstalled:Gain1MU
+++++

.....
Akitaro Watanabe
-----
bc0f047c-01b1-427f-a439-d451eda01079
-----

+++++
A0B0G0T0:RezTarget-Targeted-isICE-payCost-reduc2
.....
Anonymous Tip
-----
bc0f047c-01b1-427f-a439-d451eda01083
-----
onPlay:Draw3Cards
+++++
	
.....
Archer
-----
bc0f047c-01b1-427f-a439-d451eda01101
-----
onRez:ExileTarget-Targeted-atAgenda
+++++
A0B0G0T0:Gain2Credits-isSubroutine||A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Archived Memories
-----
bc0f047c-01b1-427f-a439-d451eda01058
-----
onPlay:Retrieve1Cards-fromArchives-doNotReveal
+++++
	
.....
Armitage Codebusting
-----
bc0f047c-01b1-427f-a439-d451eda01053
-----
onInstall:Put12Credits
+++++
A1B0G0T0:Transfer2Credits$$TrashMyself-ifEmpty	
.....
AstroScript Pilot Program
-----
bc0f047c-01b1-427f-a439-d451eda01081
-----
onScore:Put1Agenda
+++++
A0B0G0T0:Remove1Agenda-isCost$$Put1Advancement-Targeted	
.....
Aurora
-----
bc0f047c-01b1-427f-a439-d451eda01025
-----

+++++
A0B2G0T0:SimplyAnnounce{break barrier subroutine}||A0B2G0T0:Put3PlusOne	
.....
Bank Job
-----
bc0f047c-01b1-427f-a439-d451eda01029
-----
onInstall:Put8Credits||atSuccessfulRun:RequestInt-isOptional-isAlternativeRunResult$$Transfer1Credits-perX-ifSuccessfulRunRemote$$TrashMyself-ifEmpty
+++++
	
.....
Battering Ram
-----
bc0f047c-01b1-427f-a439-d451eda01042
-----

+++++
A0B2G0T0:SimplyAnnounce{break up to 2 barrier subroutines}||A0B1G0T0:Put1PlusOne
.....
Beanstalk Royalties
-----
bc0f047c-01b1-427f-a439-d451eda01098
-----
onPlay:Gain3Credits
+++++
	
.....
Biotic Labor
-----
bc0f047c-01b1-427f-a439-d451eda01059
-----
onPlay:Gain2Clicks
+++++
	
.....
Breaking News
-----
bc0f047c-01b1-427f-a439-d451eda01082
-----
onScore:Gain2Tags-onOpponent$$Put1BreakingNews||atTurnEnd:Remove1BreakingNews-isCost-byMe$$Lose2Tags-onOpponent
+++++
	
.....
Cell Portal
-----
bc0f047c-01b1-427f-a439-d451eda01074
-----

+++++
A0B0G0T0:SimplyAnnounce{deflects the runner to the outermost piece of ice}-isSubroutine$$DerezMyself	
.....
Chum
-----
bc0f047c-01b1-427f-a439-d451eda01075
-----

+++++
A0B0G0T0:Put2PlusOne-Targeted-atICE-isSubroutine||A0B0G0T0:Inflict3NetDamage-onOpponent-isSubroutine	
.....
Closed Accounts
-----
bc0f047c-01b1-427f-a439-d451eda01084
-----
onPlay:Lose999Credits-onOpponent-ifTagged1
+++++
	
.....
Corporate Troubleshooter
-----
bc0f047c-01b1-427f-a439-d451eda01065
-----

+++++
A0B0G0T1:RequestInt$$Lose1Credits-perX-isCost$$Put1PlusOne-perX-Targeted-atICE-isRezzed
.....
Corroder
-----
bc0f047c-01b1-427f-a439-d451eda01007
-----

+++++
A0B1G0T0:SimplyAnnounce{break barrier subroutine}||A0B1G0T0:Put1PlusOne	
.....
Crash Space
-----
bc0f047c-01b1-427f-a439-d451eda01030
-----
onInstall:Put2Credits||whileInstalled:Reduce#CostDeltag-affectsAll-excludeDummy-forMe||atTurnPreStart:Refill2Credits-excludeDummy-duringMyTurn||onDamage:CreateDummy-with3protectionMeatDMG-trashCost$$TrashMyself-isSilent
+++++
A0B0G0T1:CreateDummy-with3protectionMeatDMG-trashCost
.....
Crypsis
-----
bc0f047c-01b1-427f-a439-d451eda01051
-----

+++++
A0B1G0T0:SimplyAnnounce{break ice subroutine}||A0B1G0T0:Put1PlusOne||A0B0G0T0:Remove1Virus||A1B0G0T0:Put1Virus
.....
Cyberfeeder
-----
bc0f047c-01b1-427f-a439-d451eda01005
-----
onInstall:Put1Credits-isSilent||whileInstalled:Reduce#CostUse-affectsIcebreaker-forMe||whileInstalled:Reduce#CostInstall-affectsVirus-forMe||atTurnPreStart:Refill1Credits-duringMyTurn
+++++
	
.....
Data Dealer
-----
bc0f047c-01b1-427f-a439-d451eda01031
-----

+++++
A1B0G0T0:ExileTarget-Targeted-isScored-targetMine$$Gain9Credits	
.....
Data Mine
-----
bc0f047c-01b1-427f-a439-d451eda01076
-----

+++++
A0B0G0T1:Inflict1NetDamage-onOpponent-isSubroutine	
.....
Data Raven
-----
bc0f047c-01b1-427f-a439-d451eda01088
-----

+++++
A0B0G0T0:Gain1Tags-onOpponent||A0B0G0T0:Trace3-isSubroutine-traceEffects<Put1Power,None>||A0B0G0T0:Remove1Power-isCost$$Gain1Tags-onOpponent	
.....
Datasucker
-----
bc0f047c-01b1-427f-a439-d451eda01008
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunHQ||atSuccessfulRun:Put1Virus-ifSuccessfulRunR&D||atSuccessfulRun:Put1Virus-ifSuccessfulRunArchives
+++++
A0B0G0T0:Remove1Virus-isCost$$Put1MinusOne-Targeted-atICE	
.....
Decoy
-----
bc0f047c-01b1-427f-a439-d451eda01032
-----

+++++
A0B0G0T1:Lose1Tags-isPenalty
.....
Deja Vu
-----
bc0f047c-01b1-427f-a439-d451eda01002
-----
onPlay:Retrieve1Card-fromHeap||onPlay:Retrieve2Cards-fromHeap-grabVirus
+++++
	
.....
Demolition Run
-----
bc0f047c-01b1-427f-a439-d451eda01003
-----
onPlay:RunGeneric
+++++
	
.....
Desperado
-----
bc0f047c-01b1-427f-a439-d451eda01024
-----
whileInstalled:Gain1MU||atSuccessfulRun:Gain1Credits
+++++
	
.....
Diesel
-----
bc0f047c-01b1-427f-a439-d451eda01034
-----
onPlay:Draw3Cards
+++++
	
.....
Djinn
-----
bc0f047c-01b1-427f-a439-d451eda01009
-----
onInstall:Put3DaemonMU-isSilent
+++++
A0B0G0T0:PossessTarget-Targeted-atProgram_and_nonIcebreaker-targetMine||A1B1G0T0:Retrieve1Card-grabVirus$$ShuffleStack
.....
Easy Mark
-----
bc0f047c-01b1-427f-a439-d451eda01019
-----
onPlay:Gain3Credits
+++++
	
.....
Enigma
-----
bc0f047c-01b1-427f-a439-d451eda01111
-----

+++++
A0B0G0T0:Lose1Clicks-onOpponent-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Experiential Data
-----
bc0f047c-01b1-427f-a439-d451eda01066
-----

+++++
	
.....
Femme Fatale
-----
bc0f047c-01b1-427f-a439-d451eda01026
-----
onInstall:Put1Femme Fatale-Targeted-isICE-isOptional
+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B2G0T0:Put1PlusOne||A0B0G0T0:RequestInt-Msg{How many subroutines does the target ice have?}$$Lose1Credits-perX-isCost$$SimplyAnnounce{bypass target ice}	
.....
Forged Activation Orders
-----
bc0f047c-01b1-427f-a439-d451eda01020
-----

+++++
	
.....
Gabriel Santiago
-----
bc0f047c-01b1-427f-a439-d451eda01017
-----
atSuccessfulRun:Gain2Credits-ifSuccessfulRunHQ-onlyOnce
+++++
	
.....
Ghost Branch
-----
bc0f047c-01b1-427f-a439-d451eda01087
-----
onAccess:Gain1Tags-onOpponent-perMarker{Advancement}-isOptional-ifInstalled-pauseRunner
+++++
A0B0G0T0:Gain1Tags-onOpponent-perMarker{Advancement}-onAccess	
.....
Gordian Blade
-----
bc0f047c-01b1-427f-a439-d451eda01043
-----

+++++
A0B1G0T0:SimplyAnnounce{break code gate subroutine}||A0B1G0T0:Put1PlusOne	
.....
Grimoire
-----
bc0f047c-01b1-427f-a439-d451eda01006
-----
whileInstalled:Gain2MU||whileInPlay:Put1Virus-foreachCardInstall-onTriggerCard-typeVirus
+++++
A0B0G0T0:Put1Virus-Targeted-atProgram_and_Virus
.....
Haas-Bioroid
-----
bc0f047c-01b1-427f-a439-d451eda01054
-----
whileInPlay:Gain1Credits-foreachCardInstall-byMe-onlyOnce
+++++
	
.....
Hadrian's Wall
-----
bc0f047c-01b1-427f-a439-d451eda01102
-----

+++++
A0B0G0T0:RunEnd-isSubroutine	
.....
Hedge Fund
-----
bc0f047c-01b1-427f-a439-d451eda01110
-----
onPlay:Gain9Credits
+++++
	
.....
Heimdall 1.0
-----
bc0f047c-01b1-427f-a439-d451eda01061
-----

+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Hostile Takeover
-----
bc0f047c-01b1-427f-a439-d451eda01094
-----
onScore:Gain7Credits$$Gain1Bad Publicity
+++++
	
.....
Hunter
-----
bc0f047c-01b1-427f-a439-d451eda01112
-----

+++++
A0B0G0T0:Trace3-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>
.....
Ice Carver
-----
bc0f047c-01b1-427f-a439-d451eda01015
-----

+++++
	
.....
Ice Wall
-----
bc0f047c-01b1-427f-a439-d451eda01103
-----

+++++
A0B0G0T0:RunEnd-isSubroutine	
.....
Ichi 1.0
-----
bc0f047c-01b1-427f-a439-d451eda01062
-----

+++++
A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine||A0B0G0T0:Trace1-isSubroutine-traceEffects<Gain1Tags-onOpponent++Inflict1BrainDamage-onOpponent,None>	
.....
Infiltration
-----
bc0f047c-01b1-427f-a439-d451eda01049
-----
onPlay:CustomScript
+++++
	
.....
Inside Job
-----
bc0f047c-01b1-427f-a439-d451eda01021
-----
onPlay:RunGeneric
+++++
	
.....
Jinteki
-----
bc0f047c-01b1-427f-a439-d451eda01067
-----
whileInPlay:Inflict1NetDamage-onOpponent-foreachAgendaScored||whileInPlay:Inflict1NetDamage-onOpponent-foreachAgendaLiberated
+++++
	
.....
Kate "Mac" McCaffrey
-----
bc0f047c-01b1-427f-a439-d451eda01033
-----
whileInstalled:Reduce1CostInstall-affectsHardware-onlyOnce-forMe||whileInstalled:Reduce1CostInstall-affectsProgram-onlyOnce-forMe||whileInPlay:Pass-foreachCardInstall-typeProgram_or_Hardware-byMe-onlyOnce
+++++
	
.....
Lemuria Codecracker
-----
bc0f047c-01b1-427f-a439-d451eda01023
-----

+++++
A1B1G0T0:ExposeTarget-Targeted-isUnrezzed	
.....
Magnum Opus
-----
bc0f047c-01b1-427f-a439-d451eda01044
-----

+++++
A1B0G0T0:Gain2Credits	
.....
Matrix Analyzer
-----
bc0f047c-01b1-427f-a439-d451eda01089
-----

+++++
A0B1G0T0:Put1Advancement-Targeted||A0B0G0T0:Trace2-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>
.....
Medium
-----
bc0f047c-01b1-427f-a439-d451eda01010
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunR&D
+++++
	
.....
Melange Mining Corp
-----
bc0f047c-01b1-427f-a439-d451eda01108
-----

+++++
A3B0G0T0:Gain7Credits	
.....
Mimic
-----
bc0f047c-01b1-427f-a439-d451eda01011
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}	
.....
Modded
-----
bc0f047c-01b1-427f-a439-d451eda01035
-----
onPlay:InstallTarget-DemiAutoTargeted-atProgram_or_Hardware-fromHand-choose1-payCost-reduc3
+++++
	
.....
NBN
-----
bc0f047c-01b1-427f-a439-d451eda01080
-----
atTurnPreStart:Refill2Credits-duringMyTurn||whileRezzed:Reduce#CostTrace-affectsAll-forMe
+++++
	
.....
Net Shield
-----
bc0f047c-01b1-427f-a439-d451eda01045
-----
onDamage:Lose1Credits-isCost$$Put1protectionNetDMG-onlyOnce-isPriority
+++++
A0B1G0T2:Put1protectionNetDMG
.....
Neural EMP
-----
bc0f047c-01b1-427f-a439-d451eda01072
-----
onPlay:Inflict1NetDamage-onOpponent
+++++
	
.....
Neural Katana
-----
bc0f047c-01b1-427f-a439-d451eda01077
-----

+++++
A0B0G0T0:Inflict3NetDamage-onOpponent-isSubroutine	
.....
Ninja
-----
bc0f047c-01b1-427f-a439-d451eda01027
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B3G0T0:Put5PlusOne	
.....
Nisei MK II
-----
bc0f047c-01b1-427f-a439-d451eda01068
-----
onScore:Put1Agenda
+++++
A0B0G0T0:Remove1Agenda-isCost$$RunEnd	
.....
Noise
-----
bc0f047c-01b1-427f-a439-d451eda01001
-----
whileInPlay:Draw1Card-toTrash-ofOpponent-foreachCardInstall-typeVirus-byMe
+++++
	
.....
PAD Campaign
-----
bc0f047c-01b1-427f-a439-d451eda01109
-----
atTurnStart:Gain1Credits-duringMyTurn
+++++
	
.....
Parasite
-----
bc0f047c-01b1-427f-a439-d451eda01012
-----
atTurnStart:Put1Virus-duringMyTurn||Placement:ICE-isRezzed
+++++
	
.....
Pipeline
-----
bc0f047c-01b1-427f-a439-d451eda01046
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B2G0T0:Put1PlusOne	
.....
Posted Bounty
-----
bc0f047c-01b1-427f-a439-d451eda01095
-----
onScore:Gain1Bad Publicity-isOptional$$Gain1Tags-onOpponent$$ExileMyself
+++++
	
.....
Precognition
-----
bc0f047c-01b1-427f-a439-d451eda01073
-----
onPlay:CustomScript
+++++
	
.....
Priority Requisition
-----
bc0f047c-01b1-427f-a439-d451eda01106
-----
onScore:RezTarget-Targeted-atICE
+++++
	
.....
Private Security Force
-----
bc0f047c-01b1-427f-a439-d451eda01107
-----

+++++
A1B0G0T0:Inflict1MeatDamage-onOpponent-ifTagged1	
.....
Project Junebug
-----
bc0f047c-01b1-427f-a439-d451eda01069
-----
onAccess:Lose1Credits-isCost-isOptional-ifInstalled-pauseRunner$$Inflict2NetDamage-onOpponent-perMarker{Advancement}
+++++
A0B1G0T0:Inflict2NetDamage-onOpponent-perMarker{Advancement}-onAccess
.....
Psychographics
-----
bc0f047c-01b1-427f-a439-d451eda01085
-----
onPlay:RequestInt$$Lose1Credits-perX-isCost$$Put1Advancement-perX-Targeted
+++++
	
.....
Rabbit Hole
-----
bc0f047c-01b1-427f-a439-d451eda01039
-----
whileInstalled:Gain1Base Link||onInstall:CustomScript
+++++
	
.....
Red Herrings
-----
bc0f047c-01b1-427f-a439-d451eda01091
-----

+++++
	
.....
Research Station
-----
bc0f047c-01b1-427f-a439-d451eda01105
-----
onRez:Gain2Hand Size||onTrash:Lose2Hand Size-ifActive
+++++
	
.....
Rototurret
-----
bc0f047c-01b1-427f-a439-d451eda01064
-----

+++++
A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Sacrificial Construct
-----
bc0f047c-01b1-427f-a439-d451eda01048
-----

+++++
A0B0G0T1:SimplyAnnounce{prevent an installed program or hardware from being trashed}	
.....
SanSan City Grid
-----
bc0f047c-01b1-427f-a439-d451eda01092
-----

+++++
	
.....
Scorched Earth
-----
bc0f047c-01b1-427f-a439-d451eda01099
-----
onPlay:Inflict4MeatDamage-onOpponent-ifTagged1
+++++
	
.....
SEA Source
-----
bc0f047c-01b1-427f-a439-d451eda01086
-----
onPlay:Trace3-traceEffects<Gain1Tags-onOpponent,None>
+++++

.....
Security Subcontract
-----
bc0f047c-01b1-427f-a439-d451eda01096
-----

+++++
A1B0G0T0:TrashTarget-Targeted-atICE-targetMine-isRezzed$$Gain4Credits	
.....
Shadow
-----
bc0f047c-01b1-427f-a439-d451eda01104
-----

+++++
A0B0G0T0:Gain2Credits-isSubroutine||A0B0G0T0:Trace3-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>
.....
Shipment from Kaguya
-----
bc0f047c-01b1-427f-a439-d451eda01100
-----
onPlay:Put1Advancement-Targeted
+++++
	
.....
Shipment from Mirrormorph
-----
bc0f047c-01b1-427f-a439-d451eda01060
-----
onPlay:InstallMulti-Targeted-atnonOperation-fromHand
+++++
	
.....
Snare!
-----
bc0f047c-01b1-427f-a439-d451eda01070
-----
onAccess:Lose4Credits-isCost-isOptional$$Inflict3NetDamage-onOpponent$$Gain1Tags-onOpponent
+++++
A0B4G0T0:Inflict3NetDamage-onOpponent-onAccess$$Gain1Tags-onOpponent
.....
Sneakdoor Beta
-----
bc0f047c-01b1-427f-a439-d451eda01028
-----

+++++
A1B0G0T0:RunArchives-feintToHQ	
.....
Special Order
-----
bc0f047c-01b1-427f-a439-d451eda01022
-----
onPlay:Retrieve1Card-grabIcebreaker$$ShuffleStack
+++++
	
.....
Stimhack
-----
bc0f047c-01b1-427f-a439-d451eda01004
-----
onPlay:RunGeneric$$Put9Credits||whileRunning:Reduce#CostAll-affectsAll-forMe||atJackOut:Inflict1BrainDamage-nonPreventable$$TrashMyself
+++++
	
.....
Sure Gamble
-----
bc0f047c-01b1-427f-a439-d451eda01050
-----
onPlay:Gain9Credits
+++++
	
.....
The Maker's Eye
-----
bc0f047c-01b1-427f-a439-d451eda01036
-----
onPlay:RunR&D
+++++
	
.....
The Personal Touch
-----
bc0f047c-01b1-427f-a439-d451eda01040
-----
onInstall:Put1PlusOnePerm-Targeted-atIcebreaker||Placement:Icebreaker-targetMine
+++++
	
.....
The Toolbox
-----
bc0f047c-01b1-427f-a439-d451eda01041
-----
whileInstalled:Gain2MU$$Gain2Base Link||onInstall:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileRezzed:Reduce#CostUse-affectsIcebreaker-forMe
+++++
	
.....
Tinkering
-----
bc0f047c-01b1-427f-a439-d451eda01037
-----
onPlay:Put1Keyword:Sentry-Targeted-isICE-isSilent$$Put1Keyword:Code Gate-Targeted-isICE-isSilent$$Put1Keyword:Barrier-Targeted-isICE-isSilent$$Put1Tinkering-Targeted-isICE
+++++
	
.....
Tollbooth
-----
bc0f047c-01b1-427f-a439-d451eda01090
-----

+++++
A0B0G0T0:UseCustomAbility||A0B0G0T0:RunEnd-isSubroutine	
.....
Viktor 1.0
-----
bc0f047c-01b1-427f-a439-d451eda01063
-----

+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Wall of Static
-----
bc0f047c-01b1-427f-a439-d451eda01113
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Wall of Thorns
-----
bc0f047c-01b1-427f-a439-d451eda01078
-----

+++++
A0B0G0T0:Inflict2NetDamage-onOpponent-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Weyland Consortium
-----
bc0f047c-01b1-427f-a439-d451eda01093
-----
whileInPlay:Gain1Credits-foreachCardPlay-typeTransaction-byMe
+++++
	
.....
Wyldside
-----
bc0f047c-01b1-427f-a439-d451eda01016
-----
atTurnStart:Draw2Cards-duringMyTurn$$Lose1Clicks
+++++
	
.....
Wyrm
-----
bc0f047c-01b1-427f-a439-d451eda01013
-----

+++++
A0B3G0T0:SimplyAnnounce{break ice subroutine}||A0B1G0T0:Put1MinusOne-Targeted-atICE||A0B1G0T0:Put1PlusOne	
.....
Yog.0
-----
bc0f047c-01b1-427f-a439-d451eda01014
-----

+++++
A0B0G0T0:SimplyAnnounce{break code gate subroutine}	
.....
Zaibatsu Loyalty
-----
bc0f047c-01b1-427f-a439-d451eda01071
-----

+++++
A0B1G0T0:SimplyAnnounce{prevent card from being exposed}||A0B0G0T1:SimplyAnnounce{prevent card from being exposed}
......
Ash 2X3ZB9CY
-----
bc0f047c-01b1-427f-a439-d451eda02013
-----

+++++
A0B0G0T0:Trace4-traceEffects<SimplyAnnounce{stop the runner from accessing anymore cards},None>
.....
Braintrust
-----
bc0f047c-01b1-427f-a439-d451eda02014
-----
onScore:Put1Agenda-perMarker{Advancement}-ignore3-div2||whileScored:ReduceXCostRez-affectsICE-perMarker{Agenda}-forMe
+++++

.....
Caduceus
-----
bc0f047c-01b1-427f-a439-d451eda02019
-----

+++++
A0B0G0T0:Trace3-isSubroutine-traceEffects<Gain3Credits,None>||A0B0G0T0:Trace2-isSubroutine-traceEffects<RunEnd,None>
.....
Cortez Chip
-----
bc0f047c-01b1-427f-a439-d451eda02005
-----

+++++
A0B0G0T1:Put1Cortez Chip-Targeted-isICE
.....
Draco
-----
bc0f047c-01b1-427f-a439-d451eda02020
-----
onRez:RequestInt-Msg{How many Power counters do you want to add on Draco?}$$Lose1Credits-perX-isCost-actiontypeUSE$$Put1PlusOnePerm-perX
+++++
A0B0G0T0:Trace2-isSubroutine-traceEffects<Gain1Tags-onOpponent++RunEnd,None>
.....
Imp
-----
bc0f047c-01b1-427f-a439-d451eda02003
-----
onInstall:Put2Virus
+++++
A0B0G0T2:Remove1Virus-isCost$$SimplyAnnounce{trash an accessed card}
.....
Janus 1.0
-----
bc0f047c-01b1-427f-a439-d451eda02012
-----

+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine
.....
Mandatory Upgrades
-----
bc0f047c-01b1-427f-a439-d451eda02011
-----
whileScored:Gain1Max Click||onScore:Gain1Clicks
+++++

.....
Morning Star
-----
bc0f047c-01b1-427f-a439-d451eda02004
-----

+++++
A0B1G0T0:SimplyAnnounce{break any number of barrier subroutines}
.....
Peacock
-----
bc0f047c-01b1-427f-a439-d451eda02006
-----

+++++
A0B2G0T0:SimplyAnnounce{break code gate subroutine}||A0B2G0T0:Put3PlusOne
.....
Plascrete Carapace
-----
bc0f047c-01b1-427f-a439-d451eda02009
-----
onInstall:Put4Power||onDamage:Remove1Power-isCost$$TrashMyself-ifEmpty$$CreateDummy-with1protectionMeatDMG-doNotTrash-trashCost
+++++
A0B0G0T0:Remove1Power-isCost$$TrashMyself-ifEmpty$$CreateDummy-with1protectionMeatDMG-doNotTrash-trashCost
.....
Project Atlas
-----
bc0f047c-01b1-427f-a439-d451eda02018
-----
onScore:Put1Agenda-perMarker{Advancement}-ignore3
+++++
A0B0G0T0:Remove1Agenda-isCost$$Retrieve1Card$$ShuffleStack
.....
Restructured Datapool
-----
bc0f047c-01b1-427f-a439-d451eda02016
-----

+++++
A1B0G0T0:Trace2e-traceEffects<Gain1Tags-onOpponent,None>
.....
Snowflake
-----
bc0f047c-01b1-427f-a439-d451eda02015
-----

+++++
A0B0G0T0:Psi-psiEffects<RunEnd,None>-isSubroutine
.....
Spinal Modem
-----
bc0f047c-01b1-427f-a439-d451eda02002
-----
onInstall:Put2Credits-isSilent||whileInstalled:Gain1MU||atTurnPreStart:Refill2Credits-duringMyTurn||whileRezzed:Reduce#CostUse-affectsIcebreaker-forMe||whileRunning:Inflict1BrainDamage-foreachUnavoidedTrace-byMe
+++++

.....
The Helpful AI
-----
bc0f047c-01b1-427f-a439-d451eda02008
-----
whileInstalled:Gain1Base Link
+++++
A0B0G0T1:Put2PlusOne-Targeted-atIcebreaker
.....
TMI
-----
bc0f047c-01b1-427f-a439-d451eda02017
-----
onRez:Trace2-traceEffects<None,DerezMyself>
+++++
A0B0G0T0:RunEnd
.....
Whizzard
-----
bc0f047c-01b1-427f-a439-d451eda02001
-----
atTurnPreStart:Refill3Credits-duringMyTurn||Reduce#CostTrash-affectsAll-forMe
+++++

.....
Haas-Bioroid
-----
bc0f047c-01b1-427f-a439-d451eda02010
-----
whileInPlay:Put1PlusOnePerm-foreachCardRezzed-onTriggerCard-typeBioroid_and_ICE||whileInPlay:Remove1PlusOnePerm-foreachCardDerezzed-onTriggerCard-typeBioroid_and_ICE
+++++

.....
ZU.13 Key Master
-----
bc0f047c-01b1-427f-a439-d451eda02007
-----
ConstantAbility:Cloud2Link
+++++
A0B1G0T0:SimplyAnnounce{break code gate subroutine}||A0B1G0T0:Put1PlusOne
.....
Amazon Industrial Zone
-----
bc0f047c-01b1-427f-a439-d451eda02038
-----

+++++
A0B0G0T0:RezTarget-Targeted-isICE-payCost-reduc3
.....
Big Brother
-----
bc0f047c-01b1-427f-a439-d451eda02035
-----
onPlay:Gain2Tags-onOpponent-ifTagged1
+++++

.....
ChiLo City Grid
-----
bc0f047c-01b1-427f-a439-d451eda02036
-----

+++++
A0B0G0T0:Gain1Tags-onOpponent
.....
Compromised Employee
-----
bc0f047c-01b1-427f-a439-d451eda02025
-----
onInstall:Put1Credits-isSilent||atTurnPreStart:Refill1Credits-duringMyTurn||whileInstalled:Reduce#CostTrace-affectsAll-forMe||whileInPlay:Gain1Credits-foreachCardRezzed-typeICE
+++++

.....
Dyson Mem Chip
-----
bc0f047c-01b1-427f-a439-d451eda02028
-----
whileInstalled:Gain1Base Link$$Gain1MU
+++++

.....
E3 Feedback Implants
-----
bc0f047c-01b1-427f-a439-d451eda02024
-----

+++++
A0B1G0T0:SimplyAnnounce{break 1 additional subroutine on the current ICE}
.....
Encryption Protocol
-----
bc0f047c-01b1-427f-a439-d451eda02029
-----
whileRezzed:Increase1CostTrash-affectsAll-forOpponent-ifInstalled
+++++

.....
Executive Retreat
-----
bc0f047c-01b1-427f-a439-d451eda02039
-----
onScore:Put1Agenda-isSilent$$ReshuffleHQ
+++++
A1B0G0T0:Remove1Agenda-isCost$$Draw5Cards
.....
Fetal AI
-----
bc0f047c-01b1-427f-a439-d451eda02032
-----
onAccess:Inflict2NetDamage-onOpponent||onLiberation:Lose2Credits-isCost-onOpponent
+++++

.....
Freelancer
-----
bc0f047c-01b1-427f-a439-d451eda02040
-----
onPlay:TrashMulti-Targeted-atResource
+++++

.....
Jinteki
-----
bc0f047c-01b1-427f-a439-d451eda02031
-----

+++++

.....
Liberated Account
-----
bc0f047c-01b1-427f-a439-d451eda02022
-----
onInstall:Put16Credits
+++++
A1B0G0T0:Transfer4Credits$$TrashMyself-ifEmpty	
.....
Notoriety
-----
bc0f047c-01b1-427f-a439-d451eda02026
-----
onPlay:Gain1Agenda Points$$ScoreMyself$$Put1Scored-isSilent
+++++

.....
Power Grid Overload
-----
bc0f047c-01b1-427f-a439-d451eda02037
-----
onPlay:Trace2
+++++
A0B0G0T0:TrashTarget-Targeted-atHardware
.....
Satellite Uplink
-----
bc0f047c-01b1-427f-a439-d451eda02023
-----
onPlay:ExposeMulti-Targeted-isUnrezzed
+++++

.....
Sensei
-----
bc0f047c-01b1-427f-a439-d451eda02034
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Sherlock 1.0
-----
bc0f047c-01b1-427f-a439-d451eda02030
-----

+++++
A0B0G0T0:Trace4||A0B0G0T0:UninstallTarget-toStack-Targeted-atProgram
.....
Snowball
-----
bc0f047c-01b1-427f-a439-d451eda02027
-----
atJackOut:Remove999Snowball
+++++
A0B1G0T0:SimplyAnnounce{break barrier subroutine}$$Put1Snowball||A0B1G0T0:Put1PlusOne	
.....
Trick of Light
-----
bc0f047c-01b1-427f-a439-d451eda02033
-----

+++++

.....
Vamp
-----
bc0f047c-01b1-427f-a439-d451eda02021
-----
onPlay:RunHQ||atSuccessfulRun:RequestInt-Msg{How many credits do you want to burn?}$$Lose1Credits-perX-isCost-isOptional-isAlternativeRunResult$$Lose1Credits-perX-ofOpponent$$Gain1Tags$$TrashMyself-ifSuccessfulRunHQ
+++++

.....
Nerve Agent
-----
bc0f047c-01b1-427f-a439-d451eda02041
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunHQ
+++++
	
.....
Joshua B.
-----
bc0f047c-01b1-427f-a439-d451eda02042
-----

+++++
A0B0G0T2:Gain1Clicks$$Infect1Joshua Enhancement-isSilent
.....
Dinosaurus
-----
bc0f047c-01b1-427f-a439-d451eda02048
-----
onInstall:Put1Dinosaurus Hosted-isSilent||ConstantAbility:CountsAsDaemon||onHost:Put2PlusOnePerm-isSilent
+++++
A0B0G0T0:PossessTarget-Targeted-atIcebreaker_and_nonAI-targetMine
.....
Emergency Shutdown
-----
bc0f047c-01b1-427f-a439-d451eda02043
-----
onPlay:DerezTarget-Targeted-atICE
+++++

.....
Muresh Bodysuit
-----
bc0f047c-01b1-427f-a439-d451eda02044
-----
onDamage:Put1protectionMeatDMG-onlyOnce-isPriority
+++++
A0B0G0T2:Put1protectionMeatDMG
.....
Snitch
-----
bc0f047c-01b1-427f-a439-d451eda02045
-----
atJackOut:Remove999Snitched-isSilent
+++++
A0B0G0T0:ExposeTarget-Targeted-isICE-restrictionMarkerSnitched
.....
Public Sympathy
-----
bc0f047c-01b1-427f-a439-d451eda02050
-----
whileInstalled:Gain2Hand Size
+++++

.....
Chimera
-----
bc0f047c-01b1-427f-a439-d451eda02060
-----
onRez:ChooseKeyword{Code Gate|Barrier|Sentry}||atTurnEnd:DerezMyself$$Remove1Keyword:Sentry-isSilent$$Remove1Keyword:Barrier-isSilent$$Remove1Keyword:Code Gate-isSilent
+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Commercialization
-----
bc0f047c-01b1-427f-a439-d451eda02058
-----
onPlay:Gain1Credits-perTargetMarker{Advancement}-Targeted-atICE-isICE
+++++

.....
Edge of World
-----
bc0f047c-01b1-427f-a439-d451eda02053
-----
onAccess:Lose3Credits-isCost-isOptional-ifInstalled$$RequestInt-Msg{How many ICE are installed on this server?}$$Inflict1BrainDamage-onOpponent-perX
+++++
A0B3G0T0:RequestInt-Msg{How many ICE are installed on this server?}-onAccess-ifInstalled$$Inflict1BrainDamage-onOpponent-perX
.....
Marked Accounts
-----
bc0f047c-01b1-427f-a439-d451eda02055
-----
atTurnStart:Transfer1Credits-duringMyTurn
+++++
A1B0G0T0:Put3Credits
.....
Personal Workshop
-----
bc0f047c-01b1-427f-a439-d451eda02049
-----
atTurnStart:CustomScript
+++++
A1B0G0T0:CustomScript
.....
Pop-up Window
-----
bc0f047c-01b1-427f-a439-d451eda02056
-----

+++++
A0B0G0T0:Gain1Credits||A0B0G0T0:Lose1Credits-ofOpponent-isCost-isSubroutine||A0B0G0T0:RunEnd-isSubroutine
.....
Private Contracts
-----
bc0f047c-01b1-427f-a439-d451eda02059
-----
onRez:Put14Credits
+++++
A1B0G0T0:Transfer2Credits$$TrashMyself-ifEmpty	
.....
Project Vitruvius
-----
bc0f047c-01b1-427f-a439-d451eda02051
-----
onScore:Put1Agenda-perMarker{Advancement}-ignore3
+++++
A0B0G0T0:Remove1Agenda-isCost$$Retrieve1Cards-fromArchives-doNotReveal
.....
Test Run
-----
bc0f047c-01b1-427f-a439-d451eda02047
-----
onPlay:Retrieve1Card-grabProgram-toTable-with1Test Run$$ShuffleStack||onPlay:Retrieve1Card-fromHeap-grabProgram-toTable-with1Test Run
+++++
A0B0G0T0:UninstallTarget-toStack-AutoTargeted-atProgram-hasMarker{Test Run}$$TrashMyself
.....
Viper
-----
bc0f047c-01b1-427f-a439-d451eda02052
-----

+++++
A0B0G0T0:Trace3-isSubroutine-traceEffects<Lose1Clicks-ofOpponent,None>||A0B0G0T0:Trace3-isSubroutine-traceEffects<RunEnd,None>
.....
Woodcutter
-----
bc0f047c-01b1-427f-a439-d451eda02057
-----

+++++
A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine	
.....
Chaos Theory
-----
bc0f047c-01b1-427f-a439-d451eda02046
-----
onStartup:Gain1MU-isSilent
+++++

.....
Disrupter
-----
bc0f047c-01b1-427f-a439-d451eda02061
-----

+++++
A0B0G0T1:SimplyAnnounce{Prevent the Trace and initiate it again with a base strength of 0}
.....
Force of Nature
-----
bc0f047c-01b1-427f-a439-d451eda02062
-----

+++++
A0B2G0T0:SimplyAnnounce{break up to 2 code gate subroutines}||A0B1G0T0:Put1PlusOne	
.....
Scrubber
-----
bc0f047c-01b1-427f-a439-d451eda02063
-----
onInstall:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileInstalled:Reduce#CostTrash-affectsAll-forMe
+++++

.....
Doppelganger
-----
bc0f047c-01b1-427f-a439-d451eda02064
-----
whileInstalled:Gain1MU
+++++
A0B0G0T2:RunEnd-isSilent$$RunGeneric
.....
Crescentus
-----
bc0f047c-01b1-427f-a439-d451eda02065
-----

+++++
A0B0G0T1:DerezTarget-Targeted-atICE-isRezzed
.....
Deus X
-----
bc0f047c-01b1-427f-a439-d451eda02066
-----
onDamage:Put100protectionNetDMG-trashCost-excludeDummy
+++++
A0B0G0T1:SimplyAnnounce{break any number of AP subroutines}-excludeDummy||A0B0G0T1:CreateDummy-with100protectionNetDMG-trashCost
.....
All Nighter
-----
bc0f047c-01b1-427f-a439-d451eda02067
-----

+++++
A1B0G0T1:Gain2Clicks
.....
Inside Man
-----
bc0f047c-01b1-427f-a439-d451eda02068
-----
onInstall:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileInstalled:Reduce#CostInstall-affectsHardware-forMe
+++++

.....
Underworld Contact
-----
bc0f047c-01b1-427f-a439-d451eda02069
-----
atTurnStart:Gain1Credits-ifIHave2Base Link-duringMyTurn
+++++

.....
Green Level Clearance
-----
bc0f047c-01b1-427f-a439-d451eda02070
-----
onPlay:Gain3Credits$$Draw1Card
+++++

.....
Hourglass
-----
bc0f047c-01b1-427f-a439-d451eda02071
-----

+++++
A0B0G0T0:Lose1Clicks-onOpponent-isSubroutine
.....
Dedicated Server
-----
bc0f047c-01b1-427f-a439-d451eda02072
-----
onRez:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileRezzed:Reduce#CostRez-affectsICE-forMe
+++++

.....
Bullfrog
-----
bc0f047c-01b1-427f-a439-d451eda02073
-----

+++++
A0B0G0T0:Psi-psiEffects<UseCustomAbility,None>-isSubroutine
.....
Uroboros
-----
bc0f047c-01b1-427f-a439-d451eda02074
-----

+++++
A0B0G0T0:Trace4-isSubroutine-traceEffects<SimplyAnnounce{stop the runner from making any more runs this turn},None>||A0B0G0T0:Trace4-isSubroutine-traceEffects<RunEnd,None>
.....
Net Police
-----
bc0f047c-01b1-427f-a439-d451eda02075
-----
onRez:Put1Credits-perOpponentCounter{Base Link}||atTurnPreStart:Refill1Credits-perOpponentCounter{Base Link}-duringMyTurn||whileRezzed:Reduce#CostTrace-affectsAll-forMe
+++++

.....
Weyland Consortium: Because we Build it
-----
bc0f047c-01b1-427f-a439-d451eda02076
-----
atTurnPreStart:Refill1Credits-duringMyTurn||whileRezzed:Reduce#CostAdvancement-affectsICE-forMe
+++++

.....
Government Contracts
-----
bc0f047c-01b1-427f-a439-d451eda02077
-----

+++++
A2B0G0T0:Gain4Credits
.....
Tyrant
-----
bc0f047c-01b1-427f-a439-d451eda02078
-----

+++++
A0B0G0T0:RunEnd-isSubroutine	
.....
Oversight AI
-----
bc0f047c-01b1-427f-a439-d451eda02079
-----
Placement:ICE-isUnrezzed||onPlay:RezTarget-Targeted-atICE-isUnrezzed
+++++

.....
False Lead
-----
bc0f047c-01b1-427f-a439-d451eda02080
-----

+++++
A0B0G0T0:Lose2Clicks-ofOpponent-isExact$$ExileMyself
.....
Surge
-----
bc0f047c-01b1-427f-a439-d451eda02081
-----
onPlay:Put2Virus-Targeted-atProgram
+++++

.....
Xanadu
-----
bc0f047c-01b1-427f-a439-d451eda02082
-----
whileInstalled:Increase1CostRez-affectsAll-isICE-forOpponent
+++++

.....
Andromeda
-----
bc0f047c-01b1-427f-a439-d451eda02083
-----
onStartup:Draw4Cards-isSilent||onMulligan:Draw4Cards-isSilent
+++++

.....
Networking
-----
bc0f047c-01b1-427f-a439-d451eda02084
-----
onPlay:Lose1Tags
+++++
A0B1G0T0:UninstallMyself-isSilent$$SimplyAnnounce{take networking back into their grip}
.....
HQ Interface
-----
bc0f047c-01b1-427f-a439-d451eda02085
-----

+++++

.....
Pheromones
-----
bc0f047c-01b1-427f-a439-d451eda02086
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunHQ||onRez:Put1Credits-perMarker{Virus}||atTurnPreStart:Refill1Credits-perMarker{Virus}-duringMyTurn||whileRunningHQ:Reduce#CostAll-affectsAll-forMe
+++++

.....
Quality Time
-----
bc0f047c-01b1-427f-a439-d451eda02087
-----
onPlay:Draw5Cards
+++++

.....
Replicator
-----
bc0f047c-01b1-427f-a439-d451eda02088
-----
whileInPlay:UseCustomAbility-foreachCardInstall-onTriggerCard-typeHardware-byMe
+++++

.....
Creeper
-----
bc0f047c-01b1-427f-a439-d451eda02089
-----
ConstantAbility:Cloud2Link
+++++
A0B2G0T0:SimplyAnnounce{break sentry subroutine}||A0B1G0T0:Put1PlusOne
.....
Kraken
-----
bc0f047c-01b1-427f-a439-d451eda02090
-----
onPlay:SimplyAnnounce{force the corp to trash a piece of ice on target server}
+++++

.....
Kati Jones
-----
bc0f047c-01b1-427f-a439-d451eda02091
-----

+++++
A1B0G0T0:Put3Credits-onlyOnce||A1B0G0T0:Transfer999Credits-onlyOnce
.....
Eve Campaign
-----
bc0f047c-01b1-427f-a439-d451eda02092
-----
onRez:Put16Credits||atTurnStart:Transfer2Credits-byMe$$TrashMyself-ifEmpty
+++++

.....
Rework
-----
bc0f047c-01b1-427f-a439-d451eda02093
-----
onPlay:ReworkTarget-Targeted-fromHand$$ShuffleR&D-isSilent
+++++

.....
Whirlpool
-----
bc0f047c-01b1-427f-a439-d451eda02094
-----

+++++
A0B0G0T1:SimplyAnnounce{prevent the runner from jacking out for the remainder of this run}
.....
Hosukai Grid
-----
bc0f047c-01b1-427f-a439-d451eda02095
-----

+++++
A0B0G0T0:Inflict1NetDamage-onOpponent
.....
Data Hound
-----
bc0f047c-01b1-427f-a439-d451eda02096
-----

+++++
A0B0G0T0:Trace2-isSubroutine-traceEffects<SimplyAnnounce{sniff the runner's stack},None>||A0B0G0T0:UseCustomAbility

.....
Bernice Mai
-----
bc0f047c-01b1-427f-a439-d451eda02097
-----

+++++
A0B0G0T0:Trace5-traceEffects<Gain1Tags-onOpponent,TrashMyself>
.....
Salvage
-----
bc0f047c-01b1-427f-a439-d451eda02098
-----

+++++
A0B0G0T0:Trace2-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>
.....
Simone Diego
-----
bc0f047c-01b1-427f-a439-d451eda02099
-----
onRez:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn
+++++
A1B0G0T0:Remove1Credits-isCost$$Put1Advancement-Targeted
.....
Foxfire
-----
bc0f047c-01b1-427f-a439-d451eda02100
-----
onPlay:Trace7-traceEffects<SimplyAnnounce{trash 1 virtual resource, or 1 link},None>
+++++
A0B0G0T0:TrashTarget-Targeted-atVirtual_and_Resource_or_Link
.....

Retrieval Run
-----
bc0f047c-01b1-427f-a439-d451eda02101
-----
onPlay:RunArchives||atSuccessfulRun:Retrieve1Card-fromHeap-grabProgram-toTable-isOptional-isAlternativeRunResult$$TrashMyself-ifSuccessfulRunArchives-isSilent
+++++

.....

Darwin
-----
bc0f047c-01b1-427f-a439-d451eda02102
-----
atTurnStart:Lose1Credits-isCost-isOptional-duringMyTurn$$Put1Virus
+++++
A0B2G0T0:SimplyAnnounce{break ICE subroutine}
.....

Data Leak Reversal
-----
bc0f047c-01b1-427f-a439-d451eda02103
-----
onInstall:UninstallMyself-ifHasnotSucceededCentral$$Gain1Clicks-isSilent-ifHasnotSucceededCentral
+++++
A1B0G0T0:Draw1Card-toTrash-ofOpponent-ifTagged1
.....

Faerie
-----
bc0f047c-01b1-427f-a439-d451eda02104
-----

+++++
A0B0G0T0:SimplyAnnounce{break sentry subroutine}||A0B1G0T0:Put1PlusOne
.....

Mr. Li
-----
bc0f047c-01b1-427f-a439-d451eda02105
-----

+++++
A1B0G0T0:CustomScript
.....

Indexing
-----
bc0f047c-01b1-427f-a439-d451eda02106
-----
onPlay:RunR&D||atSuccessfulRun:CustomScript-isAlternativeRunResult-isOptional-ifSuccessfulRunR&D$$TrashMyself-ifSuccessfulRunR&D-isSilent
+++++

.....

R&D Interface
-----
bc0f047c-01b1-427f-a439-d451eda02107
-----

+++++

.....

Deep Thought
-----
bc0f047c-01b1-427f-a439-d451eda02108
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunR&D||atTurnStart:CustomScript-duringMyTurn
+++++

.....

New Angeles City Hall
-----
bc0f047c-01b1-427f-a439-d451eda02109
-----
whileInstalled:TrashMyself-foreachAgendaLiberated
+++++
A0B2G0T0:Lose1Tags
.....

Eli 1.0
-----
bc0f047c-01b1-427f-a439-d451eda02110
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....

Ruhr Valley
-----
bc0f047c-01b1-427f-a439-d451eda02111
-----

+++++
A0B0G0T0:Autoaction
.....

Ronin
-----
bc0f047c-01b1-427f-a439-d451eda02112
-----

+++++
A1B0G0T1:Remove4Advancement-isCost$$Inflict3NetDamage-onOpponent
.....

Midori
-----
bc0f047c-01b1-427f-a439-d451eda02113
-----

+++++
A0B0G0T0:CustomScript
.....

NBN: The World is Yours
-----
bc0f047c-01b1-427f-a439-d451eda02114
-----
onStartup:Gain1Hand Size-isSilent||onMulligan:Gain1Hand Size-isSilent
+++++

.....

Project Beale
-----
bc0f047c-01b1-427f-a439-d451eda02115
-----
onScore:Put1Agenda-perMarker{Advancement}-ignore3-div2||whileScored:Gain1Agenda Points-perMarker{Agenda}
+++++

.....

Midseason Replacements
-----
bc0f047c-01b1-427f-a439-d451eda02116
-----
onPlay:Trace6-traceEffects<Gain1Tags-perX-onOpponent,None>
+++++

.....

Flare
-----
bc0f047c-01b1-427f-a439-d451eda02117
-----

+++++
A0B0G0T0:Trace6-isSubroutine-traceEffects<Inflict2MeatDamage-nonPreventable-onOpponent++RunEnd,None>||A0B0G0T0:TrashTarget-Targeted-atHardware
.....

Dedicated Response Team
-----
bc0f047c-01b1-427f-a439-d451eda02118
-----
atJackOut:Inflict2MeatDamage-onOpponent-ifTagged1-ifSuccessfulRunAny
+++++

.....

Burke Bugs
-----
bc0f047c-01b1-427f-a439-d451eda02119
-----

+++++
A0B0G0T0:Trace0-isSubroutine-traceEffects<SimplyAnnounce{force the runner to trash a program},None>
.....

Corporate War
-----
bc0f047c-01b1-427f-a439-d451eda02120
-----
onScore:Gain7Credits-ifIHave7Credits-isSilentHaveChk$$Lose999Credits-ifIHasnt7Credits-isSilentHaveChk
+++++

.....
Cerebral Imaging: Infinite Frontiers
-----
bc0f047c-01b1-427f-a439-d451eda03001
-----
atTurnPreEnd:SetTo1Hand Size-perMyCounter{Credits}-duringMyTurn
+++++

.....
Next Design: Guarding the Net
-----
bc0f047c-01b1-427f-a439-d451eda03003
-----

+++++
A0B0G0T0:InstallMulti-Targeted-atICE-fromHand||A0B0G0T0:Draw999Cards
.....
Director Haas' Pet Project
-----
bc0f047c-01b1-427f-a439-d451eda03004
-----
onScore:CustomScript
+++++

.....
Efficiency Committee
-----
bc0f047c-01b1-427f-a439-d451eda03005
-----
onScore:Put3Agenda
+++++
A1B0G0T0:Remove1Agenda-isCost$$Gain2Clicks
.....
Project Wotan
-----
bc0f047c-01b1-427f-a439-d451eda03006
-----
onScore:Put3Agenda||atJackOut:Remove999Project Wotan ETR-AutoTargeted-atICE-hasMarker{Project Wotan ETR}
+++++
A0B0G0T0:Remove1Agenda-isCost$$Put1Project Wotan ETR-Targeted-atICE_and_Bioroid-isRezzed
.....
Sentinel Defense Program
-----
bc0f047c-01b1-427f-a439-d451eda03007
-----
whileScored:Inflict1NetDamage-onOpponent-foreachBrainDMGInflicted
+++++

.....
Alix T4LB07
-----
bc0f047c-01b1-427f-a439-d451eda03008
-----
whileInPlay:Put1Power-foreachCardInstall-byMe
+++++
A1B0G0T1:Gain2Credits-perMarker{Power}
.....
Cerebral Overwriter
-----
bc0f047c-01b1-427f-a439-d451eda03009
-----
onAccess:Lose3Credits-isCost-isOptional-ifInstalled-pauseRunner$$Inflict1BrainDamage-onOpponent-perMarker{Advancement}
+++++
A0B3G0T0:Inflict1BrainDamage-onOpponent-perMarker{Advancement}-onAccess	
.....
Director Haas
-----
bc0f047c-01b1-427f-a439-d451eda03010
-----
onRez:Gain1Clicks$$Gain1Max Click||onTrash:Lose1Max Click-ifActive-ifUnscored$$Lose1Clicks-ifActive-ifUnscored$$ScoreMyself-onOpponent-ifAccessed-ifUnscored-preventTrash-runTrashScriptWhileInactive$$Gain2Agenda Points-onOpponent-ifAccessed-ifUnscored$$Put2Scored-isSilent-ifAccessed-ifUnscored
+++++

.....
Haas Arcology AI
-----
bc0f047c-01b1-427f-a439-d451eda03011
-----

+++++
A1B0G0T0:Remove1Advancement-isCost-onlyOnce$$Gain2Clicks
.....
Thomas Haas
-----
bc0f047c-01b1-427f-a439-d451eda03012
-----

+++++
A0B0G0T1:Gain2Credits-perMarker{Advancement}
.....
Bioroid Efficiency Research
-----
bc0f047c-01b1-427f-a439-d451eda03013
-----
Placement:ICE_and_Bioroid-isUnrezzed||onPlay:RezTarget-Targeted-atICE_and_Bioroid-isUnrezzed||onTrash:DerezHost
+++++

.....
Successful Demonstration
-----
bc0f047c-01b1-427f-a439-d451eda03014
-----
onPlay:Gain7Credits
+++++

.....
Heimdall 2.0
-----
bc0f047c-01b1-427f-a439-d451eda03015
-----

+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine||A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine$$RunEnd||A0B0G0T0:RunEnd-isSubroutine	
.....
Howler
-----
bc0f047c-01b1-427f-a439-d451eda03016
-----
atJackOut:DerezTarget-AutoTargeted-atICE_and_Bioroid-hasMarker{Howler}$$TrashTarget-AutoTargeted-atHowler-hasMarker{Howler}$$Remove1Howler-AutoTargeted-isIce-hasMarker{Howler}
+++++
A0B0G0T0:CustomScript
.....
Ichi 2.0
-----
bc0f047c-01b1-427f-a439-d451eda03017
-----

+++++
A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine||A0B0G0T0:Trace3-isSubroutine-traceEffects<Gain1Tags-onOpponent++Inflict1BrainDamage-onOpponent,None>	
.....
Minelayer
-----
bc0f047c-01b1-427f-a439-d451eda03018
-----

+++++
A0B0G0T0:InstallTarget-Targeted-atICE-fromHand
.....
Viktor 2.0
-----
bc0f047c-01b1-427f-a439-d451eda03019
-----

+++++
A0B0G0T0:Trace2-isSubroutine-traceEffects<Put1Power,None>||A0B0G0T0:RunEnd-isSubroutine||A0B0G0T0:Remove1Power-isCost$$Inflict1BrainDamage-onOpponent
.....
Zed 1.0
-----
bc0f047c-01b1-427f-a439-d451eda03020
-----

+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent
.....
Awakening Center
-----
bc0f047c-01b1-427f-a439-d451eda03021
-----
atJackOut:TrashTarget-AutoTargeted-atICE_and_Bioroid-hasMarker{AwakeningCenter}
+++++
A1B0G0T0:CustomScript
.....
Tyr's Hand
-----
bc0f047c-01b1-427f-a439-d451eda03022
-----

+++++
A0B0G0T1:SimplyAnnounce{prevent a subroutine from being broken on a piece of bioroid ice protecting this server}
.....
Gila Hands Arcology
-----
bc0f047c-01b1-427f-a439-d451eda03023
-----

+++++
A2B0G0T0:Gain3Credits
.....
Levy University
-----
bc0f047c-01b1-427f-a439-d451eda03024
-----

+++++
A1B1G0T0:Retrieve1Card-grabICE$$ShuffleR&D
.....
Server Diagnostics
-----
bc0f047c-01b1-427f-a439-d451eda03025
-----
atTurnStart:Gain2Credits-duringMyTurn||whileRezzed:TrashMyself-foreachCardInstall-isICE
+++++

.....
Bastion
-----
bc0f047c-01b1-427f-a439-d451eda03026
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Datapike
-----
bc0f047c-01b1-427f-a439-d451eda03027
-----

+++++
A0B0G0T0:UseCustomAbility-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Rielle "Kit" Peddler: Transhuman
-----
bc0f047c-01b1-427f-a439-d451eda03028
-----

+++++

.....
Exile: Streethawk
-----
bc0f047c-01b1-427f-a439-d451eda03030
-----

+++++
A0B0G0T0:Draw1Card
.....
Escher
-----
bc0f047c-01b1-427f-a439-d451eda03031
-----
onPlay:RunHQ||atSuccessfulRun:CustomScript-isOptional-isAlternativeRunResult-ifSuccessfulRunHQ||atJackOut:CustomScript
+++++

.....
Exploratory Romp
-----
bc0f047c-01b1-427f-a439-d451eda03032
-----
onPlay:RunGeneric||atSuccessfulRun:Remove3Advancement-DemiAutoTargeted-hasMarker{Advancement}-choose1-isAlternativeRunResult$$TrashMyself-isSilent
+++++
A0B0G0T0:Remove3Advancement-Targeted-hasMarker{Advancement}
.....
Freelance Coding Contract
-----
bc0f047c-01b1-427f-a439-d451eda03033
-----
onPlay:Discard0Card-Targeted-atProgram-fromHand$$Gain2Credits-perX
+++++

.....
Scavenge
-----
bc0f047c-01b1-427f-a439-d451eda03034
-----
onPlay:CustomScript
+++++

.....
Levy AR Lab Access
-----
bc0f047c-01b1-427f-a439-d451eda03035
-----
onPlay:TrashMulti-AutoTargeted-atEvent-hasntMarker{Scored}$$ReshuffleHeap-warnReshuffle$$ReshuffleStack$$Draw5Cards$$ExileMyself
+++++

.....
Monolith
-----
bc0f047c-01b1-427f-a439-d451eda03036
-----
whileInstalled:Gain3MU||onInstall:InstallMulti-Targeted-atProgram-fromHand-payCost-reduc4||onDamage:Discard1Card-isCost-DemiAutoTargeted-atProgram-fromHand-choose1$$Put1protectionNetBrainDMG
+++++
A0B0G0T0:Discard1Card-isCost-DemiAutoTargeted-atProgram-fromHand-choose1$$Put1protectionNetBrainDMG
.....
Feedback Filter
-----
bc0f047c-01b1-427f-a439-d451eda03037
-----
onDamage:Lose3Credits-isCost$$Put1protectionNetDMG-excludeDummy-isSilent||onDamage:CreateDummy-with2protectionBrainDMG-trashCost
+++++
A0B3G0T0:Put1protectionNetDMG-excludeDummy||A0B0G0T1:CreateDummy-with2protectionBrainDMG-trashCost
.....
Clone Chip
-----
bc0f047c-01b1-427f-a439-d451eda03038
-----

+++++
A0B0G0T1:Retrieve1Card-grabProgram-fromHeap-toTable-payCost
.....
Omni-drive
-----
bc0f047c-01b1-427f-a439-d451eda03039
-----
onInstall:Put1DaemonMU-isSilent$$Put1Credits-isSilent||atTurnPreStart:Refill1Credits-duringMyTurn||whileRezzed:Reduce#CostUse-affectsAll-forMe-ifHosted||ConstantAbility:CountsAsDaemon
+++++
A0B0G0T0:PossessTarget-Targeted-atProgram-targetMine
.....
Atman
-----
bc0f047c-01b1-427f-a439-d451eda03040
-----
onInstall:RequestInt-Msg{How many Power counters do you want to add on Atman?}$$Lose1Credits-perX-isCost-actiontypeUSE$$Put1PlusOnePerm-perX
+++++
A0B1G0T0:SimplyAnnounce{break ICE subroutine}
.....
Cloak
-----
bc0f047c-01b1-427f-a439-d451eda03041
-----
onInstall:Put1Credits-isSilent||whileInstalled:Reduce#CostUse-affectsIcebreaker-forMe||atTurnPreStart:Refill1Credits-duringMyTurn
+++++

.....
Dagger
-----
bc0f047c-01b1-427f-a439-d451eda03042
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B0G0T0:Remove1Credits-AutoTargeted-atStealth-isCost$$Put5PlusOne
.....
Chakana
-----
bc0f047c-01b1-427f-a439-d451eda03043
-----
atSuccessfulRun:Put1Virus-ifSuccessfulRunR&D||whileInPlay:Increase1Advancement-perMarker{Virus}-div3-max1
+++++

.....
Cyber-Cypher
-----
bc0f047c-01b1-427f-a439-d451eda03044
-----
onInstall:Put1CyberCypher-Targeted-isServer
+++++
A0B1G0T0:SimplyAnnounce{break code gate subroutine}||A0B1G0T0:Put1PlusOne	
.....
Paricia
-----
bc0f047c-01b1-427f-a439-d451eda03045
-----
onInstall:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileInstalled:Reduce#CostTrash-affectsAsset-forMe
+++++

.....
Self-modifying Code
-----
bc0f047c-01b1-427f-a439-d451eda03046
-----

+++++
A0B2G0T0:TrashMyself$$Retrieve1Card-grabProgram-fromStack-toTable-payCost$$ShuffleStack
.....
Sahasrara
-----
bc0f047c-01b1-427f-a439-d451eda03047
-----
onInstall:Put2Credits-isSilent||atTurnPreStart:Refill2Credits-duringMyTurn||whileRezzed:Reduce#CostInstall-affectsProgram-forMe
+++++

.....
Inti
-----
bc0f047c-01b1-427f-a439-d451eda03048
-----

+++++
A0B1G0T0:SimplyAnnounce{break a barrier subroutine}||A0B2G0T0:Put1PlusOne	
.....
Professional Contacts
-----
bc0f047c-01b1-427f-a439-d451eda03049
-----

+++++
A1B0G0T0:Gain1Credits$$Draw1Card
.....
Borrowed Satellite
-----
bc0f047c-01b1-427f-a439-d451eda03050
-----
whileInstalled:Gain1Hand Size$$Gain1Base Link
+++++

.....
Ice Analyzer
-----
bc0f047c-01b1-427f-a439-d451eda03051
-----
whileInstalled:Reduce#CostInstall-affectsProgram-forMe||whileInPlay:Put1Credits-foreachCardRezzed-typeICE
+++++

.....
Dirty Laundry
-----
bc0f047c-01b1-427f-a439-d451eda03052
-----
onPlay:RunGeneric||atJackOut:Gain5Credits$$TrashMyself-ifSuccessfulRunAny
+++++

.....
Daily Casts
-----
bc0f047c-01b1-427f-a439-d451eda03053
-----
onInstall:Put8Credits||atTurnStart:Transfer2Credits-byMe$$TrashMyself-ifEmpty
+++++

.....
Same Old Thing
-----
bc0f047c-01b1-427f-a439-d451eda03054
-----

+++++
A2B0G0T1:CustomScript
.....
The Source
-----
bc0f047c-01b1-427f-a439-d451eda03055
-----
whileInPlay:Lose3Credits-isCost-foreachAgendaLiberated-typeAgenda||whileInPlay:TrashMyself-foreachAgendaLiberated-typeAgenda||whileInPlay:TrashMyself-foreachAgendaScored||whileInPlay:Increase1Advancement
+++++

.....
Frame Job
-----
bc0f047c-01b1-427f-a439-d451eda04001
-----
onPlay:ExileTarget-Targeted-isScored-targetMine$$Gain1Bad Publicity-onOpponent
+++++

.....
Pawn
-----
bc0f047c-01b1-427f-a439-d451eda04002
-----
CaissaPlace:ICE
+++++
A1B0G0T0:RehostMyself-Targeted-isICE||A0B0G0T0:RehostMyself-Targeted-isICE||A0B0G0T1:InstallTarget-DemiAutoTargeted-atCaissa-fromHand-choose1||A0B0G0T1:Retrieve1Card-fromHeap-grabCaissa-toTable||A0B0G0T0:RehostMyself-Targeted-isICE$$Gain1Credits$$Draw1Cards$$Remove1Test Run-isSilent
.....
Rook
-----
bc0f047c-01b1-427f-a439-d451eda04003
-----
CaissaPlace:ICE
+++++
A1B0G0T0:RehostMyself-Targeted-isICE
.....
Hostage
-----
bc0f047c-01b1-427f-a439-d451eda04004
-----
onPlay:Retrieve1Card-grabConnection$$ShuffleStack||onPlay:Retrieve1Card-grabConnection-toTable-payCost$$ShuffleStack
+++++

.....
Gorman Drip v1
-----
bc0f047c-01b1-427f-a439-d451eda04005
-----
whileInPlay:Put1Virus-foreachCreditClicked-byOpponent||whileInPlay:Put1Virus-foreachCardDrawnClicked-byOpponent
+++++
A1B0G0T1:Gain1Credits-perMarker{Virus}
.....
Lockpick
-----
bc0f047c-01b1-427f-a439-d451eda04006
-----
onInstall:Put1Credits-isSilent||whileInstalled:Reduce#CostUse-affectsDecoder-forMe||atTurnPreStart:Refill1Credits-duringMyTurn
+++++

.....
False Echo
-----
bc0f047c-01b1-427f-a439-d451eda04007
-----

+++++
A0B0G0T1:SimplyAnnounce{force the corporation to rez target ICE or uninstall it to HQ}
.....
Motivation
-----
bc0f047c-01b1-427f-a439-d451eda04008
-----
atTurnStart:CustomScript-duringMyTurn
+++++

.....
John Masanori
-----
bc0f047c-01b1-427f-a439-d451eda04009
-----
atSuccessfulRun:Draw1Card-onlyOnce||atJackOut:Gain1Tags-ifUnsuccessfulRunAny-restrictionMarkerMasanori Unsuccessful
+++++

.....
Project Ares
-----
bc0f047c-01b1-427f-a439-d451eda04010
-----
onScore:Put1Agenda-perMarker{Advancement}-ignore4$$Gain1Bad Publicity-hasOrigMarker{Agenda}
+++++

.....
NEXT Bronze
-----
bc0f047c-01b1-427f-a439-d451eda04011
-----
whileRezzed:Refill1PlusOnePerm-perEveryCard-atNEXT-isICE-isRezzed-foreachCardRezzed-typeNEXT_and_ICE-isSilent||whileRezzed:Remove1PlusOnePerm-foreachCardDerezzed-typeNEXT_and_ICE-isSilent||whileRezzed:Remove1PlusOnePerm-foreachCardTrashed-typeNEXT_and_ICE-isSilent||onDerez:Remove999PlusOnePerm||onTrash:Remove999PlusOnePerm
+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Celebrity Gift
-----
bc0f047c-01b1-427f-a439-d451eda04012
-----
onPlay:CustomScript
+++++

.....
Himitsu-Bako
-----
bc0f047c-01b1-427f-a439-d451eda04013
-----

+++++
A0B1G0T0:UninstallMyself||A0B0G0T0:RunEnd-isSubroutine
.....
Character Assassination
-----
bc0f047c-01b1-427f-a439-d451eda04014
-----
onScore:TrashTarget-DemiAutoTargeted-atResource-choose1
+++++

.....
Jackson Howard
-----
bc0f047c-01b1-427f-a439-d451eda04015
-----

+++++
A1B0G0T0:Draw2Cards||A0B0G0T0:ExileMyself$$Retrieve3Cards-fromArchives-toDeck-upToAmount-doNotReveal$$ShuffleR&D
.....
Invasion of Privacy
-----
bc0f047c-01b1-427f-a439-d451eda04016
-----
onPlay:Trace2-traceEffects<UseCustomAbility,Gain1Bad Publicity>
+++++

.....
Geothermal Fracking
-----
bc0f047c-01b1-427f-a439-d451eda04017
-----
onScore:Put2Agenda
+++++
A1B0G0T0:Remove1Agenda-isCost$$Gain7Credits$$Gain1Bad Publicity
.....
Swarm
-----
bc0f047c-01b1-427f-a439-d451eda04018
-----
onRez:Gain1Bad Publicity
+++++
A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine||A0B0G0T0:Lose3Credits-onOpponent-perMarker{Advancement}
.....
Cyberdex Trial
-----
bc0f047c-01b1-427f-a439-d451eda04019
-----
onPlay:Remove999Virus-AutoTargeted-atProgram-hasMarker{Virus}-targetOpponents
+++++

.....
Grim
-----
bc0f047c-01b1-427f-a439-d451eda04020
-----
onRez:Gain1Bad Publicity
+++++
A0B0G0T0:TrashTarget-Targeted-atProgram-isSubroutine
.....
The Collective
-----
bc0f047c-01b1-427f-a439-d451eda00001
-----
whileInPlay:CustomScript-foreachCardInstall-duringMyTurn||whileInPlay:CustomScript-foreachCardPlay-duringMyTurn||whileInPlay:CustomScript-foreachCardDrawnClicked-duringMyTurn||whileInPlay:CustomScript-foreachCreditClicked-duringMyTurn||whileInPlay:CustomScript-foreachCardAction-duringMyTurn||atRunStart:CustomScript-duringMyTurn||atTurnStart:CustomScript-duringMyTurn
+++++
A0B0G0T0:Gain1Clicks
.....
Laramy Fisk
-----
bc0f047c-01b1-427f-a439-d451eda00002
-----
atSuccessfulRun:Draw1Card-onOpponent-ifSuccessfulRunHQ-onlyOnce-isOptional||atSuccessfulRun:Draw1Card-onOpponent-ifSuccessfulRunR&D-onlyOnce-isOptional||atSuccessfulRun:Draw1Card-onOpponent-ifSuccessfulRunArchives-onlyOnce-isOptional
+++++

.....
Bishop
-----
bc0f047c-01b1-427f-a439-d451eda04021
-----
CaissaPlace:ICE
+++++
A1B0G0T0:RehostMyself-Targeted-isICE

.....
Scheherazade
-----
bc0f047c-01b1-427f-a439-d451eda04022
-----
onInstall:Put1001Scheherazade Hosted-isSilent||onHost:Gain1Credits
+++++
A0B0G0T0:PossessTarget-Targeted-atProgram-targetMine
.....
Hard at Work
-----
bc0f047c-01b1-427f-a439-d451eda04023
-----
atTurnStart:Gain2Credits-duringMyTurn$$Lose1Clicks
+++++

.....
Recon
-----
bc0f047c-01b1-427f-a439-d451eda04024
-----
onPlay:RunGeneric
+++++

.....
Copycat
-----
bc0f047c-01b1-427f-a439-d451eda04025
-----

+++++
A0B0G0T1:CustomScript
.....
Leviathan
-----
bc0f047c-01b1-427f-a439-d451eda04026
-----

+++++
A0B3G0T0:SimplyAnnounce{break up to 3 code gate subroutines}||A0B3G0T0:Put5PlusOne
.....
Eureka!
-----
bc0f047c-01b1-427f-a439-d451eda04027
-----
onPlay:CustomScript
+++++

.....
Record Reconstructor
-----
bc0f047c-01b1-427f-a439-d451eda04028
-----
atSuccessfulRun:Retrieve1Cards-fromArchives-faceUpOnly-toDeck-onOpponent-ifSuccessfulRunArchives-isOptional-isAlternativeRunResult
+++++

.....
Prepaid VoicePAD
-----
bc0f047c-01b1-427f-a439-d451eda04029
-----
onInstall:Put1Credits-isSilent||atTurnPreStart:Refill1Credits-duringMyTurn||whileInstalled:Reduce#CostPlay-affectsEvent-forMe
+++++

.....
Wotan
-----
bc0f047c-01b1-427f-a439-d451eda04030
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Hellion Alpha Test
-----
bc0f047c-01b1-427f-a439-d451eda04031
-----
onPlay:Trace2-traceEffects<SimplyAnnounce{add 1 installed resource to the top of the Runner stack},Gain1Bad Publicity>
+++++
A0B0G0T0:UninstallTarget-toStack-Targeted-atResource$$TrashMyself
.....
Clone Retirement
-----
bc0f047c-01b1-427f-a439-d451eda04032
-----
onScore:Lose1Bad Publicity||onLiberation:Gain1Bad Publicity
+++++

.....
Swordsman
-----
bc0f047c-01b1-427f-a439-d451eda04033
-----

+++++
A0B0G0T0:TrashTarget-Targeted-atProgram_and_AI-isSubroutine||A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine

.....
Shipment from SanSan
-----
bc0f047c-01b1-427f-a439-d451eda04034
-----
onPlay:Put2Advancement-Targeted
+++++

.....
Muckraker
-----
bc0f047c-01b1-427f-a439-d451eda04035
-----
onRez:Gain1Bad Publicity
+++++
A0B0G0T0:Trace1-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>||A0B0G0T0:Trace2-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>||A0B0G0T0:Trace3-isSubroutine-traceEffects<Gain1Tags-onOpponent,None>||A0B0G0T0:RunEnd-isSubroutine
.....
The Cleaners
-----
bc0f047c-01b1-427f-a439-d451eda04036
-----
ConstantAbility:Enhance1MeatDamage-isScored
+++++

.....
Elizabeth Mills
-----
bc0f047c-01b1-427f-a439-d451eda04037
-----
onRez:Lose1Bad Publicity
+++++
A1B0G0T1:TrashTarget-Targeted-atLocation$$Gain1Bad Publicity
.....
Off the Grid
-----
bc0f047c-01b1-427f-a439-d451eda04038
-----
atSuccessfulRun:TrashMyself-ifSuccessfulRunHQ
+++++

.....
Profiteering
-----
bc0f047c-01b1-427f-a439-d451eda04039
-----
onScore:RequestInt-Msg{How much bad publicity do you want to take? (max 3)}$$Gain1Bad Publicity-perX$$Gain5Credits-perX
+++++

.....
Restructure
-----
bc0f047c-01b1-427f-a439-d451eda04040
-----
onPlay:Gain15Credits
+++++

.....
Reina Roja
-----
bc0f047c-01b1-427f-a439-d451eda04041
-----
whileInstalled:Increase1CostRez-affectsAll-isICE-forOpponent-onlyOnce
+++++

.....
Deep Red
-----
bc0f047c-01b1-427f-a439-d451eda04042
-----
whileInstalled:Gain3MU||whileInPlay:Put1Deep Red-foreachCardInstall-onTriggerCard-typeCaissa
+++++

.....
Knight
-----
bc0f047c-01b1-427f-a439-d451eda04043
-----
CaissaPlace:ICE
+++++
A0B2G0T0:SimplyAnnounce{break ICE subroutine}||A1B0G0T0:RehostMyself-Targeted-isICE
.....
Running Interference
-----
bc0f047c-01b1-427f-a439-d451eda04044
-----
onPlay:RunGeneric||whileInPlay:IncreaseSCostRez-affectsAll-isICE-forOpponent||atJackOut:TrashMyself
+++++

.....
Expert Schedule Analyzer
-----
bc0f047c-01b1-427f-a439-d451eda04045
-----
atSuccessfulRun:CustomScript-isOptional-isAlternativeRunResult-ifSuccessfulRunHQ-hasOrigMarker{Running}||atJackOut:Remove1Running-isSilent
+++++
A1B0G0T0:RunHQ$$Put1Running
.....
Grifter
-----
bc0f047c-01b1-427f-a439-d451eda04046
-----
atTurnEnd:Gain1Credits-ifHasSucceededAny-duringMyTurn||atTurnEnd:TrashMyself-ifHasnotSucceededAny-duringMyTurn
+++++

.....
Torch
-----
bc0f047c-01b1-427f-a439-d451eda04047
-----

+++++
A0B1G0T0:SimplyAnnounce{break code gate subroutine}||A0B1G0T0:Put1PlusOne
.....
Woman in the Red Dress
-----
bc0f047c-01b1-427f-a439-d451eda04048
-----
atTurnStart:CustomScript-duringMyTurn
+++++

.....
Raymond Flint (Script in parseNewCounters())
-----
bc0f047c-01b1-427f-a439-d451eda04049
-----

+++++
A0B0G0T1:ExposeTarget-Targeted-isUnrezzed
.....
Isabel McGuire
-----
bc0f047c-01b1-427f-a439-d451eda04050
-----

+++++
A1B0G0T0:UninstallTarget-Targeted
.....
Hudson 1.0
-----
bc0f047c-01b1-427f-a439-d451eda04051
-----

+++++
A0B0G0T0:SimplyAnnounce{stop the Runner from accessing more than 1 card during this run}-isSubroutine
.....
Accelerated Diagnostics
-----
bc0f047c-01b1-427f-a439-d451eda04052
-----
onPlay:CustomScript
+++++

.....
Unorthodox Predictions
-----
bc0f047c-01b1-427f-a439-d451eda04053
-----
onScore:ChooseKeyword{Code Gate|Barrier|Sentry}-simpleAnnounce||atTurnStart:Remove1Keyword:Sentry-isSilent$$Remove1Keyword:Barrier-isSilent$$Remove1Keyword:Code Gate-isSilent
+++++

.....
Sundew
-----
bc0f047c-01b1-427f-a439-d451eda04054
-----

+++++
A0B0G0T0:Gain2Credits
.....
City Surveillance
-----
bc0f047c-01b1-427f-a439-d451eda04055
-----
atTurnStart:CustomScript-duringOpponentTurn
+++++

.....
Snoop
-----
bc0f047c-01b1-427f-a439-d451eda04056
-----

+++++
A0B0G0T0:UseCustomAbility-isFirstCustom||A0B0G0T0:Remove1Power-isCost$$UseCustomAbility-isSecondCustom||A0B0G0T0:Trace3-isSubroutine-traceEffects<Put1Power,None>
.....
Ireress
-----
bc0f047c-01b1-427f-a439-d451eda04057
-----

+++++
A0B0G0T0:Lose1Credits-ofOpponent-isSubroutine
.....
Power Shutdown
-----
bc0f047c-01b1-427f-a439-d451eda04058
-----
onPlay:CustomScript
+++++

.....
Paper Wall
-----
bc0f047c-01b1-427f-a439-d451eda04059
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Interns
-----
bc0f047c-01b1-427f-a439-d451eda04060
-----
onPlay:Retrieve1Card-grabnonOperation-fromArchives-toTable-doNotReveal||onPlay:InstallTarget-DemiAutoTargeted-atnonOperation-fromHand-choose1
+++++

.....
Keyhole
-----
bc0f047c-01b1-427f-a439-d451eda04061
-----
atSuccessfulRun:CustomScript-isAlternativeRunResult-ifSuccessfulRunR&D-hasOrigMarker{Running}||atJackOut:Remove1Running-isSilent
+++++
A1B0G0T0:RunR&D$$Put1Running
.....
Activist Support
-----
bc0f047c-01b1-427f-a439-d451eda04062
-----
atTurnStart:Gain1Tags-ifIHasnt1Tags-duringOpponentTurn||atTurnStart:Gain1Bad Publicity-onOpponent-ifOpponentHasnt1Bad Publicity-duringMyTurn
+++++

.....
Lawyer Up
-----
bc0f047c-01b1-427f-a439-d451eda04063
-----
onPlay:Lose2Tags$$Draw3Cards
+++++

.....
Leverage
-----
bc0f047c-01b1-427f-a439-d451eda04064
-----
onPlay:CustomScript||atTurnStart:TrashMyself-onlyforDummy-duringMyTurn
+++++

.....
Garrote
-----
bc0f047c-01b1-427f-a439-d451eda04065
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B1G0T0:Put1PlusOne	
.....
LLDS Processor
-----
bc0f047c-01b1-427f-a439-d451eda04066
-----
whileInPlay:Put1LLDS Processor-foreachCardInstall-onTriggerCard-typeIcebreaker
+++++

.....
Sharpshooter
-----
bc0f047c-01b1-427f-a439-d451eda04067
-----

+++++
A0B0G0T1:SimplyAnnounce{break any number of destroyer subroutines}||A0B1G0T0:Put2PlusOne
.....
Capstone
-----
bc0f047c-01b1-427f-a439-d451eda04068
-----

+++++
A1B0G0T0:CustomScript
.....
Starlight Crusade Funding
-----
bc0f047c-01b1-427f-a439-d451eda04069
-----
atTurnStart:Lose1Clicks-duringMyTurn
+++++

.....
Rex Campaign
-----
bc0f047c-01b1-427f-a439-d451eda04070
-----
onRez:Put3Power||atTurnStart:Remove1Power-duringMyTurn$$CustomScript
+++++

.....
Fenris
-----
bc0f047c-01b1-427f-a439-d451eda04071
-----
onRez:Gain1Bad Publicity
+++++
A0B0G0T0:Inflict1BrainDamage-onOpponent-isSubroutine||A0B0G0T0:RunEnd-isSubroutine	
.....
Panic Button
-----
bc0f047c-01b1-427f-a439-d451eda04072
-----

+++++
A0B1G0T0:Draw1Card
.....
Shock!
-----
bc0f047c-01b1-427f-a439-d451eda04073
-----
onAccess:Inflict1NetDamage-onOpponent-worksInArchives
+++++

.....
Tsurugi
-----
bc0f047c-01b1-427f-a439-d451eda04074
-----

+++++
A0B0G0T0:RunEnd-isSubroutine||A0B0G0T0:Lose1Credits-isSubroutine||A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine
.....
TGTBT
-----
bc0f047c-01b1-427f-a439-d451eda04075
-----
onAccess:Gain1Tags-onOpponent-worksInArchives
+++++

.....
Sweeps Week
-----
bc0f047c-01b1-427f-a439-d451eda04076
-----
onPlay:CustomScript
+++++

.....
RSVP
-----
bc0f047c-01b1-427f-a439-d451eda04077
-----

+++++
A0B0G0T0:SimplyAnnounce{prevent the Runner from spending any credits for the remainder of this run}
.....
Curtain Wall
-----
bc0f047c-01b1-427f-a439-d451eda04078
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Punitive Counterstrike
-----
bc0f047c-01b1-427f-a439-d451eda04079
-----
onPlay:Trace5-traceEffects<UseCustomAbility,None>
+++++

.....
Veterans Program
-----
bc0f047c-01b1-427f-a439-d451eda04080
-----
onScore:Lose2Bad Publicity
+++++

.....
Chronos Protocol (Jinteki)
-----
bc0f047c-01b1-427f-a439-d451eda00003
-----

+++++

.....
Chronos Protocol (HB)
-----
bc0f047c-01b1-427f-a439-d451eda00004
-----

+++++

.....
Quest Completed
-----
bc0f047c-01b1-427f-a439-d451eda04081
-----
onPlay:CustomScript-Targeted-targetOpponents
+++++

.....
Hemorrhage
-----
bc0f047c-01b1-427f-a439-d451eda04082
-----
atSuccessfulRun:Put1Virus
+++++
A1B0G0T0:Remove2Virus-isCost$$SimplyAnnounce{force the corp to trash one card from their hand}
.....
Tallie Perrault
-----
bc0f047c-01b1-427f-a439-d451eda04083
-----

+++++
A0B0G0T0:Gain1Bad Publicity-onOpponent$$Gain1Tags||A0B0G0T1:Draw1Cards-perOpponentCounter{Bad Publicity}
.....
Executive Wiretaps
-----
bc0f047c-01b1-427f-a439-d451eda04084
-----
onPlay:CustomScript
+++++

.....
Blackguard
-----
bc0f047c-01b1-427f-a439-d451eda04085
-----
whileInstalled:Gain2MU
+++++
A0B0G0T0:SimplyAnnounce{force the corp to rez the accessed card by paying its rez cost, if able.}
.....
CyberSolutions Mem Chip
-----
bc0f047c-01b1-427f-a439-d451eda04086
-----
whileInstalled:Gain2MU
+++++

.....
Alpha
-----
bc0f047c-01b1-427f-a439-d451eda04087
-----

+++++
A0B1G0T0:SimplyAnnounce{break ICE subroutine}||A0B1G0T0:Put1PlusOne	
.....
Omega
-----
bc0f047c-01b1-427f-a439-d451eda04088
-----

+++++
A0B1G0T0:SimplyAnnounce{break ICE subroutine}||A0B1G0T0:Put1PlusOne	
.....
Blackmail
-----
bc0f047c-01b1-427f-a439-d451eda04089
-----
onPlay:Put1Blackmail-AutoTargeted-isUnrezzed-isICE$$RunGeneric||atJackOut:Remove1Blackmail-AutoTargeted-isUnrezzed-isICE
+++++

.....
Blue Level Clearance
-----
bc0f047c-01b1-427f-a439-d451eda04090
-----
onPlay:Gain5Credits$$Draw2Card
+++++

.....
Strongbox
-----
bc0f047c-01b1-427f-a439-d451eda04091
-----

+++++

.....
Toshiyuki Sakai
-----
bc0f047c-01b1-427f-a439-d451eda04092
-----
onAccess:UseCustomAbility-ifInstalled-isOptional-pauseRunner
+++++
A0B0G0T0:UseCustomAbility-ifInstalled
.....
Yagura
-----
bc0f047c-01b1-427f-a439-d451eda04093
-----

+++++
A0B0G0T0:UseCustomAbility-isSubroutine||A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine
.....
Restoring Face
-----
bc0f047c-01b1-427f-a439-d451eda04094
-----
onPlay:TrashTarget-Targeted-atSysop_or_Executive_or_Clone$$Lose2Bad Publicity
+++++
 
.....
Market Research
-----
bc0f047c-01b1-427f-a439-d451eda04095
-----
onScore:Put1Agenda-ifOpponentHave1Tags-isSilentHaveChk||whileScored:Gain1Agenda Points-perMarker{Agenda}
+++++

.....
Wraparound
-----
bc0f047c-01b1-427f-a439-d451eda04096
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
GRNDL
-----
bc0f047c-01b1-427f-a439-d451eda04097
-----
onStartup:Gain5Credits-isSilent$$Gain1Bad Publicity-isSilent
+++++

.....
Vulcan Coverup
-----
bc0f047c-01b1-427f-a439-d451eda04098
-----
onScore:Inflict2MeatDamage-onOpponent||onLiberation:Gain1Bad Publicity
+++++

.....
GRNDL Refinery
-----
bc0f047c-01b1-427f-a439-d451eda04099
-----

+++++
A1B0G0T1:Gain4Credits-perMarker{Advancement}
.....
Subliminal Messaging
-----
bc0f047c-01b1-427f-a439-d451eda04100
-----
onPlay:Gain1Credits$$Gain1Clicks-ifVarSubliminal_SetTo_False$$SetVarSubliminal-ToTrue
+++++

.....
Singularity
-----
bc0f047c-01b1-427f-a439-d451eda04101
-----
onPlay:RunRemote||atSuccessfulRun:SimplyAnnounce{trash all cards in the server}-isAlternativeRunResult$$TrashMyself
+++++

.....
Queen&#039;s Gambit
-----
bc0f047c-01b1-427f-a439-d451eda04102
-----
onPlay:RequestInt-Max3-Msg{How many advancement counters do you want to put on target card?}$$Put1Advancement-perX-Targeted-isUnrezzed$$Gain2Credits-perX
+++++

.....
Dyson Fractal Generator
-----
bc0f047c-01b1-427f-a439-d451eda04103
-----
onInstall:Put1Credits-isSilent||whileInstalled:Reduce#CostUse-affectsFracter-forMe||atTurnPreStart:Refill1Credits-duringMyTurn
+++++

.....
Silencer
-----
bc0f047c-01b1-427f-a439-d451eda04104
-----
onInstall:Put1Credits-isSilent||whileInstalled:Reduce#CostUse-affectsKiller-forMe||atTurnPreStart:Refill1Credits-duringMyTurn
+++++

.....
Savoir-faire
-----
bc0f047c-01b1-427f-a439-d451eda04105
-----

+++++
A0B2G0T0:InstallTarget-DemiAutoTargeted-atProgram-fromHand-payCost-choose1-onlyOnce
.....
Fall Guy
-----
bc0f047c-01b1-427f-a439-d451eda04106
-----

+++++
A0B0G0T1:SimplyAnnounce{prevent an installed resource from being trashed}||A0B0G0T1:Gain2Credits
.....
Power Nap
-----
bc0f047c-01b1-427f-a439-d451eda04107
-----
onPlay:Gain2Credits$$UseCustomAbility
+++++

.....
Paintbrush
-----
bc0f047c-01b1-427f-a439-d451eda04108
-----

+++++
A1B0G0T0:Put1Keyword:Sentry-Targeted-isICE-isRezzed-isSilent$$Put1Keyword:Code Gate-Targeted-isICE-isSilent-isRezzed$$Put1Keyword:Barrier-Targeted-isICE-isSilent-isRezzed$$Put1Paintbrush-Targeted-isICE-isRezzed
.....
Lucky Find
-----
bc0f047c-01b1-427f-a439-d451eda04109
-----
onPlay:Gain9Credits
+++++

.....
Gyri Labyrinth
-----
bc0f047c-01b1-427f-a439-d451eda04110
-----

+++++
A0B0G0T0:Lose2Hand Size-onOpponent-isSubroutine$$Put1Gyri Labyrinth-AutoTargeted-atIdentity-targetOpponents
.....
Reclamation Order
-----
bc0f047c-01b1-427f-a439-d451eda04111
-----
onPlay:CustomScript
+++++

.....
Broadcast Square
-----
bc0f047c-01b1-427f-a439-d451eda04112
-----

+++++
A0B0G0T0:Trace3-traceEffects<Lose1Bad Publicity,None>
.....
Corporate Shuffle
-----
bc0f047c-01b1-427f-a439-d451eda04113
-----
onPlay:ReshuffleHQ$$Draw5Cards
+++++

.....
Caprice Nisei
-----
bc0f047c-01b1-427f-a439-d451eda04114
-----

+++++
A0B0G0T0:Psi-psiEffects<RunEnd,None>
.....
Shinobi
-----
bc0f047c-01b1-427f-a439-d451eda04115
-----
onRez:Gain1Bad Publicity
+++++
A0B0G0T0:Trace1-isSubroutine-traceEffects<Inflict1NetDamage-onOpponent,None>||A0B0G0T0:Trace2-isSubroutine-traceEffects<Inflict2NetDamage-onOpponent,None>||A0B0G0T0:Trace3-isSubroutine-traceEffects<Inflict3NetDamage-onOpponent++RunEnd,None>
.....
Marker
-----
bc0f047c-01b1-427f-a439-d451eda04116
-----

+++++
A0B0G0T0:SimplyAnnounce{give the next piece of ICE an End the Run subroutine}-isSubroutine
.....
Hive
-----
bc0f047c-01b1-427f-a439-d451eda04117
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Witness Tampering
-----
bc0f047c-01b1-427f-a439-d451eda04118
-----
onPlay:Lose2Bad Publicity
+++++

.....
NAPD Contract
-----
bc0f047c-01b1-427f-a439-d451eda04119
-----
onLiberation:Lose4Credits-isCost-onOpponent
+++++

.....
Quandary
-----
bc0f047c-01b1-427f-a439-d451eda04120
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Harmony Medtech
-----
bc0f047c-01b1-427f-a439-d451eda05001
-----

+++++

.....
Nisei Division
-----
bc0f047c-01b1-427f-a439-d451eda05002
-----
whileInPlay:Gain1Credits-foreachRevealedPSI
+++++

.....
Tennin Institute
-----
bc0f047c-01b1-427f-a439-d451eda05003
-----

+++++
A0B0G0T0:Put1Advancement-Targeted
.....
House of Knives
-----
bc0f047c-01b1-427f-a439-d451eda05004
-----
onScore:Put3Agenda
+++++
A0B0G0T0:Remove1Agenda-isCost$$Inflict1NetDamage-onOpponent
.....
Medical Breakthrough
-----
bc0f047c-01b1-427f-a439-d451eda05005
-----
whileScored:Decrease1Advancement-affectsMedical Breakthrough
+++++

.....
Philotic Entanglement
-----
bc0f047c-01b1-427f-a439-d451eda05006
-----
onScore:Inflict1NetDamage-onOpponent-perEveryCard-at-isScored-targetOpponents
+++++

.....
The Future Perfect
-----
bc0f047c-01b1-427f-a439-d451eda05007
-----
onAccess:Psi-psiEffects<None,ScoreMyself-onOpponent>-ifNotInstalled-pauseRunner-worksInArchives-disableAutoStealingInArchives
+++++

.....
Chairman Hiro
-----
bc0f047c-01b1-427f-a439-d451eda05008
-----
onRez:Lose2Hand Size-onOpponent||onTrash:Gain2Hand Size-onOpponent-ifActive-ifUnscored$$ScoreMyself-onOpponent-ifAccessed-ifUnscored-preventTrash-runTrashScriptWhileInactive$$Gain2Agenda Points-onOpponent-ifAccessed-ifUnscored$$Put2Scored-isSilent-ifAccessed-ifUnscored
+++++

.....
Mental Health Clinic
-----
bc0f047c-01b1-427f-a439-d451eda05009
-----
onRez:Gain1Hand Size-onOpponent||onTrash:Lose1Hand Size-onOpponent-ifActive||atTurnStart:Gain1Credits-duringMyTurn
+++++

.....
Psychic Field
-----
bc0f047c-01b1-427f-a439-d451eda05010
-----
onAccess:Psi-psiEffects<Inflict1NetDamage-onOppponent-perEveryCard-at-fromHand,None>-ifInstalled
+++++
A0B0G0T0:Psi-psiEffects<Inflict1NetDamage-onOppponent-perEveryCard-at-fromHand,None>
.....
Shi.Kyu
-----
bc0f047c-01b1-427f-a439-d451eda05011
-----
onAccess:UseCustomAbility-ifNotAccessedInRD-worksInArchives
+++++

.....
Tenma Line
-----
bc0f047c-01b1-427f-a439-d451eda05012
-----

+++++
A1B0G0T0:SimplyAnnounce{Swap 2 pieces of installed ICE}
.....
Cerebral Cast
-----
bc0f047c-01b1-427f-a439-d451eda05013
-----
onPlay:Psi-psiEffects<UseCustomAbility,None>
+++++

.....
Medical Research Fundraiser
-----
bc0f047c-01b1-427f-a439-d451eda05014
-----
onPlay:Gain8Credits$$Gain3Credits-onOpponent
+++++

.....
Mushin No Shin
-----
bc0f047c-01b1-427f-a439-d451eda05015
-----
onPlay:InstallTarget-DemiAutoTargeted-atAsset_or_Upgrade_or_Agenda-fromHand-choose1-with3Advancement
+++++

.....
Inazuma
-----
bc0f047c-01b1-427f-a439-d451eda05016
-----

+++++
A0B0G0T0:SimplyAnnounce{prevent the Runner from breaking any subroutines on the next piece of ice he or she encounters during this run.}-isSubroutine||A0B0G0T0:SimplyAnnounce{prevent the Runner from jacking out until after encountering the next piece of ice during this run}-isSubroutine
.....
Komainu
-----
bc0f047c-01b1-427f-a439-d451eda05017
-----

+++++
A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine
.....
Pup
-----
bc0f047c-01b1-427f-a439-d451eda05018
-----

+++++
A0B0G0T0:Inflict1NetDamage-onOpponent-isSubroutine||A0B0G0T0:Lose1Credits-onOpponent-isSubroutine
.....
Shiro
-----
bc0f047c-01b1-427f-a439-d451eda05019
-----

+++++
A0B0G0T0:UseCustomAbility-isFirstCustom-isSubroutine||A0B0G0T0:Pay1Credits-isCost-isSubroutine||A0B0G0T0:UseCustomAbility-isSecondCustom-isSubroutine
.....
Susanoo-No-Mikoto
-----
bc0f047c-01b1-427f-a439-d451eda05020
-----

+++++
A0B0G0T0:UseCustomAbility-isSubroutine
.....
NeoTokyo City Grid
-----
bc0f047c-01b1-427f-a439-d451eda05021
-----

+++++
A0B0G0T0:Gain1Credits
.....
Tori Hanzo #Hardcoded#
-----
bc0f047c-01b1-427f-a439-d451eda05022
-----

+++++

.....
Plan B
-----
bc0f047c-01b1-427f-a439-d451eda05023
-----
onAccess:UseCustomAbility
+++++
A0B0G0T0:UseCustomAbility
.....
Guard
-----
bc0f047c-01b1-427f-a439-d451eda05024
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Rainbow
-----
bc0f047c-01b1-427f-a439-d451eda05025
-----

+++++
A0B0G0T0:RunEnd-isSubroutine
.....
Diversified Portfolio
-----
bc0f047c-01b1-427f-a439-d451eda05026
-----
onPlay:RequestInt-Msg{How many remote servers with a card installed in them do you currently have?}$$Gain1Credits-perX
+++++

.....
Fast Track
-----
bc0f047c-01b1-427f-a439-d451eda05027
-----
onPlay:Retrieve1Card-grabAgenda$$ShuffleStack
+++++

.....
Iain Stirling
-----
bc0f047c-01b1-427f-a439-d451eda05028
-----
atTurnStart:CustomScript-duringMyTurn
+++++

.....
Ken "Express" Tenma
-----
bc0f047c-01b1-427f-a439-d451eda05029
-----
whileInPlay:Gain1Credits-foreachCardPlay-typeRun_and_Event-byMe-onlyOnce
+++++

.....
Silhouette
-----
bc0f047c-01b1-427f-a439-d451eda05030
-----

+++++
A0B0G0T0:ExposeTarget-Targeted-isUnrezzed
.....
Calling in Favors
-----
bc0f047c-01b1-427f-a439-d451eda05031
-----
onPlay:Gain1Credits-perEveryCard-atConnection_and_Resource
+++++

.....
Early Bird
-----
bc0f047c-01b1-427f-a439-d451eda05032
-----
onPlay:RunGeneric$$Gain1Clicks
+++++

.....
Express Delivery
-----
bc0f047c-01b1-427f-a439-d451eda05033
-----
onPlay:Retrieve1Cards-onTop4Cards-doNotReveal$$ShuffleStack
+++++

.....
Feint
-----
bc0f047c-01b1-427f-a439-d451eda05034
-----
onPlay:RunHQ||atSuccessfulRun:SimplyAnnounce{stop accessing cards}-isAlternativeRunResult$$TrashMyself-ifSuccessfulRunHQ-isSilent
+++++

.....
Legwork
-----
bc0f047c-01b1-427f-a439-d451eda05035
-----
onPlay:RunHQ
+++++

.....
Planned Assault
-----
bc0f047c-01b1-427f-a439-d451eda05036
-----
onPlay:Retrieve1Card-grabRun_and_Event-toTable-payCost$$ShuffleStack
+++++

.....
Logos
-----
bc0f047c-01b1-427f-a439-d451eda05037
-----
whileInstalled:Gain1Hand Size$$Gain1MU
+++++
A0B0G0T0:Retrieve1Card-doNotReveal$$ShuffleStack
.....
Public Terminal
-----
bc0f047c-01b1-427f-a439-d451eda05038
-----
onInstall:Put1Credits-isSilent||atTurnPreStart:Refill1Credits-duringMyTurn||whileInstalled:Reduce#CostPlay-affectsRun_and_Event-forMe
+++++

.....
Unregistered S&amp;W 35
-----
bc0f047c-01b1-427f-a439-d451eda05039
-----

+++++
A2B0G0T0:TrashTarget-Targeted-atBioroid_and_nonICE_or_Clone_or_Executive_or_Sysop
.....
Window
-----
bc0f047c-01b1-427f-a439-d451eda05040
-----

+++++
A1B0G0T0:UseCustomAbility
.....
Alias
-----
bc0f047c-01b1-427f-a439-d451eda05041
-----

+++++
A0B1G0T0:SimplyAnnounce{break sentry subroutine}||A0B2G0T0:Put3PlusOne
.....
Breach
-----
bc0f047c-01b1-427f-a439-d451eda05042
-----

+++++
A0B2G0T0:SimplyAnnounce{break up to 3 barrier subroutine}||A0B2G0T0:Put4PlusOne
.....
Bug
-----
bc0f047c-01b1-427f-a439-d451eda05043
-----

+++++
A0B2G0T0:UseCustomAbility
.....
Gingerbread
-----
bc0f047c-01b1-427f-a439-d451eda05044
-----

+++++
A0B1G0T0:SimplyAnnounce{break tracer subroutine}||A0B2G0T0:Put3PlusOne
.....
Grappling Hook
-----
bc0f047c-01b1-427f-a439-d451eda05045
-----

+++++
A0B0G0T1:SimplyAnnounce{break all but 1 subroutines on a piece of ice.}
.....
Passport
-----
bc0f047c-01b1-427f-a439-d451eda05046
-----

+++++
A0B1G0T0:SimplyAnnounce{break code gate subroutine}||A0B2G0T0:Put2PlusOne
.....
Push Your Luck
-----
bc0f047c-01b1-427f-a439-d451eda05047
-----
onPlay:CustomScript
+++++

.....
Security Testing
-----
bc0f047c-01b1-427f-a439-d451eda05048
-----
atTurnStart:CustomScript-duringMyTurn||atSuccessfulRun:CustomScript||atTurnEnd:Remove999SecurityTesting-AutoTargeted_atServer_or_Security Testing
+++++
A0B0G0T0:Remove999SecurityTesting-Targeted-isCost$$Gain2Credits-onlyOnce
.....
Theophilius Bagbiter
-----
bc0f047c-01b1-427f-a439-d451eda05049
-----
onInstall:Lose999Credits||atTurnPreEnd:SetTo1Hand Size-perMyCounter{Credits}-duringMyTurn
+++++

.....
Tri-maf Contact
-----
bc0f047c-01b1-427f-a439-d451eda05050
-----
onTrash:Inflict3MeatDamage
+++++
A1B0G0T0:Gain2Credits-onlyOnce
.....
Mass Install
-----
bc0f047c-01b1-427f-a439-d451eda05051
-----
onPlay:InstallMulti-Targeted-atProgram-fromHand-payCost
+++++

.....
Q-Coherence Chip
-----
bc0f047c-01b1-427f-a439-d451eda05052
-----
whileInstalled:Gain1MU||whileInPlay:TrashMyself-foreachCardTrashed-typeProgram
+++++

.....
Overmind
-----
bc0f047c-01b1-427f-a439-d451eda05053
-----
onInstall:Put1Power-perMyCounter{MU}
+++++
A0B0G0T0:Remove1Power-isCost$$SimplyAnnounce{break ICE subroutine}||A0B1G0T0:Put1PlusOne
.....
Oracle May
-----
bc0f047c-01b1-427f-a439-d451eda05054
-----

+++++
A1B0G0T0:UseCustomAbility-onlyOnce
.....
Donut Taganes
-----
bc0f047c-01b1-427f-a439-d451eda05055
-----
whileInstalled:Increase1CostPlay-affectsAll
+++++

.....

ENDSCRIPTS
=====
'''

########NEW FILE########
__FILENAME__ = constants
﻿###==================================================File Contents==================================================###
# This file contains global variables in ANR. They should not be modified by the scripts at all.
###=================================================================================================================###

import re
#---------------------------------------------------------------------------
# These are constant global variables in ANR: They should not be modified by the scripts at all.
#---------------------------------------------------------------------------

mdict = dict( # A dictionary which holds all the hard coded markers (in the markers file)
             BadPublicity =            ("Bad Publicity", "7ae6b4f2-afee-423a-bc18-70a236b41292"),
             Agenda =                  ("Agenda", "38c5b2a0-caa2-40e4-b5b2-0f1cc7202782"), # We use the blue counter as agendas
             Power =                   ("Power", "815b944d-d7db-4846-8be2-20852a1c9530"),
             Virus =                   ("Virus", "7cbe3738-5c50-4a32-97e7-8cb43bf51afa"),
             Click =                   ("Click", "1c873bd4-007f-46f9-9b17-3d8780dabfc4"),
             Credit5 =                 ("5 Credits","feb0e161-da94-4705-8d56-b48f17d74a99"),
             Credits =                 ("Credit","bda3ae36-c312-4bf7-a288-7ee7760c26f7"),
             Credit =                  ("Credit","bda3ae36-c312-4bf7-a288-7ee7760c26f7"), # Just in case of Typos
             Tag =                     ("Tag","1d1e7dd2-c60a-4770-82b7-d2d9232b3be8"),
             Advancement =             ("Advancement", "f8372e2c-c5df-42d9-9d54-f5d9890e9821"),
             Scored =                  ("Scored", "4911f1ad-abf9-4b75-b4c5-86df3f9098ee"),
             ScorePenalty =            ("Score Penalty", "44bbc99e-72cb-45a6-897c-029870f25556"),
             PlusOnePerm =             ("Permanent +1", "1bd5cc9f-3528-45d2-a8fc-e7d7bd6865d5"),
             PlusOne =                 ("Temporary +1", "e8d0b72e-0384-4762-b983-31137d4b4625"),
             MinusOne =                ("Temporary -1", "d5466468-e05c-4ad8-8bc0-02fbfe4a2ec6"),
             protectionMeatDMG =       ("Meat Damage protection","2bcb7e73-125d-4cea-8874-d67b7532cbd5"),
             protectionNetDMG =        ("Net Damage protection","6ac8bd15-ac1d-4d0c-81e3-990124333a19"),
             protectionBrainDMG =      ("Brain damage protection","99fa1d76-5361-4213-8300-e4c173bc0143"),
             protectionNetBrainDMG =   ("Net & Brain Damage protection","de733be8-8aaf-4580-91ce-5fcaa1183865"),
             protectionAllDMG =        ("Complete Damage protection","13890548-8f1e-4c02-a422-0d93332777b2"),
             protectionVirus =         ("Virus protection","590322bd-83f0-43fa-9239-a2b723b08460"),
             BrainDMG =                ("Brain Damage","59810a63-2a6b-4ae2-a71c-348c8965d612"),
             DaemonMU =                ("Daemon MU", "17844835-3140-4555-b592-0f711048eabd"),
             PersonalWorkshop =        ("Personal Workshop", "efbfabaa-384d-4139-8be1-7f1d706b3dd8"),
             AwakeningCenter =         ("Awakening Center", "867864c4-7d68-4279-823f-100f747aa6f8"),
             Blackmail =               ("Blackmail", "e11a0cf8-25b4-4b5e-9a27-397cc934e890"),
             Cloud =                   ("Cloud", "5f58fb37-e44d-4620-8093-3b7378fb5f57"),
             SecurityTesting =         ("Security Testing", "a3f8daee-be33-42f8-97dc-4d8860ef7fe9"),
             BaseLink =                ("Base Link", "2fb5b6bb-31c5-409c-8aa6-2c46e971a8a5"))

             
regexHooks = dict( # A dictionary which holds the regex that then trigger each core command. 
                   # This is so that I can modify these "hooks" only in one place as I add core commands and modulators.
                   # We use "[:\$\|]" before all hooks, because we want to make sure the script is a core command, and nor part of a modulator (e.g -traceEffects)
                  GainX =              re.compile(r'(?<![<,+-])(Gain|Lose|SetTo)([0-9]+)'), 
                  CreateDummy =        re.compile(r'(?<![<,+-])CreateDummy'),
                  ReshuffleX =         re.compile(r'(?<![<,+-])Reshuffle([A-Za-z& ]+)'),
                  RollX =              re.compile(r'(?<![<,+-])Roll([0-9]+)'),
                  RequestInt =         re.compile(r'(?<![<,+-])RequestInt'),
                  DiscardX =           re.compile(r'(?<![<,+-])Discard[0-9]+'),
                  TokensX =            re.compile(r'(?<![<,+-])(Put|Remove|Refill|Use|Infect)([0-9]+)'),
                  TransferX =          re.compile(r'(?<![<,+-])Transfer([0-9]+)'),
                  DrawX =              re.compile(r'(?<![<,+-])Draw([0-9]+)'),
                  ShuffleX =           re.compile(r'(?<![<,+-])Shuffle([A-Za-z& ]+)'),
                  RunX =               re.compile(r'(?<![<,+-])Run([A-Z][A-Za-z& ]+)'),
                  TraceX =             re.compile(r'(?<![<,+-])Trace([0-9]+)'),
                  InflictX =           re.compile(r'(?<![<,+-])Inflict([0-9]+)'),
                  RetrieveX =          re.compile(r'(?<![<,+-])Retrieve([0-9]+)'),
                  ModifyStatus =       re.compile(r'(?<![<,+-])(Rez|Derez|Expose|Trash|Uninstall|Possess|Exile|Rework|Install|Score|Rehost)(Target|Host|Multi|Myself)'),
                  SimplyAnnounce =     re.compile(r'(?<![<,+-])SimplyAnnounce'),
                  ChooseKeyword =      re.compile(r'(?<![<,+-])ChooseKeyword'),
                  CustomScript =       re.compile(r'(?<![<,+-])CustomScript'),
                  UseCustomAbility =   re.compile(r'(?<![<,+-])UseCustomAbility'),
                  PsiX =               re.compile(r'(?<![<,+-])Psi'),
                  SetVarX =            re.compile(r'(?<![<,+-])SetVar'))

specialHostPlacementAlgs = { # A Dictionary which holds tuples of X and Y placement offsets, for cards which place their hosted cards differently to normal, such as Personal Workshop
                              'Personal Workshop' :            (-32,0),
                              'Awakening Center'  :            (-32,0)
                           }
                           
                  
automatedMarkers = [] #Used in the Inspect() command to let the player know if the card has automations based on the markers it puts out.

place = dict( # A table holding tuples with the original location various card types are expected to start their setup
            Hardware =              (106, -207, 10, 8, 1),  # 1st value is X, second is Y third is Offset (i.e. how far from the other cards (in pixel size) each extra copy should be played. Negative values means it will fall on top of the previous ones slightly) 
            Program =               (-6, -207, 10, 9, -1), # 4th value is Loop Limit (i.e. at how many cards after the first do we loop back to the first position. Loop is always slightly offset, so as not to hide the previous ones completely)
            Resource =              (-6, -337, 10, 9, -1), # Last value is wether the cards will be placed towards the right or left. -1 means to the left.
            Event =                 (435, -331, 10, 3, 1),
            Console =               (221, -331, 0, 1, 1),
            scoredAgenda =          (477, 54, -30, 6, 1),
            liberatedAgenda =       (477, -79, -30, 6, 1),
            Server =                (54, 188, 45, 7, -1),
            Operation =             (463, 256, 10, 3, 1),
            ICE =                   (157, 110, 30, 7, -1), # Temporary. ICE, Upgrades, Assets and Agendas will be special
            Upgrade =               (54, 255, -30, 13, -1), # Temporary.
            Asset =                 (54, 255, -30, 13, -1), # Temporary.
            Agenda =                (54, 255, -30, 13, -1) # Temporary.
            )
               
markerRemovals = { # A dictionary which holds the costs to remove various special markers.
                       # The costs are in a tuple. First is clicks cost and then is credit cost.
                     'Fang' :                        (1,2),
                     'Data Raven' :                  (1,1),
                     'Fragmentation Storm' :         (1,1),
                     'Rex' :                         (1,2),
                     'Crying' :                      (1,2),
                     'Cerberus' :                    (1,4),
                     'Baskerville' :                 (1,3),
                     'Doppelganger' :                (1,4),
                     'Mastiff' :                     (1,4)}

CorporateFactions = [
         'Haas-Bioroid',
         'The Weyland Consortium',
         'NBN',
         'Jinteki']
         
RunnerFactions = [
         'Anarch',
         'Shaper',
         'Criminal']
 
CorporationCardTypes = [
         'ICE',
         'Asset',
         'Agenda',
         'Upgrade',
         'Operation']
         
RunnerCardTypes = [
         'Program',
         'Hardware',
         'Resource',
         'Event']

LimitedCard = [ ### Cards which are limited to one per deck ###
         'bc0f047c-01b1-427f-a439-d451eda03004', # Director Haas Pet-Project
         'bc0f047c-01b1-427f-a439-d451eda05006'  # Philotic Entanglement
         ] 
SpecialDaemons = [ # These are cards which can host programs and avoid their MU cost, but don't have the daemon keyword
         'Dinosaurus'] # Not in use yet.

IgnoredModulators = [ # These are modulators to core commands that we do not want to be mentioning on the multiple choice, of cards that have one
               'isSubroutine',
               'onAccess',
               'ignore',
               'div',
               'isOptional',
               'excludeDummy',
               'onlyforDummy',
               'isCost']
               
trashEasterEgg = [
   "You really shouldn't try to trash this kind of card.",
   "No really, stop trying to trash this card. You need it.",
   "Just how silly are you?",
   "You just won't rest until you've trashed a setup card will you?",
   "I'm warning you...",
   "OK, NOW I'm really warning you...",
   "Shit's just got real!",
   "Careful what you wish for..."]
trashEasterEggIDX = 0
 
ScoredColor = "#00ff44"
SelectColor = "#009900"
EmergencyColor = "#fff600"
DummyColor = "#9370db" # Marks cards which are supposed to be out of play, so that players can tell them apart.
RevealedColor = "#ffffff"
PriorityColor = "#ffd700"
InactiveColor = "#888888" # Cards which are in play but not active yer (e.g. see the shell traders)
StealthColor = "#000000" # Cards which are in play but not active yer (e.g. see the shell traders)
NewCardColor = "#ffa500" # Cards which came into play just this turn

Xaxis = 'x'
Yaxis = 'y'

knownLeagues = {'BGG-L02'           : 'Acceletated Beta League', # The known leagues. Now the game will confirm this was a league match before submitting.
                'BGG-L03'           : 'BGG Third League',
                'BGG-L04'           : 'Show Your True Colors League',
                'BGG-L05'           : 'Fear and Loathing in New Angeles League',
                'HOL'               : 'Honor and OCTGN League',
                'BGG Tournament 3'  : 'BGG Tournament 3',
                'OGO L1'            : 'RPGnet OGO League'
               }
               
#---------------------------------------------------------------------------
# Patreon stuff (http://www.patreon.com/db0)
#---------------------------------------------------------------------------

# All names need to be lowercase as I convert the player's name to lowercase in order to do a case-insensitive search.

SuperchargedSubs = ['stevehouston',       # Brendan               - http://www.patreon.com/user?u=66164
                    'emlun',              # Emil Lundberg         - http://www.patreon.com/user?u=52834
                    '0sum',               # Yongqian Li           - http://www.patreon.com/user?u=66506 
                    'drtall2',            # Sean Fellows          - http://www.patreon.com/user?u=50373
                    'x3r0h0ur',           # Brian Cassidy         - http://www.patreon.com/user?u=66217
                    'davidcarlton',       # David Carlton         - http://www.patreon.com/davidcarlton
                    'conduit23',          # Matt                  - http://www.patreon.com/user?u=66664
                    'failtech',           # Hesy                  - http://www.patreon.com/user?u=66835
                    'renewal',            # Goetzmann             - http://www.patreon.com/user?u=78431
                    'wrathofmine',        # wrathofmine           - http://www.patreon.com/user?u=98478
                    'esurnir',            # Jean-Baptiste         - http://www.patreon.com/user?u=100387
                    'sly',                # Anthony Giovannetti   - http://www.patreon.com/StimHack
                    'Prentice78',         # Mathias Fleck         - http://www.patreon.com/user?u=120373
                    'rallenkov',          # Ralph Radtke          - http://www.patreon.com/user?u=149608
                    'tobinator',          # Tobin Lopes           - http://www.patreon.com/user?u=149628
                    'icydevarosp',        # Nickolas Riggs        - http://www.patreon.com/user?u=151453
                    'broccoli',           # Bryan Graham          - http://www.patreon.com/user?u=42675
                    'alsciende'           # Cedric                - http://netrunnerdb.com/
                   ] # 3$ Tier

CustomSubs = ['dovian',                   # Daniel DeBoer         - http://www.patreon.com/user?u=66260
              'TandooriChicken',          # TandooriChicken       - http://www.patreon.com/user?u=149887
              'demarko'                   # Dannel Jurado         - http://www.patreon.com/demarko
             ] # $5 Tier   
   
CardSubs = ['susuexp',                    # Simon Gunkel          - http://www.patreon.com/user?u=66210
            'reverendanthony',            # Anthony Burch         - http://www.patreon.com/user?u=66843
            'rediknight',                 # Jeremy Espinosa       - http://www.patreon.com/user?u=68437 # Declined all but last payment.
            'wimpgod',                    # Gary Bergeron         - Old time supporter
            'Kethran',                    # Marius Ødegård        - http://www.patreon.com/user?u=90737
            'db0',
            'dbzer0'
           ] # $10 Tier


SuperchargedMsg = "{} is Supercharging their systems.\
             \n+=+ Their presence on the grid is enhanced!".format(me)
           
CustomMsgs = dict( # Dictionary holding the messages requested by people on the 5$ tier and above
                 dovian          = "Dovian wants YOU to support A:NR on OCTGN! - http://www.patreon.com/db0",
                 demarko         = "Above the door is a matte black hemisphere about a meter in diameter, set into the front wall of the building. It is the closest thing the place has to decoration. Underneath it, in letters carved into the wall's black substance, is the name of the place: THE BLACK SUN.",
                 reverendanthony = "When Anthony makes a run on your HQ he stops to kiss you on the cheek real quick",
                 TandooriChicken = "How about a nice game of chess?",
                 db0             = "Please consider supporting A:NR development via Patreon - http://www.patreon.com/db0"
                  )
                  
corpStartMsgs = dict( # Dictionary holding the messages requested by people on the 5$ tier and for corp turn start
                    rediknight         = "\"When I advance my agendas you'll never know if it is safe to proceed or if the damage you will take will bleed you dry.\"",
                    )
                    
corpEndMsgs = dict( # Dictionary holding the messages requested by people on the 5$ tier and for corp turn end
                    )                    
                    
runnerStartMsgs = dict( # Dictionary holding the messages requested by people on the 5$ tier and for runner turn start
                    rediknight         = "\"When I run no server is safe. Is it crime to take what is mine?\""
                    )
                    
runnerEndMsgs = dict( # Dictionary holding the messages requested by people on the 5$ tier and for runner turn end
                    )                                        
                    
########NEW FILE########
__FILENAME__ = customscripts
    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the autoscripting for cards with specialized effects. So called 'CustomScripts'
# * UseCustomAbility() is used among other scripts, and it just one custom ability among other normal core commands
# * CustomScipt() is a completely specialized effect, that is usually so unique, that it's not worth updating my core commands to facilitate it for just one card.
###=================================================================================================================###

collectiveSequence = []

def UseCustomAbility(Autoscript, announceText, card, targetCards = None, notification = None, n = 0):
   global reversePlayerChk
   if fetchProperty(card, 'name') == "Tollbooth":
      targetPL = findOpponent()
      # We reverse for which player the reduce effects work, because we want cards which pay for the opponent's credit cost to take effect now.
      reduction = reduceCost(card, 'FORCE', 3, True, reversePlayer = True) # We use a dry-run to see if they have a card which card reduce the tollbooth cost such as stimhack
      if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))  
      elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      else: extraText = ''
      if targetPL.Credits >= 3 - reduction: 
         finalAmount = targetPL.Credits - 3 # We note it down to mention it later due to a bug that may occur.
         targetPL.Credits -= 3 - reduceCost(card, 'FORCE', 3, reversePlayer = True)
         announceString = announceText + ' force {} to pay {}{}, bringing them down to {}'.format(targetPL,uniCredit(3),extraText,uniCredit(finalAmount))
      else: 
         jackOut(silent = True)
         announceString = announceText + ' end the run'
   if fetchProperty(card, 'name') == "Datapike":
      targetPL = findOpponent()
      # We reverse for which player the reduce effects work, because we want cards which pay for the opponent's credit cost to take effect now.
      reduction = reduceCost(card, 'FORCE', 2, True, reversePlayer = True) # We use a dry-run to see if they have a card which card reduce the tollbooth cost such as stimhack
      if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction))  
      elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      else: extraText = ''
      if targetPL.Credits >= 2 - reduction:
         finalAmount = targetPL.Credits - 2
         targetPL.Credits -= 2 - reduceCost(card, 'FORCE', 2, reversePlayer = True)
         announceString = announceText + ' force {} to pay {}{}, bringing them down to {}'.format(targetPL,uniCredit(2),extraText,uniCredit(finalAmount))
      else: 
         jackOut(silent = True)
         announceString = announceText + ' end the run'
   if fetchProperty(card, 'name') == "Replicator":
      targetC = targetCards[0] # For this to be triggered a program has to have been installed, which was passed to us in an array.
      if not confirm("Would you like to replicate the {}?".format(targetC.name)):
         return 'ABORT'
      retrieveResult = RetrieveX('Retrieve1Card-grab{}-isTopmost'.format(targetC.name.replace('-','_')), announceText, card)
      shuffle(me.piles['R&D/Stack'])
      if re.search(r'no valid targets',retrieveResult[0]): announceString = "{} tries to use their replicator to create a copy of {}, but they run out of juice.".format(me,targetC.name) # If we couldn't find a copy of the played card to replicate, we inform of this
      else: announceString = "{} uses their replicator to create a copy of {}".format(me,targetC.name)
      notify(announceString)
   if fetchProperty(card, 'name') == "Data Hound":
      count = askInteger("By which amount of trace strength did you exceeded the runner's link strength?",1)
      if not count: return 'ABORT'
      targetPL = findOpponent()
      addGroupVisibility(targetPL.piles['R&D/Stack'],me) # Workaround for OCTGN bug #1242
      grabPileControl(targetPL.piles['R&D/Stack'])
      targetPL.piles['R&D/Stack'].addViewer(me)
      cardList = list(targetPL.piles['R&D/Stack'].top(count)) # We make a list of the top cards the corp can look at.
      debugNotify("Turning Runner's Stack Face Up", 2)
      if len(cardList): loopChk(cardList[len(cardList) - 1])
      if len(cardList) > 1:
         notify(":> {}'s Data Hound is sniffing through {}'s Stack".format(me,targetPL))
         choice = SingleChoice("Choose card to trash", makeChoiceListfromCardList(cardList))
         trashedC = cardList.pop(choice)
      else: trashedC = cardList.pop(0)
      debugNotify("Trashing {}".format(trashedC), 2)
      sendToTrash(trashedC)
      if len(cardList) > 1: notify("{}'s Data Hound has sniffed out and trashed {} and is now reorganizing {}'s Stack".format(me,trashedC,targetPL))
      else: notify("{} has sniffed out and trashed {}".format(me,trashedC))
      idx = 0 # The index where we're going to be placing each card.
      while len(cardList) > 0:
         if len(cardList) == 1: choice = 0
         else: choice = SingleChoice("Choose card put on the {} position of the Stack".format(numOrder(idx)), makeChoiceListfromCardList(cardList))
         movedC = cardList.pop(choice)
         movedC.moveTo(targetPL.piles['R&D/Stack'],idx) # If there's only one card left, we put it in the last available index location in the Stack. We always put the card one index position deeper, because the first card is the cover.
         idx += 1
      debugNotify("Removing Visibility", 2)
      rnd(1,100) # Delay to be able to announce names.
      targetPL.piles['R&D/Stack'].removeViewer(me)
      passPileControl(targetPL.piles['R&D/Stack'],targetPL)
      delGroupVisibility(targetPL.piles['R&D/Stack'],me) # Workaround for OCTGN bug #1242
      announceString = ':=> Sniff'
         #      __
         # (___()'`;   *Sniff*
         # /,    /`
         # \\"--\\      
         # Pity the chatbox does not support formatting :(
   if fetchProperty(card, 'name') == "Invasion of Privacy":
      cardList = []
      count = len(me.hand)
      iter = 0
      for c in me.hand:
         cardList.append(c)
         c.moveToTable(playerside * iter * cwidth(c) - (count * cwidth(c) / 2), 0 - yaxisMove(c), False)
         c.highlight = RevealedColor
         iter += 1
      notify("{} reveals {} from their hand. Target the cards you want to trash and press 'Del'".format(me,[c.name for c in cardList]))
      while not confirm("You have revealed your hand to your opponent. Return them to Grip?\n\n(Pressing 'No' will send a ping to your opponent to see if they're done reading them)"):
         notify("{} would like to know if it's OK to return their remaining cards to their Grip.".format(me))
      for c in cardList: 
         if c.group == table: c.moveTo(me.hand)
   if fetchProperty(card, 'name') == "Aggressive Secretary":
      programTargets = [c for c in table if c.Type == 'Program']
      debugNotify("Found {} Programs on table".format(len(programTargets)))
      if not len(programTargets): 
         notify("{} can find no programs to trash".format(card))
         return
      rc = payCost(2, 'not free')
      if rc == "ABORT": 
         notify("{} could not pay to use {}".format(me,card))
         return
      chosenProgs = multiChoice('Please choose {} programs to trash'.format(card.markers[mdict['Advancement']]), makeChoiceListfromCardList(programTargets),card)
      if chosenProgs == 'ABORT': return
      while len(chosenProgs) > card.markers[mdict['Advancement']]:
         chosenProgs = multiChoice('You chose too many programs. Please choose up to {} programs to trash'.format(card.markers[mdict['Advancement']]), makeChoiceListfromCardList(programTargets),card)
         if chosenProgs == 'ABORT': return
      for choiceProg in chosenProgs:
         prog = programTargets[choiceProg]
         intTrashCard(prog, fetchProperty(prog,'Stat'), "free", silent = True)
         notify(":> {} trashes {}".format(card,prog))
      announceString = ''
   if fetchProperty(card, 'name') == "Snoop":
      if re.search(r'-isFirstCustom',Autoscript): 
         remoteCall(findOpponent(),"Snoop",['Simply Reveal'])
         announceString = announceText + " reveal the runner's hand"
      else: 
         remoteCall(findOpponent(),"Snoop",['Reveal and Trash'])
         announceString = announceText + " reveal the runner's hand and trash a card"
   if fetchProperty(card, 'name') == "Punitive Counterstrike":
      barNotifyAll("000000","--The runner is setting how many agenda points they stole last turn.")
      count = askInteger("How many agenda points did you steal last turn?", 0)
      if count: InflictX('Inflict{}MeatDamage-onOpponent'.format(count), '', card)
      notify("--> {} is punished for their shenanigans with {} meat damage".format(me,count))
   if fetchProperty(card, 'name') == "Yagura":
      me.piles['R&D/Stack'].setVisibility('me')
      topC = me.piles['R&D/Stack'][0]
      cardDetails = makeChoiceListfromCardList([topC])[0]
      me.piles['R&D/Stack'].setVisibility('none')
      #notify("{}".format(topCard))
      notify("{} is looking at the top card in their R&D...".format(me))
      if confirm("The top card is:\n{}\n\nDo you want to send it to the bottom of your deck?".format(cardDetails)):
         topC.moveToBottom(me.piles['R&D/Stack'])
         announceString = announceText + " send the top card of their R&D to the bottom".format(me)
      else:
         announceString = announceText + " look at the top card of their R&D and leave it where it is".format(me)   
   if fetchProperty(card, 'name') == "Toshiyuki Sakai":
      handTargets = [c for c in me.hand if c.Type == 'Agenda' or c.Type == 'Asset']
      debugNotify("Found {} Assets / Agendas in hand".format(len(handTargets)))
      if not len(handTargets): 
         notify("{} can find no assets or agendas in your hand".format(card))
         return
      chosenInstall = SingleChoice('Please choose one asset/agenda from your hand with which to replace Toshiyuki Sakai', makeChoiceListfromCardList(handTargets))
      if chosenInstall == 'ABORT': return
      x,y = card.position
      handTargets[chosenInstall].moveToTable(x, y, True)
      handTargets[chosenInstall].markers[mdict['Advancement']] = card.markers[mdict['Advancement']]
      card.moveTo(me.hand)
      notify(":> {} replaces {} with a new card from their hand".format(me,card))
      announceString = ''
   if fetchProperty(card, 'name') == "Power Nap":
      doubles = len([c for c in me.piles['Heap/Archives(Face-up)'] if re.search(r'Double',c.Keywords)])
      if doubles:
         me.Credits += doubles
         notify('--> {} gains {} extra credits for the double events in their Heap'.format(me,uniCredit(doubles)))
      announceString = ''
   if fetchProperty(card, 'name') == "Bullfrog":
      remoteCall(findOpponent(),"Bullfrog",[card])
      announceString = ''
   if card.model == "bc0f047c-01b1-427f-a439-d451eda05011":
      count = askInteger("How many credits do you want to pay for Shi.Kyu?", 0)
      if not count: count = 0
      while count > me.Credits: 
         count = askInteger(":::ERROR::: You do not have {} credits to spend.\n\nHow many credits do you want to pay for Shi.Kyu?".format(count), 0)
         if not count: count = 0
      me.Credits -= count
      notify("{} opts spend {} credits to power Shi.Kyu".format(me,count))
      remoteCall(findOpponent(),"ShiKyu",[card,count])
      announceString = ''
   if fetchProperty(card, 'name') == "Cerebral Cast":
      choice = SingleChoice("Do you want to take a tag or 1 brain damage?",["Take a Tag","Suffer 1 Brain Damage"])
      if choice == 0: 
         me.Tags += 1
         notify("{} chooses to take a Tag".format(me))
      else: 
         InflictX('Inflict1BrainDamage-onOpponent', '', card)
         notify("{} chooses to take a brain damage".format(me))
      announceString = ''
   if fetchProperty(card, 'name') == "Shiro":
      if re.search(r'-isFirstCustom',Autoscript): 
         announceString = announceText + " look and rearrange at the top 3 card of their R&D"
         me.piles['R&D/Stack'].addViewer(me)
         cardList = list(me.piles['R&D/Stack'].top(3)) # We make a list of the top cards we will look at.
         if len(cardList): loopChk(cardList[len(cardList) - 1])
         notify(":> {} is rearranging through {}'s R&D".format(card,me))
         idx = 0 # The index where we're going to be placing each card.
         while len(cardList) > 0:
            if len(cardList) == 1: choice = 0
            else: choice = SingleChoice("Choose card put on the {} position of the R&D".format(numOrder(idx)), makeChoiceListfromCardList(cardList))
            movedC = cardList.pop(choice)
            movedC.moveTo(me.piles['R&D/Stack'],idx) # If there's only one card left, we put it in the last available index location in the Stack. We always put the card one index position deeper, because the first card is the cover.
            idx += 1
         notify("{} has finished preparing the R&D".format(card))
         debugNotify("Removing Visibility", 2)
         me.piles['R&D/Stack'].removeViewer(me)
      else:
         announceString = announceText + " force the runner to access the top card from their R&D"
         remoteCall(fetchRunnerPL(),"RDaccessX",[table,0,0,1])
   if fetchProperty(card, 'name') == "Susanoo-No-Mikoto":
      setGlobalVariable('status','runningArchives') # We change the global variable which holds on which server the runner is currently running on
      enemyIdent = getSpecial('Identity',fetchRunnerPL())
      #confirm("{}.{}".format(runnerPL,getSpecial('Archives',me).name))
      enemyIdent.arrow(getSpecial('Archives',me), False)
      enemyIdent.arrow(getSpecial('Archives',me), True)
      announceString = announceText + " deflect the runner to Archives. The Runner cannot  jack out until after he or she encounters a piece of ice."
   if fetchProperty(card, 'name') == "Plan B":
      if not card.markers[mdict['Advancement']]: advCount = 0
      else: advCount = card.markers[mdict['Advancement']] # We store the count of advancement markers in case the runner proceeds to trash the trap.
      if advCount > 1 and len(me.hand):
         scorableAgendas = [c for c in me.hand if c.Type == 'Agenda' and num(c.Cost) <= advCount]
         if len(scorableAgendas): extraTXT = "You have the following agendas in your HQ you can score with Plan B:\n\n{}".format([c.name for c in scorableAgendas])
         else: extraTXT = ''
         if confirm("Do you want to initiate a Plan B?{}.\n\n(This dialogue also servers as a pause so that your opponent does not know if have any agendas you can score in HQ or not)".format(extraTXT)):
            if len(scorableAgendas):
               if len(scorableAgendas) == 1: choice = 0
               else:
                  choice = SingleChoice("Choose which agenda to score", makeChoiceListfromCardList(scorableAgendas,True))
               if choice == None: notify("{} opts not to initiate their Plan B.".format(me))
               else: 
                  scrAgenda(scorableAgendas[choice], silent = True, forced = True)
                  notify("{} initiates their {} and scores {} from their HQ".format(me,card,scorableAgendas[choice]))
            else: notify("{} opts not to initiate their Plan B".format(me))
         else: notify("{} opts not to initiate their Plan B".format(me))
      else: notify("{} wasn't prepared enough to succeed".format(card))
      announceString = ''
   if fetchProperty(card, 'name') == "Window":
      me.piles['R&D/Stack'].bottom().moveTo(me.hand)
      announceString = announceText + " draw the bottom card from their stack"
   if fetchProperty(card, 'name') == "Bug":
      bugMemory = getGlobalVariable('Bug Memory')
      if bugMemory == 'None': 
         whisper(":::ERROR::: The corp didn't draw a card recently to expose")
         announceString = announceText
      else: announceString = announceText + " expose {} just drawn by the corp".format(bugMemory)
   if fetchProperty(card, 'name') == "Oracle May":
      choice = SingleChoice("What kind of card type do you think is on top of your deck?",['Event','Program','Hardware','Resource'])
      if choice == None: announceString = announceText
      foreseenCard = me.piles['R&D/Stack'].top()
      foreseenCard.moveTo(me.piles['Heap/Archives(Face-up)'])
      update()
      notify(":> {} reveals a {}".format(card,foreseenCard))
      choiceType = ['Event','Program','Hardware','Resource'][choice]
      if foreseenCard.Type == choiceType:
         announceString = announceText + " foresee an {} accurately! {} draws {} to their hand and gains {}".format(choiceType,me,foreseenCard.name,uniCredit(2))
         rnd(1,10)
         foreseenCard.moveTo(me.hand)
         me.Credits += 2
      else: announceString = announceText + " attempt to foresee a {}, but was mistaken. {} is trashed".format(choiceType,foreseenCard)
         
   return announceString
   
def CustomScript(card, action = 'PLAY', origin_card = None, original_action = None): # Scripts that are complex and fairly unique to specific cards, not worth making a whole generic function for them.
   global ModifyDraw, secretCred, collectiveSequence
   debugNotify(">>> CustomScript() with action: {}".format(action)) #Debug
   trash = me.piles['Heap/Archives(Face-up)']
   arcH = me.piles['Archives(Hidden)']
   deck = me.piles['R&D/Stack']
   #confirm("Customscript") # Debug
   if card.model == '23473bd3-f7a5-40be-8c66-7d35796b6031' and action == 'USE': # Virus Scan Special Ability
      clickCost = useClick(count = 3)
      if clickCost == 'ABORT': return 'ABORT'
      playVirusPurgeSound()
      for c in table: 
         foundMarker = findMarker(c,'Virus')
         if foundMarker: c.markers[foundMarker] = 0
      notify("{} to clean all viruses from their corporate grid".format(clickCost))
      return 'CLICK USED'
   elif card.model == '71a89203-94cd-42cd-b9a8-15377caf4437' and action == 'USE': # Technical Difficulties Special Ability
      knownMarkers = []
      for marker in card.markers:
         if marker[0] in markerRemovals: # If the name of the marker exists in the markerRemovals dictionary it means it can be removed and has a specific cost.
            knownMarkers.append(marker)
      if len(knownMarkers) == 0: 
         whisper("No known markers with ability to remove")
         return 'ABORT'
      elif len(knownMarkers) == 1: selectedMarker = knownMarkers[0]
      else: 
         selectTXT = 'Please select a marker to remove\n\n'
         iter = 0
         for choice in knownMarkers:
            selectTXT += '{}: {} ({} {} and {})\n'.format(iter,knownMarkers[iter][0],markerRemovals[choice[0]][0],uniClick(),markerRemovals[choice[0]][1])
            iter += 1
         sel = askInteger(selectTXT,0)
         selectedMarker = knownMarkers[sel]
      aCost = markerRemovals[selectedMarker[0]][0] # The first field in the tuple for the entry with the same name as the selected marker, in the markerRemovals dictionary. All clear? Good.
      cost = markerRemovals[selectedMarker[0]][1]
      clickCost = useClick(count = aCost)
      if clickCost == 'ABORT': return 'ABORT'
      creditCost = payCost(cost)
      if creditCost == 'ABORT':
         me.Clicks += aCost # If the player can't pay the cost after all and aborts, we give him his clicks back as well.
         return 'ABORT' 
      card.markers[selectedMarker] -= 1
      notify("{} to remove {} for {}.".format(clickCost,selectedMarker[0],creditCost))
      return 'CLICK USED'      
   elif fetchProperty(card, 'name') == 'Accelerated Beta Test' and action == 'SCORE':
      if not confirm("Would you like to initiate an accelerated beta test?"): return 'ABORT'
      iter = 0
      foundICE = []
      allCards = list(deck.top(3))
      for c in allCards:
         c.moveTo(arcH)
         loopChk(c,'Type')
         if c.type == 'ICE': foundICE.append(c)
      information("You have beta tested the following cards.\n\n{}\n\n\n(This dialogue is a pause so that your opponent does not know if you saw any ICE or not)\n\nPress OK to continue.".format([c.name for c in allCards]))
      installedICE = 0
      while len(foundICE):
         choice = SingleChoice("Chose an ICE to install or press Cancel to trash all remaining ICE", makeChoiceListfromCardList(foundICE, True))
         if choice != None:
            chosenC = foundICE.pop(choice)
            placeCard(chosenC,'InstallRezzed')
            chosenC.orientation ^= Rot90
            notify(" -- {} Beta Tested!".format(chosenC))
            executePlayScripts(chosenC,'REZ')
            autoscriptOtherPlayers('CardInstall',chosenC)
            autoscriptOtherPlayers('CardRezzed',chosenC)
            installedICE += 1
         else: break
      if installedICE: notify("{} initiates an Accelerated Beta Test and reveals {} Ice from the top of their R&D. These Ice are automatically installed and rezzed".format(me, installedICE))
      else: notify("{} initiates a Accelerated Beta Test but their beta team was incompetent.".format(me))
   elif fetchProperty(card, 'name') == 'Infiltration' and action == 'PLAY':
      tCards = [c for c in table if c.targetedBy and c.targetedBy == me and c.isFaceUp == False]
      if tCards: expose(tCards[0]) # If the player has any face-down cards currently targeted, we assume he wanted to expose them.
      elif confirm("Do you wish to gain 2 credits?\
                \n\nIf you want to expose a target, simply ask the corp to use the 'Expose' option on the table.\
                \n\nHowever if you have a target selected when you play this card, we will also announce that for you."):
         me.Credits += 2
         notify("--> {} gains {}".format(me,uniCredit(2)))
   elif fetchProperty(card, 'name') == "Rabbit Hole" and action == 'INSTALL':
      if not confirm("Would you like to extend the rabbit hole?"): 
         return 'ABORT'
      cardList = [c for c in deck]
      reduction = 0
      rabbits = 0
      totalCost = 0
      for c in cardList: c.moveTo(arcH)
      rnd(1,100)
      debugNotify("Entering rabbit search loop", 2)
      for c in cardList: 
         if c.model == "bc0f047c-01b1-427f-a439-d451eda01039":
            debugNotify("found rabbit!", 2)
            storeProperties(c)
            reduction += reduceCost(c, action, num(c.Cost)) #Checking to see if the cost is going to be reduced by cards we have in play.
            rc = payCost(num(c.Cost) - reduction, "not free")
            if rc == "ABORT": break
            else: totalCost += (num(c.Cost) - reduction)
            placeCard(c, action)
            rabbits += 1
            cardList.remove(c)
            if not confirm("Rabbit Hole extended! Would you like to dig deeper?"): break
      for c in cardList: c.moveTo(deck)
      rnd(1,10)
      shuffle(deck)
      if rabbits: # If the player managed to find and install some extra rabbit holes...
         if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction)) #If it is, make sure to inform.    
         elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
         else: extraText = ''
         me.counters['Base Link'].value += rabbits
         notify("{} has extended the Rabbit Hole by {} {} by paying {}{}".format(me,rabbits,uniLink(),uniCredit(totalCost),extraText))
      else: notify("{} does not find enough rabbits.".format(me))
   elif fetchProperty(card, 'name') == 'Personal Workshop':
      if action == 'USE':
         targetList = [c for c in me.hand  # First we see if they've targeted a card from their hand
                        if c.targetedBy 
                        and c.targetedBy == me 
                        and num(c.Cost) > 0
                        and (c.Type == 'Program' or c.Type == 'Hardware')]
         if len(targetList) > 0:
            selectedCard = targetList[0]
            actionCost = useClick(count = 1)
            if actionCost == 'ABORT': return 'ABORT'
            hostCards = eval(getGlobalVariable('Host Cards'))
            hostCards[selectedCard._id] = card._id # We set the Personal Workshop to be the card's host
            setGlobalVariable('Host Cards',str(hostCards))
            cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == card._id])
            debugNotify("About to move into position", 2) #Debug
            storeProperties(selectedCard)
            orgAttachments(card)
            TokensX('Put1PersonalWorkshop-isSilent', "", selectedCard) # We add a Personal Workshop counter to be able to trigger the paying the cost ability
            announceText = TokensX('Put1Power-perProperty{Cost}', "{} to activate {} in order to ".format(actionCost,card), selectedCard)
            selectedCard.highlight = InactiveColor
            notify(announceText)
            return 'CLICK USED'
         else: 
            whisper(":::ERROR::: You need to target a program or hardware in your hand, with a cost of 1 or more, before using this action")  
            return 'ABORT'
      elif action == 'Start' and card.controller == me:
         hostCards = eval(getGlobalVariable('Host Cards'))
         PWcards = [Card(att_id) for att_id in hostCards if hostCards[att_id] == card._id]
         if len(PWcards) == 0: return 'ABORT'# No cards are hosted in the PW, we're doing nothing
         elif len(PWcards) == 1: selectedCard = PWcards[0] # If only one card is hosted in the PW, we remove a power from one of those.
         else: # Else we have to ask which one to remove.
            selectTXT = 'Personal Workshop: Please select one of your hosted cards from which to remove a power counter\n\n'
            iter = 0
            PWchoices = makeChoiceListfromCardList(PWcards)
            choice = SingleChoice("Choose one of the Personal Workshop hosted cards from which to remove a power counter", PWchoices, type = 'button', default = 0)
            selectedCard = PWcards[choice]
         TokensX('Remove1Power', "Personal Workshop:",selectedCard)
         notify("--> {}'s Personal Workshop removes 1 power marker from {}".format(me,selectedCard))
         if selectedCard.markers[mdict['Power']] == 0: # Empty of power markers means the card can be automatically installed
            host = chkHostType(selectedCard, seek = 'DemiAutoTargeted') 
            if host:
               try:
                  if host == 'ABORT': 
                     selectedCard.markers[mdict['Power']] += 1
                     delayed_whisper("-- Undoing Personal Workshop build")
                     return 'ABORT'
               except:
                  extraTXT = ' and hosted on {}'.format(host) # If the card requires a valid host and we found one, we will mention it later.
            else: extraTXT = ''
            clearAttachLinks(selectedCard) # We unhost it from Personal Workshop so that it's not trashed if PW is trashed
            placeCard(selectedCard, hostCard = host)
            orgAttachments(card)
            selectedCard.markers[mdict['PersonalWorkshop']] = 0
            selectedCard.highlight = None
            executePlayScripts(selectedCard,'INSTALL')
            autoscriptOtherPlayers('CardInstall',selectedCard)
            MUtext = chkRAM(selectedCard)
            notify("--> {} has been built{} from {}'s Personal Workshop{}".format(selectedCard,extraTXT,identName,MUtext))         
   elif fetchProperty(card, 'name') == 'Mr. Li' and action == 'USE':
      ClickCost = useClick(count = 1)
      if ClickCost == 'ABORT': return 'ABORT'
      StackTop = list(me.piles['R&D/Stack'].top(2))
      if len(StackTop) < 2:
         whisper("Your Stack is does not have enough cards. You cannot take this action")
         return 'ABORT'
      notify("--> {} is visiting Mr. Li...".format(me))
      for c in StackTop:
         debugNotify("Pulling cards to hand", 3) #Debug
         c.moveTo(me.hand)
         debugNotify(" Looping...", 4)
         loopChk(c)
         storeProperties(c)
      rnd(1,100) # A delay because it bugs out
      debugNotify("StackTop: {} in hand".format([c.name for c in StackTop])) #Debug
      returnChoice = SingleChoice('Select a card to put to the botton of your Stack', makeChoiceListfromCardList(StackTop, True), type = 'button', default = 0)
      StackTop[returnChoice].moveToBottom(me.piles['R&D/Stack'])
      catchwords = ["Excellent.","Don't leave town.","We'll be in touch.","We'll be seeing you soon...","Always a pleasure.","Remember our agreement.","Interesting request there."]
      goodbye = catchwords.pop(rnd(0, len(catchwords) - 1))
      notify('{} to have {} procure 1 card.\n- "{}"'.format(ClickCost,card,goodbye))
      return 'CLICK USED'
   elif fetchProperty(card, 'name') == "Indexing" and action == 'SuccessfulRun':
      targetPL = findOpponent()
      addGroupVisibility(targetPL.piles['R&D/Stack'],me) # Workaround for OCTGN bug #1242
      debugNotify("Taking R&D Control")
      grabPileControl(targetPL.piles['R&D/Stack'])
      if len(targetPL.piles['R&D/Stack']) < 5: count = len(targetPL.piles['R&D/Stack'])
      else: count = 5
      cardList = list(targetPL.piles['R&D/Stack'].top(count)) # We make a list of the top 5 cards the runner can look at.
      debugNotify("Taking R&D Visibility")
      targetPL.piles['R&D/Stack'].addViewer(me)
      if len(cardList): loopChk(cardList[len(cardList) - 1])
      idx = 0 # The index where we're going to be placing each card.
      while len(cardList) > 0:
         if len(cardList) == 1: choice = 0
         else: choice = SingleChoice("Choose card put on the {} position of the Stack".format(numOrder(idx)), makeChoiceListfromCardList(cardList), cancelButton = False, type = 'button')
         movedC = cardList.pop(choice)
         movedC.moveTo(targetPL.piles['R&D/Stack'],idx) # If there's only one card left, we put it in the last available index location in the Stack. 
         idx += 1
      notify("{} has successfully indexed {}'s R&D".format(me,targetPL))
      targetPL.piles['R&D/Stack'].removeViewer(me)
      passPileControl(targetPL.piles['R&D/Stack'],targetPL)
      delGroupVisibility(targetPL.piles['R&D/Stack'],me) # Workaround for OCTGN bug #1242
   elif fetchProperty(card, 'name') == "Deep Thought" and action == 'Start':
      if card.markers[mdict['Virus']] and card.markers[mdict['Virus']] >= 3:
         targetPL = findOpponent()
         debugNotify("Moving Corp's Top card to our Scripting Pile", 2)
         cardView = targetPL.piles['R&D/Stack'].top()
         cardView.moveTo(me.ScriptingPile)
         rnd(1,10)
         notify(":> Deep Thought has revealed the top card of R&D to {}".format(me))
         delayed_whisper(":> Deep Thought: {} is upcoming! Ommm...".format(cardView))
         rnd(1,10)
         cardView.moveTo(targetPL.piles['R&D/Stack'])
   elif fetchProperty(card, 'name') == "Midori" and action == 'USE':
      targetCards = findTarget('Targeted-atICE-isMutedTarget')
      if not len(targetCards):
         delayed_whisper(":::ERROR::: You need to target an installed to use this ability")
         return 'ABORT'
      tableICE = targetCards[0]
      targetCards = findTarget('Targeted-atICE-fromHand-isMutedTarget')
      if not len(targetCards):
         delayed_whisper(":::ERROR::: You need to also target an ICE in your hand to use this ability")
         return 'ABORT'
      if oncePerTurn(card) == 'ABORT': return 'ABORT'
      handICE = targetCards[0]
      storeProperties(handICE)
      x,y = tableICE.position
      handICE.moveToTable(x,y,True)
      handICE.orientation = Rot90
      tableICE.moveTo(me.hand)
      autoscriptOtherPlayers('CardInstall',handICE)
      notify('{} activates Midori to replace the approached {}, with an ICE from the HQ.'.format(me,tableICE.name))
      notify('- "Naughty Naughty..."')
   elif fetchProperty(card, 'name') == "Director Haas' Pet Project" and action == 'SCORE':
      debugNotify("about to implement Director Haas' Pet Project")
      # First we need to gather all the valid cards from hand or archives.
      installableCards = []
      for c in me.hand:
         if c.Type != 'Operation': installableCards.append(c)
      for c in me.piles['Heap/Archives(Face-up)']:
         if c.Type != 'Operation': installableCards.append(c)
      for c in me.piles['Archives(Hidden)']:
         if c.Type != 'Operation': installableCards.append(c)
      debugNotify("Finished creating installableCards[]")
      if len(installableCards) == 0:
         notify("Director Haas cannot find any cards to use for their pet project :(")
         return 'ABORT'
      if not confirm("Would you like to initiate Director Haass' Pet Project?"): return 'ABORT'
      cardChoices = []
      cardTexts = []
      chosenCList = []
      for iter in range(3):
         debugNotify("len(installableCards) = {}".format(len(installableCards)))
         debugNotify("installableCards: {}".format([rootC.name for rootC in installableCards]), 4)
         debugNotify("iter: {}/{}".format(iter,3), 4)
         del cardChoices[:]
         del cardTexts[:]
         for c in installableCards:
            if c.Rules not in cardTexts: # we don't want to provide the player with a the same card as a choice twice.
               debugNotify("Appending card", 4)
               cardChoices.append(c)
               cardTexts.append(c.Rules)
         choice = SingleChoice("Choose {} card to install in the pet project".format(numOrder(iter)), makeChoiceListfromCardList(cardChoices, includeGroup = True), [], 'Cancel')
         debugNotify("choice = {}".format(choice))
         if choice == None: break
         chosenCList.append(cardChoices[choice])
         if cardChoices[choice].group == me.piles['Heap/Archives(Face-up)']: notify("--> {} selected their {} card ({}) from their {}".format(me, numOrder(iter), cardChoices[choice], pileName(cardChoices[choice].group)))
         else: notify("--> {} selected their {} card from their {}".format(me, numOrder(iter), pileName(cardChoices[choice].group))         )
         installableCards.remove(cardChoices[choice])
         if cardChoices[choice].Type == 'Asset' or cardChoices[choice].Type == 'Agenda': # If we install an asset or agenda, we can't install any more of those so we remove them from the choice list.
            for rootC in installableCards:
               if rootC.Type == 'Asset' or rootC.Type == 'Agenda': 
                  debugNotify("{} Type = {}. Removing".format(rootC,rootC.Type))
                  installableCards.remove(rootC) 
               else:
                  debugNotify("{} Type = {}. Keeping".format(rootC,rootC.Type))            
         if len(installableCards) < 2 - iter: break
      if len(chosenCList) > 0: # If it's 0, it means the player changed their mind and pressed cancel on the first choice.
         debugNotify("chosenCList = {}".format([c.name for c in chosenCList]))
         debugNotify("About to create the new remote")
         Server = table.create("d59fc50c-c727-4b69-83eb-36c475d60dcb", 0, 0 - (40 * playerside), 1, False)
         placeCard(Server,'INSTALL')
         x,y = Server.position
         serverRoot = 0
         serverICE = 0
         debugNotify("About the place the cards in the new remote")
         for c in chosenCList:
            storeProperties(c)
            if c.Type == 'ICE':
               c.moveToTable(x - (10 * flipBoard), (120 * flipBoard) + flipModY - (70 * serverICE * playerside),True)
               c.orientation = Rot90
               serverICE += 1
            else:
               c.moveToTable(x - (serverRoot * 30 * flipBoard), (255 * flipBoard) + flipModY,True)
               serverRoot += 1
            debugNotify("Peeking() at Director Haas' Pet Project")
            c.peek()
            autoscriptOtherPlayers('CardInstall',c)
         notify("{} implements {} and installs {} ICE and {} cards in the server root".format(me,card,serverICE,serverRoot))
   elif fetchProperty(card, 'name') == "Howler" and action == 'USE':
      debugNotify("about to Howl!")
      # First we need to gather all the valid cards from hand or archives.
      installableCards = []
      for c in me.hand:
         if c.Type == 'ICE' and re.search('Bioroid',getKeywords(c)): installableCards.append(c)
      for c in me.piles['Heap/Archives(Face-up)']:
         if c.Type == 'ICE' and re.search('Bioroid',getKeywords(c)): installableCards.append(c)
      for c in me.piles['Archives(Hidden)']:
         if c.Type == 'ICE' and re.search('Bioroid',getKeywords(c)): installableCards.append(c)
      debugNotify("Finished creating installableCards[]")
      if len(installableCards) == 0:
         notify("Howler has no valid targets to shout for >_<")
         return 'ABORT'
      debugNotify("len(installableCards) = {}".format(len(installableCards)))
      debugNotify("installableCards: {}".format([rootC.name for rootC in installableCards]), 4)
      choice = SingleChoice("WAAAaaAAaa! Choose a Bioroid ICE to awaken!", makeChoiceListfromCardList(installableCards, includeGroup = True), [], 'Cancel')
      debugNotify("choice = {}".format(choice))
      if choice == None: return 'ABORT'
      chosenC = installableCards[choice]
      previousGroup = pileName(chosenC.group)
      debugNotify("chosenC = {}".format(chosenC))
      storeProperties(chosenC)
      debugNotify("About to move ICE behind the Howler")
      x,y = card.position
      chosenC.moveToTable(x, y + (40 * flipBoard))
      chosenC.orientation = Rot90
      TokensX('Put1Howler-isSilent', "", card, [chosenC,card])
      notify("{} wueaaAAAA! {} has awakened a {} from {} for the defense of this server!".format(uniSubroutine(),card,chosenC,previousGroup))
      autoscriptOtherPlayers('CardInstall',chosenC)
      autoscriptOtherPlayers('CardRezzed',chosenC)
   elif fetchProperty(card, 'name') == 'Awakening Center' and action == 'USE':
      targetList = [c for c in me.hand  # First we see if they've targeted a card from their hand
                     if c.targetedBy 
                     and c.targetedBy == me 
                     and c.Type == 'ICE'
                     and re.search('Bioroid',getKeywords(c))]
      if len(targetList) > 0:
         selectedCard = targetList[0]
         actionCost = useClick(count = 1)
         if actionCost == 'ABORT': return 'ABORT'
         hostCards = eval(getGlobalVariable('Host Cards'))
         hostCards[selectedCard._id] = card._id # We set the Awakening Center to be the card's host
         setGlobalVariable('Host Cards',str(hostCards))
         cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == card._id])
         debugNotify("About to move into position", 2) #Debug
         storeProperties(selectedCard)
         orgAttachments(card)
         TokensX('Put1Awakening Center-isSilent', "", selectedCard) # We add an Awakening Center counter to be able to trigger the rez the ice ability
         selectedCard.highlight = InactiveColor
         notify("{} has installed a Bioroid ICE in their {}".format(me,card))
         autoscriptOtherPlayers('CardInstall',selectedCard)
         return 'CLICK USED'
      else: 
         whisper(":::ERROR::: You need to target a Bioroid ICE in your HQ before using this action")  
         return 'ABORT'
   elif fetchProperty(card, 'name') == 'Escher':
      tableICE = [c for c in table if fetchProperty(c, 'Type') == 'ICE' or (not c.isFaceUp and c.orientation == Rot90)]
      if action == 'SuccessfulRun':
         for c in tableICE: c.setController(me)
         TokensX('Put1Escher-isSilent', "", card, tableICE)
         notify("{} uses non-euclidian hacks to re-organize the corporation's ICE.".format(Identity))
         delayed_whisper(":::INFO::: All ICE control has been passed to you. Jack Out to pass control back to the corporation player.")
      if action == 'JackOut':
         for c in tableICE: c.setController(findOpponent())
         TokensX('Remove1Escher-isSilent', "", card, tableICE)
         card.moveTo(card.owner.piles['Heap/Archives(Face-up)'])
   elif fetchProperty(card, 'name') == 'Scavenge' and action == 'PLAY':
      targetPrograms = findTarget('Targeted-atProgram')
      if len(targetPrograms) == 0: return 'ABORT'
      else: trashProgram = targetPrograms[0]
      intTrashCard(trashProgram, fetchProperty(trashProgram,'Stat'), "free", silent = True) # We trash it immediately as it can be picked up by scavenge itself.
      gripTargets = findTarget('Targeted-atProgram-fromHand-isMutedTarget') # First we check if the player has targeted a program from their grip as well, this way we don't have to ask.
      if len(gripTargets) > 0: 
         debugNotify("Found Hand Card Targeted group = {}".format([c.name for c in gripTargets]))
         newProgram = gripTargets[0] #If they've targeted more than one, they shouldn't have. We just select the first.
         targetPile = 'Grip'
      else:
         debugNotify("Didn't find hand card targeted")
         gripProgsNR = len([c for c in me.hand if c.Type == 'Program'])
         heapProgsNR = len([c for c in me.piles['Heap/Archives(Face-up)'] if c.Type == 'Program'])
         debugNotify("gripProgsNR = {}, heapProgsNR = {}".format(gripProgsNR,heapProgsNR))
         if gripProgsNR == 0 and heapProgsNR == 0:
            notify("{} wanted to scavenge but forgot they don't have any programs in their grip and heap")
            return 'ABORT'
         elif gripProgsNR == 0: targetPile = 'Heap'
         elif heapProgsNR == 0: targetPile = 'Grip'
         else:
            if confirm("Do you want to install the program from your heap?"):
               targetPile = 'Heap'
            else:
               targetPile = 'Grip'
         if targetPile == 'Heap':
            debugNotify("Retrieving from {}".format(targetPile))
            retrieveTuple = RetrieveX('Retrieve1Card-fromHeap-grabProgram', '', card)
            debugNotify("retrieveTuple = {}".format(retrieveTuple))
            if len(retrieveTuple[1]) == 0: 
               notify("{} scavenged their heap but couldn't find a program to install.".format(me))
               return 'ABORT'
            newProgram = retrieveTuple[1][0]
            pile = me.piles['Heap/Archives(Face-up)']
         else:
            debugNotify("Retrieving from {}".format(targetPile))
            gripTargets = findTarget('AutoTargeted-atProgram-fromHand')
            debugNotify("About to SingleChoice")
            newProgram = gripTargets[SingleChoice("Choose a program to scavenge from your grip", makeChoiceListfromCardList(gripTargets))]
            pile = me.hand
      cardCost = num(fetchProperty(newProgram, 'Cost')) - num(trashProgram.Cost)
      if cardCost < 0: cardCost = 0
      reduction = reduceCost(newProgram, 'INSTALL', cardCost, dryRun = True)
      rc = payCost(cardCost - reduction, "not free")
      if rc == 'ABORT': return 'ABORT' # If the cost couldn't be paid, we don't proceed.
      reduceCost(newProgram, 'INSTALL', cardCost) # If the cost could be paid, we finally take the credits out from cost reducing cards.
      if reduction: reduceTXT = ' (reduced by {})'.format(reduction)
      else: reduceTXT = ''
      MUtext = chkRAM(newProgram)
      placeCard(newProgram)
      rnd(1,100) # A small pause because it seems MU take a bit to update after a multiple choice selection. This means that scavenging an Overmind, would give an extra MU for some reason
      debugNotify("Executing newProgram triggers")
      executePlayScripts(newProgram,'INSTALL')
      autoscriptOtherPlayers('CardInstall',newProgram)
      debugNotify("About to announce")
      notify("{} has trashed {} and {}d through their {} finding and installing {} for {}{}{}.".format(me,trashProgram,card,targetPile,newProgram,uniCredit(cardCost),reduceTXT,MUtext))
   elif fetchProperty(card, 'name') == 'Same Old Thing' and action == 'USE':
      if useClick(count = 2) == 'ABORT': return 'ABORT' #If the player didn't have enough clicks and opted not to proceed, do nothing.
      retrieveTuple = RetrieveX('Retrieve1Card-fromHeap-grabEvent', '', card)
      debugNotify("retrieveTuple = {}".format(retrieveTuple))
      if len(retrieveTuple[1]) == 0: 
         notify("{} tried to do the same old thing but they never did a thing in their life!".format(me))
         return 'ABORT'
      sameOldThing = retrieveTuple[1][0]
      if re.search(r'Double', getKeywords(sameOldThing)) and not chkDoublePrevention() and useClick() == 'ABORT': return 'ABORT' # If it's a double event, we need to pay any double costs.
      notify("{} does the same old {}".format(me,sameOldThing))
      intPlay(sameOldThing,scripted = True)
      intTrashCard(card, fetchProperty(sameOldThing,'Stat'), "free", silent = True)
      return 'CLICK USED'
   elif fetchProperty(card, 'name') == "Motivation" and action == 'Start':
      targetPL = me
      debugNotify("Moving Top card to our Scripting Pile", 2)
      cardView = targetPL.piles['R&D/Stack'].top()
      cardView.moveTo(me.ScriptingPile)
      rnd(1,10)
      notify(":> Motivation has revealed the top card of their Stack to {}".format(me))
      delayed_whisper(":> Motivation: {} is next! Go get 'em!".format(cardView))
      rnd(1,10)
      cardView.moveTo(targetPL.piles['R&D/Stack'])
   elif fetchProperty(card, 'name') == 'Celebrity Gift' and action == 'PLAY':
      revealedCards = findTarget('Targeted-fromHand')
      del revealedCards[5:] # We don't want it to be more than 5 cards
      if len(revealedCards) == 0: 
         delayed_whisper("You need to gift something to the celebrities first you cheapskate!")
         return 'ABORT'
      iter = 0
      for c in revealedCards:
         c.moveToTable(playerside * iter * cwidth(c) - (len(revealedCards) * cwidth(c) / 2), 0 - yaxisMove(c), False)
         c.highlight = RevealedColor
         iter += 1
      notify("{} reveals {} as their celebrity gift and gains {}".format(me,[c.name for c in revealedCards],uniCredit(len(revealedCards) * 2)))
      while not confirm("You have revealed your celebrity gifts to your opponent. Return them to HQ?\n\n(Pressing 'No' will send a ping to your opponent to see if they're done reading them)"):
         notify("{} would like to know if it's OK to return their celebrity gifts to their HQ.".format(me))
      for c in revealedCards: c.moveTo(me.hand)
      me.Credits += len(revealedCards) * 2
   elif fetchProperty(card, 'name') == 'The Collective':
      if action == 'USE' or action == 'Run':
         debugNotify("Current collectiveSequence = {}".format(collectiveSequence),3)
         debugNotify("origin_card = {}. original_action = {}".format(origin_card.name,original_action),3)
         if not len(collectiveSequence):
            debugNotify("Empty collectiveSequence List")
            collectiveSequence.extend([original_action,1,origin_card.name])
         elif collectiveSequence[0] == original_action:
            debugNotify("Matched original_action")
            if original_action == 'CardAction' and collectiveSequence[2] != origin_card.name:
               debugNotify("{} and no match of {} with {}".format(action,collectiveSequence[2],origin_card.name),3)
               del collectiveSequence[:]
               collectiveSequence.extend([original_action,1,origin_card.name])
            else: 
               debugNotify("{} and matched {} with {}".format(action,collectiveSequence[2],origin_card.name),3)
               collectiveSequence[1] += 1
         else:
            debugNotify("No match on original_action")
            del collectiveSequence[:]
            collectiveSequence.extend([original_action,1,origin_card.name])
         if collectiveSequence[1] == 3:
            if oncePerTurn(card) == 'ABORT': return 'ABORT'
            else: 
               me.Clicks += 1
               notify(":> {} has streamlined their processes and gained 1 extra {}.".format(card,uniClick()))
      elif action == 'Start': del collectiveSequence[:]
      debugNotify("Exiting with collectiveSequence = {}".format(collectiveSequence))
   elif fetchProperty(card, 'name') == 'Copycat' and action == 'USE':
      runTargetRegex = re.search(r'running([A-Za-z&]+)',getGlobalVariable('status'))
      if not runTargetRegex: 
         whisper(":::ERROR::: You need to be currently running to use Copycat!")
         return 'ABORT'
      choice = SingleChoice("Which server are you continuing the run from?",['Remote Server','HQ','R&D','Archives'])
      if choice != None: # Just in case the player didn't just close the askInteger window.
         if choice == 0: Name = 'Remote'
         elif choice == 1: Name = 'HQ'
         elif choice == 2: Name = 'R&D'
         elif choice == 3: Name = 'Archives'
         else: return 'ABORT'
      myIdent = getSpecial('Identity',me)
      myIdent.target(False)
      if Name != 'Remote':
         enemyIdent = getSpecial('Identity',findOpponent())
         targetServer = getSpecial(Name,enemyIdent.controller)
         if targetServer: myIdent.arrow(targetServer, True) # If for some reason we can't find the relevant central server card (e.g. during debug), we abort gracefully
      setGlobalVariable('status','running{}'.format(Name))
      notify("{} trashes {} to switch runs to the {} server".format(me,card,Name))
      intTrashCard(card, fetchProperty(card,'Stat'), "free", silent = True)
   elif fetchProperty(card, 'name') == 'Eureka!' and action == 'PLAY':
      c = me.piles['R&D/Stack'].top()
      c.moveTo(me.piles['Heap/Archives(Face-up)'])
      rnd(0,5)
      if c.Type != 'Event':
         extraCost = num(c.Cost) - 10
         if extraCost < 0: extraCost = 0
         reduction = reduceCost(c, 'TRASH', extraCost, dryRun = True)
         if reduction > 0:
            extraText = " ({} - {})".format(extraCost,reduction)
            extraText2 = " (reduced by {})".format(uniCredit(reduction))
         elif reduction < 0:
            extraText = " ({} + {})".format(extraCost,abs(reduction))
            extraText2 = " (increased by {})".format(uniCredit(reduction))
         else:
            extraText = ''
            extraText2 = ''
         if confirm("The top card of your Stack is {}. It will cost you {}{} to install and you have {} credits. Install?".format(c.Name,extraCost - reduction,extraText,me.Credits)):
            intPlay(c, 'not free', True, 10)
         else: notify("{} almost had a breakthrough while working on {}, but didn't have the funds or willpower to follow through.".format(me,c))
      else: notify("{} went for a random breakthrough, but only remembered they should have {}'d instead.".format(me,c))
   elif fetchProperty(card, 'name') == 'Expert Schedule Analyzer' and action == 'SuccessfulRun':
      remoteCall(findOpponent(),"ESA",[])
   elif fetchProperty(card, 'name') == "Woman in the Red Dress" and action == 'Start':
      remoteCall(findOpponent(),"WitRD",[])
   elif fetchProperty(card, 'name') == 'Accelerated Diagnostics' and action == 'PLAY':
      if len(me.piles['R&D/Stack']) < 3: count = len(me.piles['R&D/Stack'])
      else: count = 3
      cardList = []
      trashedList = []
      debugNotify("Moving all cards to the scripting pile")
      for c in me.piles['R&D/Stack'].top(count): 
         c.moveTo(me.ScriptingPile)
         if fetchProperty(c, 'Type') != 'Operation': # We move all cards in execution limbo (see http://boardgamegeek.com/thread/1086167/double-accelerated-diagnostics)
            debugNotify("Appending to trashedList")
            trashedList.append(c)
         else: 
            debugNotify("Appending to cardList")
            cardList.append(c)
      debugNotify("Finished checing Types")
      if len(cardList) == 0: notify("{} initiated an Accelerated Diagnostics but their beta team was incompetent".format(me))
      else:
         debugNotify("Starting to play operations")
         opsNr = len(cardList)
         for iter in range(opsNr):
            choice = SingleChoice("Choose {} diagnostic to run".format(numOrder(iter)), makeChoiceListfromCardList(cardList,True), cancelName = 'Done')
            if choice == None: break
            intPlay(cardList[choice], 'not free', True)
            debugNotify("Card Played, trashing it")
            cardList[choice].moveTo(me.piles['Heap/Archives(Face-up)'])
            cardList.remove(cardList[choice])
         notify("{} initiated an {} for {} operations and trashed {} other cards".format(me,card,3 - len(cardList) - len(trashedList), len(cardList) + len(trashedList)))
      for c in trashedList: c.moveTo(me.piles['Archives(Hidden)']) 
      for c in cardList: c.moveTo(me.piles['Archives(Hidden)'])
   elif fetchProperty(card, 'name') == "City Surveillance" and action == 'Start': # We don't need a remote call, since it's going to be the runner pressing F1 anyway in this case.
      reduction = reduceCost(card, 'Force', 1, dryRun = True)
      if reduction > 0: extraText = " (reduced by {})".format(uniCredit(reduction)) #If it is, make sure to inform.
      elif reduction < 0: extraText = " (increased by {})".format(uniCredit(abs(reduction)))
      else: extraText = ''
      if me.Credits >= 1 - reduction and confirm("City Surveilance: Pay 1 Credit?"): 
         payCost(1 - reduction, 'not free')
         reduction = reduceCost(card, 'Force', 1)
         notify(":> {} paid {} {} to avoid the {} tag".format(me,1 - reduction, extraText, card))
      else: 
         me.Tags += 1
         notify(":> {} has been caught on {} and received 1 tag".format(me,card))
   elif fetchProperty(card, 'name') == 'Power Shutdown' and action == 'PLAY':
      count = askInteger("Trash How many cards from R&D (max {})".format(len(me.piles['R&D/Stack'])),0)
      if count > len(me.piles['R&D/Stack']): count = len(me.piles['R&D/Stack'])
      for c in me.piles['R&D/Stack'].top(count): c.moveTo(me.piles['Archives(Hidden)'])
      notify("{} has initiated a power shutdown and trashed {} cards. The runner must trash 1 installed program or hardware with an install cost of {} or less".format(me,count,count))
   elif fetchProperty(card, 'name') == 'Keyhole' and action == 'SuccessfulRun':
      targetPL = findOpponent()
      grabPileControl(targetPL.piles['R&D/Stack'])
      grabPileControl(targetPL.piles['Heap/Archives(Face-up)'])
      if len(targetPL.piles['R&D/Stack']) < 3: count = len(targetPL.piles['R&D/Stack'])
      else: count = 3
      cardList = list(targetPL.piles['R&D/Stack'].top(count)) # We make a list of the top 3 cards the runner can look at.
      debugNotify("Peeking at Corp's Stack.", 2)
      for c in targetPL.piles['R&D/Stack']: c.peek()
      update() # Delay to be able to read card info
      rnd(1,100) # More delay because apparently it wasn't enough.
      choice = SingleChoice("Choose a card to trash", makeChoiceListfromCardList(cardList, True), type = 'button')
      trashedC = cardList[choice]
      sendToTrash(trashedC)
      debugNotify("Shuffling Pile")
      shuffle(targetPL.piles['R&D/Stack'])
      notify("{} has peeked through the {} at R&D and trashed {}".format(me,card,trashedC))
      passPileControl(targetPL.piles['R&D/Stack'],targetPL)
      passPileControl(targetPL.piles['Heap/Archives(Face-up)'],targetPL)
   elif fetchProperty(card, 'name') == 'Leverage' and action == 'PLAY':
      remoteCall(findOpponent(),"Leverage",[card])
   elif fetchProperty(card, 'name') == 'Capstone' and action == 'USE':
      trashTargets = findTarget('Targeted-fromHand')
      if len(trashTargets) == 0: whisper("Capstone cannot function without at least some juice!")
      else:
         actionCost = useClick(count = 1)
         if actionCost == 'ABORT': return 'ABORT'
         count = 0
         for c in trashTargets:
            foundDuplicate = False
            for seek in table:
               if c.name == seek.name: foundDuplicate = True
            if foundDuplicate: count += 1
            c.moveTo(me.piles['Heap/Archives(Face-up)'])
         drawMany(me.piles['R&D/Stack'], count, silent = False)
         notify("{} to activate {} in order to trash {} from their hand and draw {} new cards".format(actionCost,card,[c.name for c in trashTargets],count))
         return 'CLICK USED'
   elif fetchProperty(card, 'name') == 'Rex Campaign' and action == 'Start':
      debugNotify("Checking Rex Campaign")
      if not card.markers[mdict['Power']]:
         if confirm("Your Rex Campaign has concluded. Do you want to gain 5 credits?\
                 \n\n(Pressing 'No' will remove 1 Bad Publicity instead)"):
            me.Credits += 5
            notify("--> The Rex Campaign concludes and provides {} with {}".format(me,uniCredit(5)))
         else:
            me.counters['Bad Publicity'].value -= 1
            notify("=> The Rex Campaign concludes and reduces {}'s Bad Publicity by 1".format(me))     
         sendToTrash(card)
   elif fetchProperty(card, 'name') == 'Sweeps Week' and action == 'PLAY':
      targetPL = findOpponent()
      me.Credits += len(targetPL.hand)
      notify("--> {} uses {}'s ability to gain {}".format(me,card,uniCredit(len(targetPL.hand))))
   elif fetchProperty(card, 'name') == 'Precognition' and action == 'PLAY':
      notify("{} foresees the future...".format(me))
      me.piles['R&D/Stack'].lookAt(5)
   elif fetchProperty(card, 'name') == 'Quest Completed' and action == 'PLAY':
      accessC = findTarget('Targeted-targetOpponents')
      if len(accessC): accessTarget(accessC[0], noQuestionsAsked = True)
      else: whisper("You need to target an card to access before playing this event")      
   elif action == 'USE': useCard(card)
   if fetchProperty(card, 'name') == "Executive Wiretaps" and action == 'PLAY':
      remoteCall(findOpponent(),"ExecWire",[])
   elif fetchProperty(card, 'name') == 'Reclamation Order' and action == 'PLAY':
      retrieveTuple = RetrieveX('Retrieve1Card-fromArchives', '', card)
      count = 0
      if retrieveTuple == 'ABORT': return 'ABORT'
      else:
         arcPiles = list(me.piles['Heap/Archives(Face-up)'])
         arcPiles.extend(me.piles['Archives(Hidden)'])
         foundMore = []
         for c in arcPiles:
            if c.name == retrieveTuple[1][0].name: foundMore.append(c)
         if len(foundMore):
            count = askInteger("There's {} more copies of {} in your Archives. Retrieve how many?\n\n(We'll retrieve from Open Archives first)".format(len(foundMore),retrieveTuple[1][0].name),len(foundMore))
            for iter in range(count): foundMore.pop(0).moveTo(me.hand)
      notify("{} retrieved {} copies of {} from their Archives".format(me,len(retrieveTuple[1]) + count,retrieveTuple[1][0].name))
   elif fetchProperty(card, 'name') == 'Iain Stirling' and action == 'Start':
      if me.counters['Agenda Points'].value < fetchCorpPL().counters['Agenda Points'].value:
         me.Credits += 2
         notify("{}: Provides {}".format(card,uniCredit(2)))
   if fetchProperty(card, 'name') == "Push Your Luck" and action == 'PLAY':
      count = askInteger("How many credits do you want to spend?",me.Credits)
      while count > me.Credits: count = askInteger(":::Error::: You cannot spend more credits than you have\n\nHow many credits do you want to spend?",me.Credits)
      remoteCall(findOpponent(),"PYL",[count])
   if fetchProperty(card, 'name') == "Security Testing":
      if action == 'Start':
         choice = SingleChoice("Which server would you like to security test today?",['HQ','R&D','Archives','Remote'])
         if choice == 3 or choice == None:
            card.markers[mdict['SecurityTesting']] += 1
            whisper(":::INFO::: Please manually move your Security Testing marker to the targeted remote server.\nOnce you successful run that server, target it and double click on {} to get your credits manually.".format(card))
         else:
            targetServer = getSpecial({0:'HQ',1:'R&D',2:'Archives'}.get(choice),fetchCorpPL())
            if not targetServer.markers[mdict['SecurityTesting']]: targetServer.markers[mdict['SecurityTesting']] += 1 # Apparently you cannot use more than one replacement effect each run, so only one of these counters can be placed per server
         notify("{} is going to be {} {} this turn".format(me,card,{0:'HQ',1:'R&D',2:'the Archives',3:'a remote server'}.get(choice)))
      else: 
         if getGlobalVariable('feintTarget') != 'None': currentRunTarget = getGlobalVariable('feintTarget')
         else: 
            currentRunTargetRegex = re.search(r'running([A-Za-z&]+)', getGlobalVariable('status')) # We check what the target of the current run was.
            currentRunTarget = currentRunTargetRegex.group(1)
         if currentRunTarget != 'Remote':
            targetServer = getSpecial(currentRunTarget,fetchCorpPL())
            if targetServer.markers[mdict['SecurityTesting']]: 
               #gain = targetServer.markers[mdict['SecurityTesting']] * 2
               for c in table:
                  if c.name == "Security Testing" and c.orientation == Rot0: 
                     c.orientation = Rot90
                     break # We only set one Sec.Testing as used per run.
               targetServer.markers[mdict['SecurityTesting']] = 0
               me.Credits += 2
               notify("{}: Successful Penetration nets {} {} instead of access.".format(card,me,uniCredit(2)))
               return 'ALTERNATIVE RUN'
            
def markerEffects(Time = 'Start'):
   mute()
   debugNotify(">>> markerEffects() at time: {}".format(Time)) #Debug
   ### Checking triggers from markers the rest of our cards.
   cardList = [c for c in table if c.markers]
   for card in cardList:
      for marker in card.markers:
         if (re.search(r'Tinkering',marker[0]) and Time == 'End') or (re.search(r'Paintbrush',marker[0])) and Time == 'JackOut':
            TokensX('Remove999Keyword:Code Gate-isSilent', "Tinkering:", card)
            TokensX('Remove999Keyword:Sentry-isSilent', "Tinkering:", card)
            TokensX('Remove999Keyword:Barrier-isSilent', "Tinkering:", card)
            if re.search(r'Tinkering',marker[0]): 
               TokensX('Remove999Tinkering', "Tinkering:", card)
               notify("--> {} removes tinkering effect from {}".format(me,card))
            else: 
               TokensX('Remove999Paintbrush', "Paintbrush:", card)
               notify("--> {} removes Paintbrush effect from {}".format(me,card))
         if re.search(r'Cortez Chip',marker[0]) and Time == 'End':
            TokensX('Remove1Cortez Chip-isSilent', "Cortez Chip:", card)
            notify("--> {} removes Cortez Chip effect from {}".format(me,card))
         if re.search(r'Joshua Enhancement',marker[0]) and Time == 'End': # We put Joshua's effect here, in case the runner trashes the card with Aesop's after using it
            TokensX('Remove1Joshua Enhancement-isSilent', "Joshua Enhancement:", card)
            GainX('Gain1Tags', "Joshua's Enhancements:".format(me), card)
            notify("--> Joshua's Enhancements give {} a tag".format(identName))
         if re.search(r'Test Run',marker[0]) and Time == 'End': # We put Test Run's effect here, as the card will be discarded after being played.
            notify("--> The Test Run {} is returned to {}'s stack".format(card,identName))
            rnd(1,10)
            ModifyStatus('UninstallMyself-toStack', 'Test Run:', card)
         if re.search(r'Deep Red',marker[0]) and Time == 'End': # We silently remove deep red effects
            TokensX('Remove1Deep Red-isSilent', "Deep Red:", card)
         if re.search(r'LLDS Processor',marker[0]) and Time == 'End': # We silently remove LLDS Processor bonus
            TokensX('Remove999LLDS Processor-isSilent', "LLDS Processor:", card)
         if re.search(r'Gyri Labyrinth',marker[0]) and Time == 'Start' and (card.controller != me or len(getPlayers()) == 1): 
            opponentPL = findOpponent()
            opponentPL.counters['Hand Size'].value += card.markers[marker] * 2
            notify(":> Gyri Labyrinth's effect expires and {} recovers {} hand size".format(card,card.markers[marker] * 2))
            card.markers[marker] = 0

def ASVarEffects(Time = 'Start'):
   mute()
   debugNotify(">>> ASVarEffects() at time: {}".format(Time)) #Debug
   ### Checking triggers from AutoScript Variables
   ASVars = eval(getGlobalVariable('AutoScript Variables'))
   if Time == 'Start': ASVars['Subliminal'] = 'False' # At the very start of each turn, we set the Subliminal var to False to signify no Subliminal has been played yet.
   setGlobalVariable('AutoScript Variables',str(ASVars))

def CustomEffects(Time = 'Start'):
   mute()
   debugNotify(">>> CustomEffects() at time: {}".format(Time)) #Debug
   ### Checking for specific effects that require special card awareness.
   #AwarenessList = eval(me.getGlobalVariable('Awareness'))
   if Time == 'Start': #and 'Subliminal Messaging' in AwarenessList: 
      count = sum(1 for card in me.piles['Heap/Archives(Face-up)'] if card.name == 'Subliminal Messaging')
      count += sum(1 for card in me.piles['Archives(Hidden)'] if card.name == 'Subliminal Messaging')
      if count and getGlobalVariable('Central Run') == 'False' and getGlobalVariable('Remote Run') == 'False':
         choice = 4
         while count < choice: 
            choice = askInteger("How much Subliminal Messaging do you want to take back into your HQ (Max {})?\
                             \n\n(We'll start taking from Face-Up Archives)".format(count), 1)
         grabbed = 0
         if grabbed < choice:
            for card in me.piles['Heap/Archives(Face-up)']:      
               if card.name == 'Subliminal Messaging': 
                  grabbed += 1
                  card.moveTo(me.hand)
                  notify(":> {} takes one Subliminal Messaging from Face-Up Archives to their HQ".format(me))
               if grabbed == choice: break
         if grabbed < choice:
            for card in me.piles['Archives(Hidden)']:
               if card.name == 'Subliminal Messaging': 
                  grabbed += 1
                  card.moveTo(me.hand)
                  notify(":> {} takes one Subliminal Messaging from Hidden Archives to their HQ".format(me))
               if grabbed == choice: break

def markerScripts(card, action = 'USE'):
   debugNotify(">>> markerScripts() with action: {}".format(action)) #Debug
   foundSpecial = False
   for key in card.markers:
      if key[0] == 'Personal Workshop' and action == 'USE':
         foundSpecial = True
         count = askInteger("{} has {} power counters left.\nHow many do you want to pay to remove?".format(card.name,card.markers[mdict['Power']]),card.markers[mdict['Power']])
         if not count: return foundSpecial
         if count > card.markers[mdict['Power']]: count = card.markers[mdict['Power']]
         host = chkHostType(card) 
         if host:
            try:
               if count == card.markers[mdict['Power']] and host == 'ABORT': 
                  delayed_whisper("-- Undoing Personal Workshop build")
                  return foundSpecial
            except: extraTXT = ' on {}'.format(host) # If the card requires a valid host and we found one, we will mention it later.
         else: extraTXT = ''
         hostCards = eval(getGlobalVariable('Host Cards'))
         hostCard = Card(hostCards[card._id])
         reduction = reduceCost(hostCard, 'USE', count, dryRun = True)
         rc = payCost(count - reduction, "not free")
         if rc == 'ABORT': return foundSpecial # If the cost couldn't be paid, we don't proceed.
         reduceCost(hostCard, 'USE', count) # If the cost could be paid, we finally take the credits out from cost reducing cards.
         card.markers[mdict['Power']] -= count
         if reduction: reduceTXT = ' (reduced by {})'.format(reduction)
         else: reduceTXT = ''
         if card.markers[mdict['Power']] == 0: 
            clearAttachLinks(card) # We unhost it from Personal Workshop so that it's not trashed if PW is trashed
            placeCard(card)
            orgAttachments(hostCard)
            card.markers[mdict['PersonalWorkshop']] = 0
            card.highlight = None
            executePlayScripts(card,'INSTALL')
            autoscriptOtherPlayers('CardInstall',card)
            MUtext = chkRAM(card)
            notify("{} has paid {}{} in order to install {}{} from their Personal Workshop{}".format(me,uniCredit(count),reduceTXT,card,extraTXT,MUtext))
         else:
            notify("{} has paid {}{} to remove {} power counters from {} in their Personal Workshop".format(me,uniCredit(count),reduceTXT,count,card))         
      if key[0] == 'Awakening Center' and action == 'USE' and not card.isFaceUp:
         foundSpecial = True
         host = chkHostType(card) 
         hostCards = eval(getGlobalVariable('Host Cards'))
         hostCard = Card(hostCards[card._id])
         cardCost = num(fetchProperty(card, 'Cost')) - 7
         if cardCost < 0: cardCost = 0
         reduction = reduceCost(card, 'REZ', cardCost, dryRun = True)
         rc = payCost(cardCost - reduction, "not free")
         if rc == 'ABORT': return foundSpecial # If the cost couldn't be paid, we don't proceed.
         reduceCost(card, 'REZ', cardCost) # If the cost could be paid, we finally take the credits out from cost reducing cards.
         if reduction: reduceTXT = ' (reduced by {})'.format(reduction)
         else: reduceTXT = ''
         #card.markers[mdict['AwakeningCenter']] = 0
         card.highlight = None
         intRez(card,cost = 'free',silent = True)
         notify("{} has paid {}{} in order to rez {} from their {}.".format(me,uniCredit(cardCost),reduceTXT,card,hostCard))
      if key[0] == 'Escher' and action == 'USE': 
         global EscherUse
         foundSpecial = True
         if ds == 'corp': 
            whisper("Our ICE shouldn't have Escher tokens! Cleaning")
            tableICE = [c for c in table if fetchProperty(c, 'Type') == 'ICE' or (not c.isFaceUp and c.orientation == Rot90)]
            TokensX('Remove1Escher-isSilent', "", card, tableICE)
         else:
            EscherUse +=1
            if EscherUse == 1: whisper(":::ERROR::: Runners are not allowed to rez Escher ICE")
            elif EscherUse == 2: whisper("Bweep! Please don't touch that!")
            elif EscherUse == 3: whisper("Bweep! Bweep! Intruder Alert!")
            elif EscherUse == 4: whisper("Please stay where you are. Our helpful assistants will be right with you.")
            elif EscherUse == 5: whisper("Please remain calm. Assistance is on the way.")
            elif EscherUse == 6: whisper("Please remain calm...")
            elif EscherUse == 7: whisper("Remain calm...")
            elif EscherUse == 8: whisper("Suddenly it is pitch black!")
            elif EscherUse == 9: whisper("It is pitch black! You feel that you should really consider jacking out any time now...")
            elif EscherUse == 10: whisper("You are likely to be eaten by a Grue...")
            elif EscherUse == 11: 
               if confirm("Fine! A Grue 1.0 is rezzed! Run away?"):
                  me.Clicks = 0
                  jackOut()
                  notify("{} has encountered a Grue and run away. They lose the rest of their turn for wasting so much time.".format(me))
               else:
                  delayed_whisper(":> You FOOL!")
                  notify("{} was looking for trouble in the dark and has been eaten by a Grue. {} has flatlined".format(me,me))
                  for i in range(6): applyBrainDmg()
                  jackOut()
            else: EscherUse = 0
      if key[0] == 'Deep Red' and action == 'USE':
         notify("{} uses Deep Red's ability to rehost {}".format(me,card))
         me.Clicks += 1
         card.markers[key] = 0
         # We do not return True on foundSpecial as we want the rest of the script to run its course as well.
      if key[0] == 'Blackmail' and action == 'USE' and not card.isFaceUp:
         foundSpecial = True
         whisper(":::ERROR::: You cannot rez ICE during this run, you are being Blackmailed!")
   return foundSpecial
   
def setAwareness(card):
# A function which stores if a special card exists in a player's deck, and activates extra scripts only then (to avoid unnecessary load)
   if card.name == 'Subliminal Messaging': # For now we only have subliminal. In the future we might get more card names separated by OR clauses.
      AwarenessList = eval(me.getGlobalVariable('Awareness'))
      if card.name not in AwarenessList: AwarenessList.append(card.name)
      me.setGlobalVariable('Awareness',str(AwarenessList))
   
#------------------------------------------------------------------------------
# Custom Remote Functions
#------------------------------------------------------------------------------

def ESA(): # Expert Schedule Analyzer
   debugNotify(">>> Remote Script ESA()") #Debug
   mute()
   revealedCards = []
   for c in me.hand: revealedCards.append(c)
   iter = 0
   for c in revealedCards:
      c.moveToTable(playerside * iter * cwidth(c) - (len(revealedCards) * cwidth(c) / 2), 0 - yaxisMove(c), False)
      c.highlight = RevealedColor
      iter += 1
   notify("The Expert Schedule Analyzer reveals {}".format([c.name for c in revealedCards]))
   while not confirm("You have revealed your hand to your opponent. Return them to HQ?\n\n(Pressing 'No' will send a ping to your opponent to see if they're done reading them)"):
      notify("{} would like to know if it's OK to return their remaining cards to their HQ.".format(me))
   for c in revealedCards: c.moveTo(me.hand)
         
def WitRD(): # Woman in the Red Dress   
   debugNotify(">>> Remote Script WitRD()") #Debug     
   mute()   
   cardView = me.piles['R&D/Stack'].top()
   debugNotify("Flipping top R&D card")
   cardView.isFaceUp = True
   rnd(1,10)
   notify(":> The Woman in the Red Dress has revealed {}".format(cardView))
   if confirm("Do you want to draw {} to your HQ?".format(cardView.name)):
      notify("{} decided to take {} to their hand".format(me,cardView))
      cardView.moveTo(me.hand)
   else: cardView.isFaceUp = False      

def Snoop(scenario = 'Simply Reveal', cardList = None):
   debugNotify(">>> Remote Script Snoop() with Scenario = {}".format(scenario)) #Debug     
   mute()
   if not cardList: cardList = []
   if scenario == 'Remote Corp Trash Select':
      choice = SingleChoice("Choose one card to trash", makeChoiceListfromCardList(cardList,True))
      if choice != None: 
         cardList[choice].moveTo(cardList[choice].owner.piles['Heap/Archives(Face-up)'])
         notify("{} decided to trash {} from the cards snooped at".format(me,cardList[choice]))
         cardList.remove(cardList[choice])
      for c in cardList: c.setController(c.owner)
      remoteCall(findOpponent(),"Snoop",['Recover Hand',cardList])            
   elif scenario == 'Recover Hand':
      for c in cardList: c.moveTo(me.hand)
   else:
      count = len(me.hand)
      if count == 0: 
         notify("There are no cards in the runner's Grip to snoop at")
         return
      iter = 0
      for c in me.hand:
         cardList.append(c)
         c.moveToTable(playerside * iter * cwidth(c) - (count * cwidth(c) / 2), 0 - yaxisMove(c), False)
         c.highlight = RevealedColor
         iter += 1
      notify("Snoop reveals {}".format([c.name for c in cardList]))
      if scenario == 'Simply Reveal':
         while not confirm("You have revealed your hand to your opponent. Return them to Grip?\n\n(Pressing 'No' will send a ping to your opponent to see if they're done reading them)"):
            notify("{} would like to know if it's OK to return their remaining cards to their Grip.".format(me))
         for c in cardList: c.moveTo(me.hand)
      elif scenario == 'Reveal and Trash':
         for c in cardList: c.setController(findOpponent())
         remoteCall(findOpponent(),"Snoop",['Remote Corp Trash Select',cardList])
         
def Leverage(card): # Leverage
   mute()
   barNotifyAll('#000000',"The corporation is deliberating if the runner's leverage is sufficient.")
   #notify(" - {} is deliberating if the runner's leverage is sufficient.".format(me))
   if confirm("Your opponent has just played Leverage. Do you want to take 2 Bad Publicity in order to allow them to still suffer damage until their next turn?"):
      me.counters['Bad Publicity'].value += 2
      notify("The corporation has decided to take 2 Bad Publicity. Beware!")
   else:
      CreateDummy('CreateDummy-with99protectionAllDMG-onOpponent', '', card)
      notify("--> The corporation has caved in to the runner's leverage. The runner cannot take any damage until the start of their next turn.")
      
def ExecWire(): # Expert Schedule Analyzer
   debugNotify(">>> Remote Script ExecWire()") #Debug
   mute()
   revealedCards = []
   for c in me.hand: revealedCards.append(c)
   iter = 0
   for c in revealedCards:
      c.moveToTable(playerside * iter * cwidth(c) - (len(revealedCards) * cwidth(c) / 2), 0 - yaxisMove(c), False)
      c.highlight = RevealedColor
      iter += 1
   notify("The Executive Wiretaps reveal {}".format([c.name for c in revealedCards]))
   while not confirm("You have revealed your hand to your opponent. Return them to HQ?\n\n(Pressing 'No' will send a ping to your opponent to see if they're done reading them)"):
      notify("{} would like to know if it's OK to return their remaining cards to their HQ.".format(me))
   for c in revealedCards: c.moveTo(me.hand)
         
def Bullfrog(card): # Bullfrog
   choice = SingleChoice("Which server are you going to redirect the run at?", ['Remote Server','HQ','R&D','Archives'])
   if choice != None: # Just in case the player didn't just close the askInteger window.
      if choice == 0: targetServer = 'Remote'
      elif choice == 1: targetServer = 'HQ'
      elif choice == 2: targetServer = 'R&D'
      elif choice == 3: targetServer = 'Archives'
      else: return 'ABORT'
   else: return 'ABORT'
   setGlobalVariable('status','running{}'.format(targetServer)) # We change the global variable which holds on which server the runner is currently running on
   if targetServer == 'Remote': announceText = 'a remote server'
   else: announceText = 'the ' + targetServer
   notify("--> {}'s Ability triggers and redirects the runner to {}.".format(card,announceText))

def ShiKyu(card,count): # Shi.Kyu
   mute()
   if confirm("Shi.Kyu is about to inflict {} Net Damage to you. Score it for -1 Agenda Points instead?".format(count)):
      GainX('Lose1Agenda Points-onOpponent-isSilent', '', card)
      ModifyStatus('ScoreMyself-onOpponent-isSilent', '', card)
      update()
      TokensX('Put1ScorePenalty-isSilent', '', card)
      notify("{} opts to score Shi.Kyu for -1 Agenda Point".format(me))
   else:
      remoteCall(fetchCorpPL(),'InflictX',['Inflict{}NetDamage-onOpponent'.format(count), '{} activates {} to'.format(card.owner, card), card, None, 'Automatic', count]) # We always have the corp itself do the damage
     
def PYL(count): # Push Your Luck
   mute()
   choice = SingleChoice("Do you think the runner spent an even or an odd number of credits pushing their luck?\n(They had {} to spend)".format(fetchRunnerPL().Credits),['Even','Odd'])
   if count % 2 == choice:
      notify("Failure! The corp correctly guessed the runner has spent an {} number of credits. {} lost {}".format({0:'Even',1:'Odd'}.get(count % 2),fetchRunnerPL(),uniCredit(count)))
      fetchRunnerPL().Credits -= count
      playSpecialSound('Special-Push_Your_Luck-Fail')
   else:
      notify("Success! The corp incorrectly thought the runner had spent an {} number of credits. {} gains {}".format({0:'Even',1:'Odd'}.get(count % 2),fetchRunnerPL(),uniCredit(count)))
      fetchRunnerPL().Credits += count
      playSpecialSound('Special-Push_Your_Luck-Success')
########NEW FILE########
__FILENAME__ = events
    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains the basic table actions in ANR. They are the ones the player calls when they use an action in the menu.
# Many of them are also called from the autoscripts.
###=================================================================================================================###

import re
import collections
import time

flipBoard = 1 # If True, it signifies that the table board has been flipped because the runner is on the side A
ds = None # The side of the player. 'runner' or 'corp'
flipModX = 0
flipModY = 0

def chkTwoSided():
   mute()
   if not table.isTwoSided(): information(":::WARNING::: This game is designed to be played on a two-sided table. Things will be extremely uncomfortable otherwise!! Please start a new game and make sure  the appropriate button is checked")
   fetchCardScripts() # We only download the scripts at the very first setup of each play session.
   versionCheck()
   prepPatronLists()
   checkQuickAccess()

def checkDeck(player,groups):
   debugNotify(">>> checkDeck(){}".format(extraASDebug())) #Debug
   #confirm("raw groups = {}".format(groups))
   #confirm("group names= {}".format([g.name for g in groups]))
   if player != me: return # We only want the owner of to run this script
   mute()
   global totalInfluence, Identity, ds
   notify (" -> Checking deck of {} ...".format(me))
   ok = True
   group = me.piles['R&D/Stack']
   ds = None
   for card in me.hand:
      if card.Type != 'Identity':
         whisper(":::Warning::: You are not supposed to have any non-Identity cards in your hand when you start the game")
         card.moveToBottom(me.piles['R&D/Stack'])
         continue
      else:
         ds = card.Side.lower()
         me.setGlobalVariable('ds', ds)
         storeSpecial(card)
         Identity = card
   debugNotify("About to fetch Identity card", 4) #Debug
   if not Identity: 
      delayed_whisper(":::ERROR::: Please Reset and load a deck with an Identity included. Aborting!")
      return
   loDeckCount = len(group)
   debugNotify("About to check Identity min deck size.", 4) #Debug
   if loDeckCount < num(Identity.Requirement): # For identities, .Requirement is the card minimum they have.
      ok = False
      notify ( ":::ERROR::: Only {} cards in {}'s Deck. {} Needed!".format(loDeckCount,me,num(Identity.Requirement)))
   mute()
   loAP = 0
   loInf = 0
   loRunner = False
   agendasCount = 0
   #debugNotify("About to move cards into me.ScriptingPile", 4) #Debug
   debugNotify("About to get visibility", 4) #Debug
   group.setVisibility('me')
   #for card in group: card.moveTo(me.ScriptingPile)
   #if len(players) > 1: random = rnd(1,100) # Fix for multiplayer only. Makes Singleplayer setup very slow otherwise.
   debugNotify("About to check each card in the deck", 4) #Debug
   counts = collections.defaultdict(int)
   CardLimit = {}
   professorsRig = [] # This is used by "The Professor" to avoid counting influence for the first instance of a program.
   for card in group:
      #setAwareness(card)
      counts[card.name] += 1
      if counts[card.name] > 3:
         notify(":::ERROR::: Only 3 copies of {} allowed.".format(card.name))
         ok = False
      if card.Type == 'Agenda':
         if ds == 'corp':
            loAP += num(card.Stat)
            agendasCount += 1
         else:
            notify(":::ERROR::: Agendas found in {}'s Stack.".format(me))
            ok = False
      elif card.Type in CorporationCardTypes and Identity.Faction in RunnerFactions:
         notify(":::ERROR::: Corporate cards found in {}'s Stack.".format(me))
         ok = False
      elif card.Type in RunnerCardTypes and Identity.Faction in CorporateFactions:
         notify(":::ERROR::: Runner cards found in {}'s R&Ds.".format(me))
         ok = False
      if num(card.Influence) and card.Faction != Identity.Faction:
         if Identity.model == 'bc0f047c-01b1-427f-a439-d451eda03029' and card.Type == 'Program' and card.model not in professorsRig:
            debugNotify("adding {} to prof. rig. card type = {}".format(card,card.Type))
            professorsRig.append(card.model) # First instance of a card is free of influence costs.
         else: 
            debugNotify("adding influence of {}. card type = {}".format(card,card.Type))
            loInf += num(card.Influence)
      else:
         if card.Type == 'Identity':
            notify(":::ERROR::: Extra Identity Cards found in {}'s {}.".format(me, pileName(group)))
            ok = False
         elif card.Faction != Identity.Faction and card.Faction != 'Neutral' and Identity.Faction != 'Neutral':
            notify(":::ERROR::: Faction-restricted card ({}) found in {}'s {}.".format(fetchProperty(card, 'name'), me, pileName(group)))
            ok = False
      if Identity.model == 'bc0f047c-01b1-427f-a439-d451eda03002' and card.Faction == 'Jinteki':
         notify(":::ERROR::: Jinteki cards found in a {} deck".format(Identity))
         ok = False
      if card.model in LimitedCard:
         if card.model not in CardLimit: CardLimit[card.model] = 1
         else: CardLimit[card.model] += 1
         if CardLimit[card.model] > 1: 
            notify(":::ERROR::: Duplicate Limited card ({}) found in {}'s {}.".format(card,me,pileName(group)))
            ok = False
   #if len(players) > 1: random = rnd(1,100) # Fix for multiplayer only. Makes Singleplayer setup very slow otherwise.
   #for card in me.ScriptingPile: card.moveToBottom(group) # We use a second loop because we do not want to pause after each check
   group.setVisibility('None')
   if ds == 'corp':
      requiredAP = 2 + 2 * int(loDeckCount / 5)
      if loAP not in (requiredAP, requiredAP + 1):
         notify(":::ERROR::: {} cards requires {} or {} Agenda Points, found {}.".format(loDeckCount, requiredAP, requiredAP + 1, loAP))
         ok = False
   if loInf > num(Identity.Stat) and Identity.Faction != 'Neutral':
      notify(":::ERROR::: Too much rival faction influence in {}'s R&D. {} found with a max of {}".format(me, loInf, num(Identity.Stat)))
      ok = False
   deckStats = (loInf,loDeckCount,agendasCount) # The deck stats is a tuple that we stored shared, and stores how much influence is in the player's deck, how many cards it has and how many agendas
   me.setGlobalVariable('Deck Stats',str(deckStats))
   debugNotify("Total Influence used: {} (Influence string stored is: {}".format(loInf, me.getGlobalVariable('Influence')), 2) #Debug
   if ok: notify("-> Deck of {} is OK!".format(me))
   else: 
      notify("-> Deck of {} is _NOT_ OK!".format(me))
      information("We have found illegal cards in your deck. Please load a legal deck!")
   debugNotify("<<< checkDeckNoLimit()") #Debug
   chkSideFlip()
  
def chkSideFlip(forced = False):
   mute()
   debugNotify(">>> chkSideFlip()")
   debugNotify("Checking Identity", 3)
   if not ds:
      information(":::ERROR::: No Identity found! Please load a deck which contains an Identity card before proceeding to setup.")
      return
   chooseSide()
   debugNotify("Checking side Flip", 3)
   if (ds == 'corp' and me.hasInvertedTable()) or (ds == 'runner' and not me.hasInvertedTable()): setGlobalVariable('boardFlipState','True')
   elif flipBoard == -1: setGlobalVariable('boardFlipState','False')
   else: debugNotify("Leaving Board as is")

def parseNewCounters(player,counter,oldValue):
   mute()
   debugNotify(">>> parseNewCounters() for player {} with counter {}. Old Value = {}".format(player,counter.name,oldValue))
   if counter.name == 'Tags' and player == me: chkTags()
   if counter.name == 'Bad Publicity' and oldValue < counter.value:
      if player == me: playSound('Gain-Bad_Publicity')
      for c in table: # Looking for cards which trigger off the corp gaining Bad Publicity
         if c.name == "Raymond Flint" and c.controller == me:
            if confirm("Do you want to activate Raymont Flint's ability at this point?\n\n(Make sure your opponent does not have a way to cancel this effect before continuing)"):
               HQaccess(silent = True)
   debugNotify("<<< parseNewCounters()")

def checkMovedCard(player,card,fromGroup,toGroup,oldIndex,index,oldX,oldY,x,y,isScriptMove,highlight = None,markers = None):
   mute()
   debugNotify("isScriptMove = {}".format(isScriptMove))
   if toGroup != me.piles['R&D/Stack'] and card.owner == me: superCharge(card) # First we check if we should supercharge the card, but only if the card is still on the same group at the time of execution.  
   if fromGroup == me.piles['R&D/Stack'] and toGroup == me.hand and ds == 'corp': # Code to store cards drawn by the corp to be exposed later by Bug
      if len([c for c in table if c.name == 'Bug']): setGlobalVariable('Bug Memory',card.name)
   if isScriptMove: return # If the card move happened via a script, then all further automations should have happened already.
   if fromGroup == me.hand and toGroup == table: 
      if card.Type == 'Identity': intJackin(manual = True)
      else: 
         if not card.isFaceUp: card.peek()
         intPlay(card, retainPos = True)
   elif fromGroup != table and toGroup == table and card.owner == me: # If the player moves a card into the table from Deck or Trash, we assume they are installing it for free.
      if not card.isFaceUp: card.peek()
      if confirm("Play this card from {} for free?".format(pileName(fromGroup))):
         intPlay(card, cost = 'free', scripted = True, retainPos = True)
   elif fromGroup == table and toGroup != table and card.owner == me: # If the player dragged a card manually from the table to their discard pile...
      if card.isFaceUp and card.Type == 'Program': 
         chkRAM(card, 'UNINSTALL')
         notify(":> {} frees up {} MU".format(player,card.Requirement))
      if toGroup == player.piles['Archives(Hidden)'] or toGroup == player.piles['Heap/Archives(Face-up)']:
         if ds == 'runner': sendToTrash(card, player.piles['Heap/Archives(Face-up)']) # The runner cards always go to face-up archives
         else: sendToTrash(card, toGroup)
      else: 
         executePlayScripts(card,'UNINSTALL')
         autoscriptOtherPlayers('CardUninstalled',card)
         clearAttachLinks(card) # If the card was manually uninstalled or moved elsewhere than trash, then we simply take care of the MU and the attachments
   elif fromGroup == table and toGroup == table and card.owner == me: 
      orgAttachments(card)
      
def checkGlobalVars(name,oldValue,value):
   mute()
   if name == 'boardFlipState': checkBoardFlip(name,oldValue,value)
   if name == 'accessAttempts': checkAccessAttempts(name,oldValue,value)

def checkBoardFlip(name,oldValue,value):   
   global flipBoard, flipModX, flipModY
   if value == 'True':
      debugNotify("Flipping Board")
      flipBoard = -1
      flipModX = -61
      flipModY = -77
      table.setBoardImage("table\\Tabletop_flipped.png")
   else:
      debugNotify("Restoring Board Orientation")
      flipBoard = 1
      flipModX = 0
      flipModY = 0
      table.setBoardImage("table\\Tabletop.png") # If they had already reversed the table before, we set it back proper again   

def checkAccessAttempts(name,oldValue,value):
   if ds == 'corp' and num(value) >= 3:
      if confirm("The runner is currently waiting for final corporate reactions before proceeding to access the server. Do you have any cards to rez or paid abilities to use at this moment?"):
         notify(":::WARNING::: The Corporation delays access while they deliberate which reacts to trigger...")
      else: runSuccess()
         
def reconnectMe(group=table, x=0,y=0):
   reconnect()
   
def reconnect():
# An event which takes care to properly reset all the player variables after they reconnect to the game.
   global identName, Identity, lastKnownNrClicks, PriorityInform, ds
   fetchCardScripts(silent = True)
   for card in me.hand: storeProperties(card)
   for card in table:
      storeProperties(card)
      if card.Type == 'Identity' and card.owner == me:
         identName = card.name # The name of our current identity
         Identity = card
         ds = card.Side.lower()
      if card.Type == 'ICE': card.orientation = Rot90         
   lastKnownNrClicks = me.Clicks
   PriorityInform = False # Explains what the "prioritize card" action does.
   chkSideFlip()
   notify("::> {} has reconnected to the session!".format(me))
   
########NEW FILE########
__FILENAME__ = generic
﻿    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains generic game-agnostic scripts. They can be ported as-is in any kind of game.
# * [Generic] funcrion do basic stuff like convert a sting into a number or store your card's properties.
# * [Custom Windows Forms] are functions which create custom-crafted WinForms on the table. The MultipleChoice form is heavily commented.
# * [Card Placement] Are dealing with placing or figuring where to place cards on the table
###=================================================================================================================###

import re

try:
    import os
    if os.environ['RUNNING_TEST_SUITE'] == 'TRUE':
        from meta import Automations
        Form = object
except ImportError:
    pass

playerside = None # Variable to keep track on which side each player is
playeraxis = None # Variable to keep track on which axis the player is

### Variables that hold the properties of a card.
Stored_Name = {}
Stored_Type = {}
Stored_Keywords = {}
Stored_Cost = {}
Stored_AutoActions = {}
Stored_AutoScripts = {}

### Subscriber lists.

supercharged = []
customized = []

#---------------------------------------------------------------------------
# Custom Windows Forms
#---------------------------------------------------------------------------

try:
   import clr
   clr.AddReference("System.Drawing")
   clr.AddReference("System.Windows.Forms")

   from System.Windows.Forms import *
   from System.Drawing import Color
except:
   Automations['WinForms'] = False
   
def calcStringLabelSize(STRING): 
# A function which returns a slowly expansing size for a label. The more characters, the more the width expands to allow more characters on the same line.
   newlines = 0
   for char in STRING:
      if char == '\n': newlines += 1
   STRINGwidth = 200 + (len(STRING) / 4)
   STRINGheight = 30 + ((20 - newlines) * newlines) + (30 * (STRINGwidth / 100))
   return (STRINGwidth, STRINGheight)

def calcStringButtonHeight(STRING): 
# A function which returns a slowly expansing size for a label. The more characters, the more the width expands to allow more characters on the same line.
   newlines = 0
   for char in STRING:
      if char == '\n': newlines += 1
   STRINGheight = 30 + (8 * newlines) + (7 * (len(STRING) / 20))
   return STRINGheight
   
def formStringEscape(STRING): # A function to escape some characters that are not otherwise displayed by WinForms, like amperasands '&'
   slist = list(STRING)
   escapedString = ''
   for s in slist:
      if s == '&': char = '&&'
      else: char = s
      escapedString += char
   return escapedString

class OKWindow(Form): # This is a WinForm which creates a simple window, with some text and an OK button to close it.
   def __init__(self,InfoTXT):
      self.StartPosition = FormStartPosition.CenterScreen
      (STRwidth, STRheight) = calcStringLabelSize(InfoTXT)
      FORMheight = 130 + STRheight
      FORMwidth = 100 + STRwidth
      self.Text = 'Information'
      self.Height = FORMheight
      self.Width = FORMwidth
      self.AutoSize = True
      self.MinimizeBox = False
      self.MaximizeBox = False
      self.TopMost = True
      
      labelPanel = Panel()
      labelPanel.Dock = DockStyle.Top
      labelPanel.AutoSize = True
      labelPanel.BackColor = Color.White

      self.timer_tries = 0
      self.timer = Timer()
      self.timer.Interval = 200
      self.timer.Tick += self.onTick
      self.timer.Start()
      
      label = Label()
      label.Text = formStringEscape(InfoTXT)
      if debugVerbosity >= 2: label.Text += '\n\nTopMost: ' + str(self.TopMost) # Debug
      label.Top = 30
      label.Left = (self.ClientSize.Width - STRwidth) / 2
      label.Height = STRheight
      label.Width = STRwidth
      labelPanel.Controls.Add(label)
      #label.AutoSize = True #Well, that's shit.

      button = Button()
      button.Text = "OK"
      button.Width = 100
      button.Top = FORMheight - 80
      button.Left = (FORMwidth - 100) / 2
      button.Anchor = AnchorStyles.Bottom

      button.Click += self.buttonPressed

      self.Controls.Add(labelPanel)
      self.Controls.Add(button)

   def buttonPressed(self, sender, args):
      self.timer.Stop()
      self.Close()

   def onTick(self, sender, event):
      if self.timer_tries < 3:
         self.TopMost = False
         self.Focus()
         self.Activate()
         self.TopMost = True
         self.timer_tries += 1
            
def information(Message):
   debugNotify(">>> information() with message: {}".format(Message))
   if Automations['WinForms']:
      Application.EnableVisualStyles()
      form = OKWindow(Message)
      form.BringToFront()
      form.ShowDialog()
   else: 
      confirm(Message)
   
   
class SingleChoiceWindow(Form):
 
   def __init__(self, BoxTitle, BoxOptions, type, defaultOption, pages = 0, cancelButtonBool = True, cancelName = 'Cancel'):
      self.Text = "Select an Option"
      self.index = 0
      self.confirmValue = None
      self.MinimizeBox = False
      self.MaximizeBox = False
      self.StartPosition = FormStartPosition.CenterScreen
      self.AutoSize = True
      self.TopMost = True
      
      (STRwidth, STRheight) = calcStringLabelSize(BoxTitle)
      self.Width = STRwidth + 50

      self.timer_tries = 0
      self.timer = Timer()
      self.timer.Interval = 200
      self.timer.Tick += self.onTick
      self.timer.Start()
      
      labelPanel = Panel()
      labelPanel.Dock = DockStyle.Top
      labelPanel.AutoSize = True
      labelPanel.BackColor = Color.White
      
      separatorPanel = Panel()
      separatorPanel.Dock = DockStyle.Top
      separatorPanel.Height = 20
      
      choicePanel = Panel()
      choicePanel.Dock = DockStyle.Top
      choicePanel.AutoSize = True

      self.Controls.Add(labelPanel)
      labelPanel.BringToFront()
      self.Controls.Add(separatorPanel)
      separatorPanel.BringToFront()
      self.Controls.Add(choicePanel)
      choicePanel.BringToFront()

      label = Label()
      label.Text = formStringEscape(BoxTitle)
      if debugVerbosity >= 2: label.Text += '\n\nTopMost: ' + str(self.TopMost) # Debug
      label.Top = 30
      label.Left = (self.ClientSize.Width - STRwidth) / 2
      label.Height = STRheight
      label.Width = STRwidth
      labelPanel.Controls.Add(label)
      
      bufferPanel = Panel() # Just to put the radio buttons a bit more to the middle
      bufferPanel.Left = (self.ClientSize.Width - bufferPanel.Width) / 2
      bufferPanel.AutoSize = True
      choicePanel.Controls.Add(bufferPanel)
            
      for option in BoxOptions:
         if type == 'radio':
            btn = RadioButton()
            if defaultOption == self.index: btn.Checked = True
            else: btn.Checked = False
            btn.CheckedChanged += self.checkedChanged
         else: 
            btn = Button()
            btn.Height = calcStringButtonHeight(formStringEscape(option))
            btn.Click += self.choiceMade
         btn.Name = str(self.index)
         self.index = self.index + 1
         btn.Text = formStringEscape(option)
         btn.Dock = DockStyle.Top
         bufferPanel.Controls.Add(btn)
         btn.BringToFront()

      button = Button()
      button.Text = "Confirm"
      button.Width = 100
      button.Dock = DockStyle.Bottom
      button.Click += self.buttonPressed
      if type == 'radio': self.Controls.Add(button) # We only add the "Confirm" button on a radio menu.
 
      buttonNext = Button()
      buttonNext.Text = "Next Page"
      buttonNext.Width = 100
      buttonNext.Dock = DockStyle.Bottom
      buttonNext.Click += self.nextPage
      if pages > 1: self.Controls.Add(buttonNext) # We only add the "Confirm" button on a radio menu.

      cancelButton = Button() # We add a bytton to Cancel the selection
      cancelButton.Text = cancelName # We can rename the cancel button if we want to.
      cancelButton.Width = 100
      cancelButton.Dock = DockStyle.Bottom
      #button.Anchor = AnchorStyles.Bottom
      cancelButton.Click += self.cancelPressed
      if cancelButtonBool: self.Controls.Add(cancelButton)
      
   def buttonPressed(self, sender, args):
      self.timer.Stop()
      self.Close()

   def nextPage(self, sender, args):
      self.confirmValue = "Next Page"
      self.timer.Stop()
      self.Close()
 
   def cancelPressed(self, sender, args): # The function called from the cancelButton
      self.confirmValue = None # It replaces the choice list with an ABORT message which is parsed by the calling function
      self.timer.Stop()
      self.Close() # And then closes the form
      
   def checkedChanged(self, sender, args):
      self.confirmValue = sender.Name
      
   def choiceMade(self, sender, args):
      self.confirmValue = sender.Name
      self.timer.Stop()
      self.Close()
      
   def getIndex(self):
      return self.confirmValue

   def onTick(self, sender, event):
      if self.timer_tries < 3:
         self.TopMost = False
         self.Focus()
         self.Activate()
         self.TopMost = True
         self.timer_tries += 1

def SingleChoice(title, options, type = 'button', default = 0, cancelButton = True, cancelName = 'Cancel'):
   debugNotify(">>> SingleChoice()".format(title))
   if Automations['WinForms']:
      optChunks=[options[x:x+7] for x in xrange(0, len(options), 7)]
      optCurrent = 0
      choice = "New"
      while choice == "New" or choice == "Next Page" or (choice == None and not cancelButton):
         Application.EnableVisualStyles()
         form = SingleChoiceWindow(title, optChunks[optCurrent], type, default, pages = len(optChunks), cancelButtonBool = cancelButton, cancelName = cancelName)
         form.BringToFront()
         form.ShowDialog()
         choice = form.getIndex()
         debugNotify("choice is: {}".format(choice), 2)
         if choice == "Next Page": 
            debugNotify("Going to next page", 3)
            optCurrent += 1
            if optCurrent >= len(optChunks): optCurrent = 0
         elif choice != None: 
            choice = num(form.getIndex()) + (optCurrent * 7) # if the choice is not a next page, then we convert it to an integer and give that back, adding 8 per number of page passed
   else:
      concatTXT = title + '\n\n'
      for iter in range(len(options)):
         concatTXT += '{}:--> {}\n'.format(iter,options[iter])
      choice = askInteger(concatTXT,0)
   debugNotify("<<< SingleChoice() with return {}".format(choice), 3)
   return choice

   
class MultiChoiceWindow(Form):
 # This is a windows form which creates a multiple choice form, with a button for each choice. 
 # The player can select more than one, and they are then returned as a list of integers
   def __init__(self, FormTitle, FormChoices,CPType, pages = 0,currPage = 0, existingChoices = []): # We initialize our form, expecting 3 variables. 
                                                      # FormTitle is the title of the window itself
                                                      # FormChoices is a list of strings which we use for the names of the buttons
                                                      # CPType is combined with FormTitle to give a more thematic window name.
      self.Text = CPType # We just store the variable locally
      self.index = 0 # We use this variable to set a number to each button
      self.MinimizeBox = False # We hide the minimize button
      self.MaximizeBox = False # We hide the maximize button
      self.StartPosition = FormStartPosition.CenterScreen # We start the form at the center of the player's screen
      self.AutoSize = True # We allow the form to expand in size depending on its contents
      self.TopMost = True # We make sure our new form will be on the top of all other windows. If we didn't have this here, fullscreen OCTGN would hide the form.
      self.origTitle = formStringEscape(FormTitle) # Used when modifying the label from a button
      
      self.confirmValue = existingChoices
      debugNotify("existingChoices = {}".format(self.confirmValue))
      self.nextPageBool = False  # self.nextPageBool is just remembering if the player has just flipped the page.
      self.currPage = currPage
      
      self.timer_tries = 0 # Ugly hack to fix the form sometimes not staying on top of OCTGN
      self.timer = Timer() # Create a timer object
      self.timer.Interval = 200 # Speed is at one 'tick' per 0.2s
      self.timer.Tick += self.onTick # Activate the event function on each tick
      self.timer.Start() # Start the timer.
      
      (STRwidth, STRheight) = calcStringLabelSize(FormTitle) # We dynamically calculate the size of the text label to be displayed as info to the player.
      labelPanel = Panel() # We create a new panel (e.g. container) to store the label.
      labelPanel.Dock = DockStyle.Top # We Dock the label's container on the top of the form window
      labelPanel.Height = STRheight # We setup the dynamic size
      labelPanel.Width = STRwidth
      labelPanel.AutoSize = True # We allow the panel to expand dynamically according to the size of the label
      labelPanel.BackColor = Color.White
      
      choicePanel = Panel() # We create a panel to hold our buttons
      choicePanel.Dock = DockStyle.Top # We dock this below the label panel
      choicePanel.AutoSize = True # We allow it to expand in size dynamically
      #radioPanel.BackColor = Color.LightSalmon # Debug

      separatorPanel = Panel() # We create a panel to separate the labels from the buttons
      separatorPanel.Dock = DockStyle.Top # It's going to be docked to the middle of both
      separatorPanel.Height = 20 # Only 20 pixels high

      self.Controls.Add(labelPanel) # The panels need to be put in the form one by one
      labelPanel.BringToFront() # This basically tells that the last panel we added should go below all the others that are already there.
      self.Controls.Add(separatorPanel)
      separatorPanel.BringToFront() 
      self.Controls.Add(choicePanel) 
      choicePanel.BringToFront() 

      self.label = Label() # We create a label object which will hold the multiple choice description text
      #if len(self.confirmValue): self.label.Text = formStringEscape(FormTitle) + "\n\nYour current choices are:\n{}".format(self.confirmValue) # We display what choices we've made until now to the player.
      self.label.Text = formStringEscape(FormTitle) # We escape any strings that WinForms doesn't like, like ampersand and store it in the label
      if debugVerbosity >= 2: self.label.Text += '\n\nTopMost: ' + str(self.TopMost) # Debug
      self.label.Top = 30 # We place the label 30 pixels from the top size of its container panel, and 50 pixels from the left.
      self.label.Left = 50
      self.label.Height = STRheight # We set its dynamic size
      self.label.Width = STRwidth
      labelPanel.Controls.Add(self.label) # We add the label to its container
      
      choicePush = Panel() # An extra secondary container for the buttons, that is not docked, to allow us to slightly change its positioning
      choicePush.Left = (self.ClientSize.Width - choicePush.Width) / 2 # We move it 50 pixels to the left
      choicePush.AutoSize = True # We allow it to expand dynamically
      choicePanel.Controls.Add(choicePush) # We add it to its parent container
      
      for option in FormChoices: # We dynamically add as many buttons as we have options
         btn = Button() # We initialize a button object
         btn.Name = str(self.index) # We name the button equal to its numeric value, plus its effect.
         btn.Text = str(self.index) + ':--> ' + formStringEscape(option)
         self.index = self.index + 1 # The internal of the button is also the choice that will be put in our list of integers. 
         btn.Dock = DockStyle.Top # We dock the buttons one below the other, to the top of their container (choicePush)
         btn.AutoSize = True # Doesn't seem to do anything
         btn.Height = calcStringButtonHeight(formStringEscape(option))
         btn.Click += self.choiceMade # This triggers the function which records each choice into the confirmValue[] list
         choicePush.Controls.Add(btn) # We add each button to its panel
         btn.BringToFront() # Add new buttons to the bottom of existing ones (Otherwise the buttons would be placed in reverse numerical order)

      buttonNext = Button()
      buttonNext.Text = "Next Page"
      buttonNext.Width = 100
      buttonNext.Dock = DockStyle.Bottom
      buttonNext.Click += self.nextPage
      if pages > 1: self.Controls.Add(buttonNext) # We only add the "Confirm" button on a radio menu.

      finishButton = Button() # We add a button to Finish the selection
      finishButton.Text = "Finish Selection"
      finishButton.Width = 100
      finishButton.Dock = DockStyle.Bottom # We dock it to the bottom of the form.
      #button.Anchor = AnchorStyles.Bottom
      finishButton.Click += self.finishPressed # We call its function
      self.Controls.Add(finishButton) # We add the button to the form
 
      cancelButton = Button() # We add a bytton to Cancel the selection
      cancelButton.Text = "Cancel"
      cancelButton.Width = 100
      cancelButton.Dock = DockStyle.Bottom
      #button.Anchor = AnchorStyles.Bottom
      cancelButton.Click += self.cancelPressed
      self.Controls.Add(cancelButton)

   def nextPage(self, sender, args):
      self.nextPageBool = True
      self.timer.Stop()
      self.Close()
 
   def finishPressed(self, sender, args): # The function called from the finishButton.
      self.timer.Stop()
      self.Close()  # It just closes the form

   def cancelPressed(self, sender, args): # The function called from the cancelButton
      self.confirmValue = 'ABORT' # It replaces the choice list with an ABORT message which is parsed by the calling function
      self.timer.Stop()
      self.Close() # And then closes the form
 
   def choiceMade(self, sender, args): # The function called when pressing one of the choice buttons
      self.confirmValue.append((self.currPage * 7) + int(sender.Name)) # We append the button's name to the existing choices list
      self.label.Text = self.origTitle + "\n\nYour current choices are:\n{}".format(self.confirmValue) # We display what choices we've made until now to the player.
 
   def getIndex(self): # The function called after the form is closed, to grab its choices list
      if self.nextPageBool: 
         self.nextPageBool = False
         return "Next Page"
      else: return self.confirmValue

   def getStoredChoices(self): # The function called after the form is closed, to grab its choices list
      return self.confirmValue

   def onTick(self, sender, event): # Ugly hack required because sometimes the winform does not go on top of all
      if self.timer_tries < 3: # Try three times to bring the form on top
         if debugVerbosity >= 2: self.label.Text = self.origTitle + '\n\n### Timer Iter: ' + str(self.timer_tries)
         self.TopMost = False # Set the form as not on top
         self.Focus() # Focus it
         self.Activate() # Activate it
         self.TopMost = True # And re-send it to top
         self.timer_tries += 1 # Increment this counter to stop after 3 tries.

def multiChoice(title, options,card): # This displays a choice where the player can select more than one ability to trigger serially one after the other
   debugNotify(">>> multiChoice()".format(title))
   if Automations['WinForms']: # If the player has not disabled the custom WinForms, we use those
      optChunks=[options[x:x+7] for x in xrange(0, len(options), 7)]
      optCurrent = 0
      choices = "New"
      currChoices = []
      while choices == "New" or choices == "Next Page":
         Application.EnableVisualStyles() # To make the window look like all other windows in the user's system
         if card.Type == 'ICE': CPType = 'Intrusion Countermeasures Electronics'  # Just some nice fluff
         elif re.search(r'Icebreaker', card.Keywords): CPType = 'ICEbreaker GUI'
         elif card.Type == 'Hardware': CPType = 'Dashboard'
         else: CPType = 'Control Panel'
         debugNotify("About to open form")
         form = MultiChoiceWindow(title, optChunks[optCurrent], CPType, pages = len(optChunks), currPage = optCurrent, existingChoices = currChoices) # We create an object called "form" which contains an instance of the MultiChoice windows form.
         form.ShowDialog() # We bring the form to the front to allow the user to make their choices
         choices = form.getIndex() # Once the form is closed, we check an internal variable within the form object to grab what choices they made
         if choices == "Next Page": 
            debugNotify("Going to next page", 3)
            optCurrent += 1
            if optCurrent >= len(optChunks): optCurrent = 0
            currChoices = form.getStoredChoices()
            debugNotify("currChoices = {}".format(currChoices))            
   else: # If the user has disabled the windows forms, we use instead the OCTGN built-in askInteger function
      concatTXT = title + "\n\n(Tip: You can put multiple abilities one after the the other (e.g. '110'). Max 9 at once)\n\n" # We prepare the text of the window with a concat string
      for iter in range(len(options)): # We populate the concat string with the options
         concatTXT += '{}:--> {}\n'.format(iter,options[iter])
      choicesInteger = askInteger(concatTXT,0) # We now ask the user to put in an integer.
      if not choicesInteger: choices = 'ABORT' # If the user just close the window, abort.
      else: 
         choices = list(str(choicesInteger)) # We convert our number into a list of numeric chars
         for iter in range(len(choices)): choices[iter] = int(choices[iter]) # we convert our list of chars into a list of integers      
   debugNotify("<<< multiChoice() with list: {}".format(choices), 3)
   return choices # We finally return a list of integers to the previous function. Those will in turn be iterated one-by-one serially.
      
#---------------------------------------------------------------------------
# Generic
#---------------------------------------------------------------------------

def debugNotify(msg = 'Debug Ping!', level = 2):
   if not re.search(r'<<<',msg) and not re.search(r'>>>',msg):
      hashes = '#' 
      for iter in range(level): hashes += '#' # We add extra hashes at the start of debug messages equal to the level of the debug+1, to make them stand out more
      msg = hashes + ' ' +  msg
   else: level = 1
   if debugVerbosity >= level: notify(msg)

def barNotifyAll(color, msg, remote = False): # A function that takes care to send barNotifyAll() messages to all players
   mute()
   for player in getPlayers():
      if player != me and not remote: remoteCall(player,'barNotifyAll',[color,msg,True])
   notifyBar(color,msg)
   
def num (s):
   #debugNotify(">>> num(){}".format(extraASDebug())) #Debug
   if not s: return 0
   try:
      return int(s)
   except ValueError:
      return 0
      
def numOrder(num):
    """Return the ordinal for each place in a zero-indexed list.

    list[0] (the first item) returns '1st', list[1] return '2nd', etc.
    """
    def int_to_ordinal(i):
        """Return the ordinal for an integer."""
        # if i is a teen (e.g. 14, 113, 2517), append 'th'
        if 10 <= i % 100 < 20:
            return str(i) + 'th'
        # elseif i ends in 1, 2 or 3 append 'st', 'nd' or 'rd'
        # otherwise append 'th'
        else:
            return  str(i) + {1 : 'st', 2 : 'nd', 3 : 'rd'}.get(i % 10, "th")

    return int_to_ordinal(num + 1)

def chooseSide(): # Called from many functions to check if the player has chosen a side for this game.
   debugNotify(">>> chooseSide(){}".format(extraASDebug())) #Debug
   mute()
   global playerside, playeraxis
   if playerside == None:  # Has the player selected a side yet? If not, then...
     if me.hasInvertedTable():
        playeraxis = Yaxis
        playerside = -1
     else:
        playeraxis = Yaxis
        playerside = 1
   debugNotify("<<< chooseSide(){}".format(extraASDebug()), 4) #Debug

def displaymatch(match):
   if match is None:
      return None
   return '<Match: {}, groups={}>'.format(match.group(), match.groups())
   
def storeProperties(card, forced = False): # Function that grabs a cards important properties and puts them in a dictionary
   mute()
   try:
      debugNotify(">>> storeProperties(){}".format(extraASDebug())) #Debug
      global Stored_Name, Stored_Cost, Stored_Type, Stored_Keywords, Stored_AutoActions, Stored_AutoScripts, identName
      if (card.Name == '?' and Stored_Name.get(card._id,'?') == '?') or forced:
         if not card.isFaceUp and ((card.group == table and card.owner == me) or forced): # If card is not ours and it's face down, we cannot store its properties without revealing it to the player via the full game log
                                                                                             # See https://github.com/kellyelton/OCTGN/issues/879
            card.peek()
            loopChk(card)
      if (Stored_Name.get(card._id,'?') == '?' and card.Name != '?') or (Stored_Name.get(card._id,'?') != card.Name and card.Name != '?') or forced:
         debugNotify("{} not stored. Storing...".format(card), 3)
         Stored_Name[card._id] = card.Name
         Stored_Cost[card._id] = card.Cost
         Stored_Type[card._id] = card.Type
         getKeywords(card)
         Stored_AutoActions[card._id] = CardsAA.get(card.model,'')
         Stored_AutoScripts[card._id] = CardsAS.get(card.model,'')
         if card.Type == 'Identity' and card.owner == me: identName = card.Name
      elif card.Name == '?':
         debugNotify("Could not store card properties because it is hidden from us")
         return 'ABORT'
      debugNotify("<<< storeProperties()", 3)
   except: notify("!!!ERROR!!! In storeProperties()")

def fetchProperty(card, property): 
   mute()
   debugNotify(">>> fetchProperty(){}".format(extraASDebug())) #Debug
   if property == 'name' or property == 'Name': currentValue = Stored_Name.get(card._id,'?')
   elif property == 'Cost': currentValue = Stored_Cost.get(card._id,'?')
   elif property == 'Type': currentValue = Stored_Type.get(card._id,'?')
   elif property == 'Keywords': currentValue = Stored_Keywords.get(card._id,'?')
   elif property == 'AutoScripts': currentValue = Stored_AutoScripts.get(card._id,'?')
   elif property == 'AutoActions': currentValue = Stored_AutoActions.get(card._id,'?')
   else: currentValue = card.properties[property]
   if currentValue == '?' or currentValue == 'Card':
      debugNotify("Card property: {} unreadable = {}".format(property,currentValue), 4) #Debug
      if not card.isFaceUp and card.group == table and card.owner == me:
         debugNotify("Need to peek card to read its properties.", 3) #Debug
         if debugVerbosity >= 0 and confirm("Peek at card? (>>>fetchProperty())"): card.peek()
         loopChk(card)
      debugNotify("Ready to grab real properties.", 3) #Debug
      if property == 'name': currentValue = card.Name # Now that we had a chance to peek at the card, we grab its property again.
      else: 
         currentValue = card.properties[property]
         debugNotify("Grabbing {}'s {} manually: {}.".format(card,property,card.properties[property]), 3)
         #storeProperties(card) # Commented out because putting it here can cause an infinite loop
   debugNotify("<<< fetchProperty() by returning: {}".format(currentValue), 4)
   if not currentValue: currentValue = ''
   return currentValue

def clearCovers(): # Functions which goes through the table and clears any cover cards
   debugNotify(">>> clearCovers()") #Debug
   for cover in table:
      if cover.model == 'ac3a3d5d-7e3a-4742-b9b2-7f72596d9c1b': cover.moveTo(me.piles['Removed from Game'])

def findOpponent():
   # Just a quick function to make the code more readable
   return ofwhom('ofOpponent')
   
def loopChk(card,property = 'Type'):
   debugNotify(">>> loopChk(){}".format(extraASDebug())) #Debug
   loopcount = 0
   while card.properties[property] == '?':
      rnd(1,10)
      update()
      loopcount += 1
      if loopcount == 5:
         whisper(":::Error::: Card property can't be grabbed. Aborting!")
         return 'ABORT'
   debugNotify("<<< loopChk()", 3) #Debug
   return 'OK'         
   
def sortPriority(cardList):
   debugNotify(">>> sortPriority()") #Debug
   priority1 = []
   priority2 = []
   priority3 = []
   sortedList = []
   for card in cardList:
      if card.highlight == PriorityColor: # If a card is clearly highlighted for priority, we use its counters first.
         priority1.append(card)
      elif card.targetedBy and card.targetedBy == me: # If a card it targeted, we give it secondary priority in losing its counters.
         priority2.append(card)   
      else: # If a card is neither of the above, then the order is defined on how they were put on the table.
         priority3.append(card) 
   sortedList.extend(priority1)
   sortedList.extend(priority2)
   sortedList.extend(priority3)
   if debugVerbosity >= 3: 
      tlist = []
      for sortTarget in sortedList: tlist.append(fetchProperty(sortTarget, 'name')) # Debug   
      notify("<<< sortPriority() returning {}".format(tlist)) #Debug
   return sortedList
   
def oncePerTurn(card, x = 0, y = 0, silent = False, act = 'manual'):
   debugNotify(">>> oncePerTurn(){}".format(extraASDebug())) #Debug
   mute()
   if card.orientation == Rot90:
      if act != 'manual': return 'ABORT' # If the player is not activating an effect manually, we always fail silently. So as not to spam the confirm.
      elif not confirm("The once-per-turn ability of {} has already been used this turn\nBypass restriction?.".format(fetchProperty(card, 'name'))): return 'ABORT'
      else: 
         if not silent and act != 'dryRun': notify('{} activates the once-per-turn ability of {} another time'.format(me, card))
   else:
      if not silent and act != 'dryRun': notify('{} activates the once-per-turn ability of {}'.format(me, card))
   if act != 'dryRun': 
      if card.controller != me: remoteCall(card.controller,'rotCard',card) # Cannot remote call this or ABT installing more than 1 ICE will trigger HB:ETF ability 3 times
      else: card.orientation = Rot90
   debugNotify("<<< oncePerTurn() exit OK", 3) #Debug

def chkRestrictionMarker(card, Autoscript, silent = False, act = 'manual'): # An additional oncePerTurn restriction, that works with markers (with cards that have two different once-per-turn abilities)
   debugNotify(">>> chkRestrictionMarker(){}".format(extraASDebug())) #Debug
   mute()
   restrictedMarkerRegex  = re.search(r"restrictionMarker([A-Za-z0-9_:' ]+)",Autoscript)
   if restrictedMarkerRegex:
      debugNotify("restrictedMarker = {}".format(restrictedMarkerRegex.group(1)))
      restrictedMarker = findMarker(card, restrictedMarkerRegex.group(1))
      if restrictedMarker:
         if act != 'manual': return 'ABORT' # If the player is not activating an effect manually, we always fail silently. So as not to spam the confirm.
         elif not confirm("The once-per-turn ability of {} has already been used this turn\nBypass restriction?.".format(fetchProperty(card, 'name'))): return 'ABORT'
         else: 
            if not silent and act != 'dryRun': notify('{} activates the once-per-turn ability of {} another time'.format(me, card))
      else:
         if not silent and act != 'dryRun': notify('{} activates the once-per-turn ability of {}'.format(me, card))
      if act != 'dryRun': TokensX('Put1{}-isSilent'.format(restrictedMarkerRegex.group(1)), '', card)
   debugNotify("<<< chkRestrictionMarker()") #Debug

def clearRestrictionMarkers(remoted = False):
   debugNotify(">>> clearRestrictionMarkers(){}".format(extraASDebug())) #Debug
   if not remoted:
      for player in getPlayers():
         remoteCall(player,'clearRestrictionMarkers',[True])
   for card in table:
      if card.controller == me: 
         for Autoscript in CardsAS.get(card.model,'').split('||'):
            restrictedMarkerRegex  = re.search(r"restrictionMarker([A-Za-z0-9_:' ]+)",Autoscript)
            if restrictedMarkerRegex:
               restrictedMarker = findMarker(card, restrictedMarkerRegex.group(1))
               if restrictedMarker: card.markers[restrictedMarker] = 0
   debugNotify("<<< clearRestrictionMarkers()") #Debug
         
def delayed_whisper(text): # Because whispers for some reason execute before notifys
   rnd(1,10)
   whisper(text)   
   
def chkModulator(card, modulator, scriptType = 'onPlay'): # Checks the card's autoscripts for the existence of a specific modulator
   debugNotify(">>> chkModulator() looking for {}".format(modulator)) #Debug
   debugNotify("scriptType = {}".format(scriptType)) #Debug
   ModulatorExists = False
   Autoscripts = CardsAS.get(card.model,'').split('||')
   for autoS in Autoscripts:
      debugNotify("Checking {}'s AS: {}".format(card,autoS))
      if not re.search(r'{}'.format(scriptType),autoS): 
         debugNotify("Rejected!",4)
         continue
      # We check the script only if it matches the script type we're looking for.
      # So if we're checking if a specific onTrash modulator exists on the card, we only check for "onTrash" scripts.
      if re.search(r'{}'.format(modulator),autoS): 
         debugNotify("Modulator Matches!",4)
         ModulatorExists = True
   debugNotify("<<< chkModulator() with return {}".format(ModulatorExists)) #Debug
   return ModulatorExists

def fetchHost(card):
   debugNotify(">>> fetchHost()") #Debug
   host = None
   hostCards = eval(getGlobalVariable('Host Cards'))
   hostID = hostCards.get(card._id,None)
   if hostID: host = Card(hostID) 
   debugNotify("<<< fetchHost() with return {}".format(host)) #Debug
   return host
   
#---------------------------------------------------------------------------
# Card Placement functions
#---------------------------------------------------------------------------

def cwidth(card, divisor = 10):
   #debugNotify(">>> cwidth(){}".format(extraASDebug())) #Debug
# This function is used to always return the width of the card plus an offset that is based on the percentage of the width of the card used.
# The smaller the number given, the less the card is divided into pieces and thus the larger the offset added.
# For example if a card is 80px wide, a divisor of 4 will means that we will offset the card's size by 80/4 = 20.
# In other words, we will return 1 + 1/4 of the card width. 
# Thus, no matter what the size of the table and cards becomes, the distances used will be relatively the same.
# The default is to return an offset equal to 1/10 of the card width. A divisor of 0 means no offset.
   if divisor == 0: offset = 0
   else: offset = card.width() / divisor
   return (card.width() + offset)

def cheight(card, divisor = 10):
   #debugNotify(">>> cheight(){}".format(extraASDebug())) #Debug
   if divisor == 0: offset = 0
   else: offset = card.height() / divisor
   return (card.height() + offset)

def yaxisMove(card):
   #debugNotify(">>> yaxisMove(){}".format(extraASDebug())) #Debug
# Variable to move the cards played by player 2 on a 2-sided table, more towards their own side. 
# Player's 2 axis will fall one extra card length towards their side.
# This is because of bug #146 (https://github.com/kellyelton/OCTGN/issues/146)
   if me.hasInvertedTable(): cardmove = cheight(card)
   else: cardmove = cardmove = 0
   return cardmove

  
#---------------------------------------------------------------------------
# Remote Calls
#---------------------------------------------------------------------------   

def grabPileControl(pile, player = me):
   debugNotify(">>> grabPileControl(){}".format(extraASDebug())) #Debug
   debugNotify("Grabbing control of {}'s {} on behalf of {}".format(pile.player,pile.name,player))
   if pile.controller != player:
      if pile.controller != me: remoteCall(pile.controller,'passPileControl',[pile,player])
      else: passPileControl(pile,player) # We don't want to do a remote call if the current controller is ourself, as the call we go out after we finish all scripts, which will end up causing a delay later while the game is checking if control pass is done.
   count = 0
   while pile.controller != player: 
      if count >= 2 and not count % 2: notify("=> {} is still trying to take control of {}...".format(player,pileName(pile)))
      rnd(1,100)
      count += 1
      if count >= 3: 
         notify(":::ERROR::: Pile Control not passed! Will see errors.")
         break   
   debugNotify("<<< grabPileControl(){}".format(extraASDebug())) #Debug

def passPileControl(pile,player):
   debugNotify(">>> passPileControl(){}".format(extraASDebug())) #Debug
   mute()
   update()
   pile.setController(player)
   debugNotify("<<< passPileControl(){}".format(extraASDebug())) #Debug
      
def grabCardControl(card, player = me):
   debugNotify(">>> grabCardControl(){}".format(extraASDebug())) #Debug
   debugNotify("Grabbing control of {} on behalf of {}".format(card,player))
   if card.group != table: debugNotify(":::WARNING::: Cannot grab card control while in a pile. Aborting!")
   else:
      if card.controller != player: 
         if card.controller != me: remoteCall(card.controller,'passCardControl',[card,player])
         else: passCardControl(card,player) # We don't want to do a remote call if the current controller is ourself, as the call we go out after we finish all scripts, which will end up causing a delay later while the game is checking if control pass is done.
      count = 0
      while card.controller != player: 
         if count >= 2 and not count % 2: notify("=> {} is still trying to take control of {}...".format(player,card))
         rnd(1,100)
         count += 1
         if count >= 3: 
            notify(":::ERROR::: Card Control not passed! Will see errors.")
            break   
   debugNotify("<<< grabCardControl(){}".format(extraASDebug())) #Debug
   
def passCardControl(card,player):
   debugNotify(">>> passCardControl(){}".format(extraASDebug())) #Debug
   debugNotify("card ={}, player = {}".format(card,player))
   mute()
   update()
   debugNotify("Getting ready to pass card control")
   if card.controller != player: card.setController(player)
   debugNotify("<<< passCardControl()") #Debug
      
def changeCardGroup(card, group): # A cumulative function to take care for handling card and group control when moving a card from one group to another.
   debugNotify(">>> changeCardGroup(){}".format(extraASDebug())) #Debug
   debugNotify("Will move {} to {}'s {}".format(card,group.player,group.name))
   prevGroup = card.group
   if prevGroup == table: grabCardControl(card) # We take control of the card, but only if it's on the table, otherwise we can't.
   else: grabPileControl(prevGroup)
   grabPileControl(group) # We take control of the target pile
   storeProperties(card) # Since we're at it, we might as well store its properties for later
   debugNotify("Finished Taking Control. Moving card to different group",1)
   card.moveTo(group) # We move the card into the target pile
   if group.player != group.controller: grabPileControl(group,group.player) # We return control of the target pile to its original owner.
   if prevGroup != table and prevGroup.player != prevGroup.controller: grabPileControl(prevGroup,prevGroup.player) # If we took control of a whole pile to allow us to move the card, we return it now
   debugNotify("<<< changeCardGroup(){}".format(extraASDebug())) #Debug

def placeOnTable(card,x,y,facedownStatus = False): # A function that asks the current card controller to move a card to another table position
   if card.controller == me: card.moveToTable(x, y, facedownStatus)
   else: remoteCall(card.controller,'placeOnTable',[card,x,y,facedownStatus])
   
def indexSet(card,index): # A function that asks the current card controller to move the card to a specific index.
   if card.controller == me: 
      if index == 'front': card.sendToFront()
      elif index == 'back': card.sendToBack()
      else: card.setIndex(index) 
   else: remoteCall(card.controller,'indexSet',[card,index])
   
def rotCard(card):
   mute()
   card.orientation = Rot90
      
def grabVisibility(group):
   mute()
   group.setVisibility('me')      
#---------------------------------------------------------------------------
# Patron Functions
#---------------------------------------------------------------------------   

def prepPatronLists():
   global supercharged,customized
   supercharged = SuperchargedSubs + CustomSubs + CardSubs
   customized = CustomSubs + CardSubs
   debugNotify("supercharged = {}".format(supercharged))
   
def superCharge(card):
   if me.name.lower() in supercharged: card.switchTo('Supercharged')
   if me.name.lower() in CardSubs: card.switchTo(me.name.lower())
      
def announceSupercharge():
   if me.name.lower() in supercharged:
      notify("   \n+=+ {}\n".format(CustomMsgs.get(me.name.lower(),SuperchargedMsg))) # We either announce a player's custom message, or the generic supercharged one
      
def announceSoT():
   statsTXT = "They have {}, {} cards and {} {} starting this turn.".format(uniCredit(me.Credits),len(me.hand),me.Clicks,uniClick())
   if ds == "corp": 
      announceTXT = "The offices of {} ({}) are now open for business.".format(identName,me)
      if corpStartMsgs.get(me.name.lower(),None): customTXT = "\n\n{}\n".format(corpStartMsgs[me.name.lower()])
      else: customTXT = ''
      #notify("=> The offices of {} ({}) are now open for business.\n They have {} and {} {} for this turn.".format(identName,me,uniCredit(me.Credits),me.Clicks,uniClick()))
   else:
      announceTXT = "{} ({}) has woken up.".format(identName,me)
      if runnerStartMsgs.get(me.name.lower(),None): customTXT = "\n\n{}\n".format(runnerStartMsgs[me.name.lower()])
      else: customTXT = ''
      #notify ("=> {} ({}) has woken up. They have {} and {} {} for this turn.".format(identName,me,uniCredit(me.Credits),me.Clicks,uniClick()))
   #if ds == 'runner': barNotifyAll('#AA0000',"{} has started their turn".format(me))
   #else: barNotifyAll('#0000FF',"{} has started their turn".format(me))
   notify("=> {}{}".format(announceTXT,customTXT)) 
   notify("=> {}".format(statsTXT))
   if ds == 'runner' and chkTags(): notify(":::Reminder::: {} is Tagged!".format(identName))

def announceEoT():
   statsTXT = "They end their turn with {}, {} cards in their {}, and {} cards in their {}.".format(uniCredit(me.Credits),len(me.hand),pileName(me.hand),len(me.piles['R&D/Stack']),pileName(me.piles['R&D/Stack']))
   if ds == "corp": 
      announceTXT = "{} ({}) has reached CoB.".format(identName, me)
      if corpEndMsgs.get(me.name.lower(),None): customTXT = "\n\n{}\n".format(corpEndMsgs[me.name.lower()])
      else: customTXT = ''
   else:
      announceTXT = "{} ({}) has gone to sleep for the day.".format(identName,me)
      if runnerEndMsgs.get(me.name.lower(),None): customTXT = "\n\n{}\n".format(runnerEndMsgs[me.name.lower()])
      else: customTXT = ''
   #if ds == 'runner': barNotifyAll('#880000',"{} has ended their turn".format(me))
   #else: barNotifyAll('#0000AA',"{} has ended their turn".format(me))
   notify("=> {}{}".format(announceTXT,customTXT)) 
   notify("=> {}".format(statsTXT))
      
########NEW FILE########
__FILENAME__ = meta
﻿    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

###==================================================File Contents==================================================###
# This file contains scripts which are not used to play the actual game, but is rather related to the rules of engine
# * [Generic Netrunner] functions are not doing something in the game by themselves but called often by the functions that do.
# * In the [Switches] section are the scripts which controls what automations are active.
# * [Help] functions spawn tokens on the table with succint information on how to play the game.
# * [Button] functions are trigered either from the menu or from the button cards on the table, and announce a specific message each.
# * [Debug] if for helping the developers fix bugs
# * [Online Functions] is everything which connects to online files for some purpose, such as checking the game version or displaying a message of the day
###=================================================================================================================###
import re, time
#import sys # Testing
#import dateutil # Testing
#import elementtree # Testing
#import decimal # Testing

try:
    import os
    if os.environ['RUNNING_TEST_SUITE'] == 'TRUE':
        me = object
        table = object
except ImportError:
    pass

Automations = {'Play, Score and Rez'    : True, # If True, game will automatically trigger card effects when playing or double-clicking on cards. Requires specific preparation in the sets.
               'Start/End-of-Turn'      : True, # If True, game will automatically trigger effects happening at the start of the player's turn, from cards they control.
               'Damage Prevention'      : True, # If True, game will automatically use damage prevention counters from card they control.
               'Triggers'               : True, # If True, game will search the table for triggers based on player's actions, such as installing a card, or trashing one.
               'WinForms'               : True, # If True, game will use the custom Windows Forms for displaying multiple-choice menus and information pop-ups
               'Quick Access'           : False,# If True, game will enable quick access
               'Damage'                 : True}

UniCode = True # If True, game will display credits, clicks, trash, memory as unicode characters

debugVerbosity = -1 # At -1, means no debugging messages display

startupMsg = False # Used to check if the player has checked for the latest version of the game.

gameGUID = None # A Unique Game ID that is fetched during game launch.
#totalInfluence = 0 # Used when reporting online
#gameEnded = False # A variable keeping track if the players have submitted the results of the current game already.
turn = 0 # used during game reporting to report how many turns the game lasted
AccessBtnNextChoice = 0
askedQA = False

CardsAA = {} # Dictionary holding all the AutoAction scripts for all cards
CardsAS = {} # Dictionary holding all the AutoScript scripts for all cards


#---------------------------------------------------------------------------
# Generic Netrunner functions
#---------------------------------------------------------------------------
def uniCredit(count):
   debugNotify(">>> uniCredit(){}".format(extraASDebug())) #Debug
   count = num(count)
   if UniCode: return "{} ¥".format(count)
   else: 
      if count == 1: grammar = 's'
      else: grammar =''
      return "{} Credit{}".format(count,grammar)
 
def uniRecurring(count):
   debugNotify(">>> uniRecurring(){}".format(extraASDebug())) #Debug
   count = num(count)
   if UniCode: return "{} £".format(count)
   else: 
      if count == 1: grammar = 's'
      else: grammar =''
      return "{} Recurring Credit{}".format(count,grammar)
 
def uniClick():
   debugNotify(">>> uniClick(){}".format(extraASDebug())) #Debug
   if UniCode: return ' ⌚'
   else: return '(/)'

def uniTrash():
   debugNotify(">>> uniTrash(){}".format(extraASDebug())) #Debug
   if UniCode: return '⏏'
   else: return 'Trash'

def uniMU(count = 1):
   debugNotify(">>> uniMU(){}".format(extraASDebug())) #Debug
   if UniCode: 
      if num(count) == 1: return '⎗'
      elif num(count) == 2:  return '⎘'
      else: return '{} MU'.format(count)
   else: return '{} MU'.format(count)
   
def uniLink():
   debugNotify(">>> uniLink(){}".format(extraASDebug())) #Debug
   if UniCode: return '⎙'
   else: return 'Base Link'

def uniSubroutine():
   debugNotify(">>> uniLink(){}".format(extraASDebug())) #Debug
   if UniCode: return '⏎'
   else: return '[Subroutine]'

def chooseWell(limit, choiceText, default = None):
   debugNotify(">>> chooseWell(){}".format(extraASDebug())) #Debug
   if default == None: default = 0# If the player has not provided a default value for askInteger, just assume it's the max.
   choice = limit # limit is the number of choices we have
   if limit > 1: # But since we use 0 as a valid choice, then we can't actually select the limit as a number
      while choice >= limit:
         choice = askInteger("{}".format(choiceText), default)
         if not choice: return False
         if choice > limit: whisper("You must choose between 0 and {}".format(limit - 1))
   else: choice = 0 # If our limit is 1, it means there's only one choice, 0.
   return choice

def findMarker(card, markerDesc): # Goes through the markers on the card and looks if one exist with a specific description
   debugNotify(">>> findMarker() on {} with markerDesc = {}".format(card,markerDesc)) #Debug
   foundKey = None
   if markerDesc in mdict: markerDesc = mdict[markerDesc][0] # If the marker description is the code of a known marker, then we need to grab the actual name of that.
   for key in card.markers:
      debugNotify("Key: {}\nmarkerDesc: {}".format(key[0],markerDesc), 3) # Debug
      if re.search(r'{}'.format(markerDesc),key[0]) or markerDesc == key[0]:
         foundKey = key
         debugNotify("Found {} on {}".format(key[0],card), 2)
         break
   debugNotify("<<< findMarker() by returning: {}".format(foundKey), 3)
   return foundKey
   
def getKeywords(card): # A function which combines the existing card keywords, with markers which give it extra ones.
   debugNotify(">>> getKeywords(){}".format(extraASDebug())) #Debug
   global Stored_Keywords
   #confirm("getKeywords") # Debug
   keywordsList = []
   cKeywords = card.Keywords # First we try a normal grab, if the card properties cannot be read, then we flip face up.
   if cKeywords == '?': cKeywords = fetchProperty(card, 'Keywords')
   strippedKeywordsList = cKeywords.split('-')
   for cardKW in strippedKeywordsList:
      strippedKW = cardKW.strip() # Remove any leading/trailing spaces between traits. We need to use a new variable, because we can't modify the loop iterator.
      if strippedKW: keywordsList.append(strippedKW) # If there's anything left after the stip (i.e. it's not an empty string anymrore) add it to the list.   
   if card.markers:
      for key in card.markers:
         markerKeyword = re.search('Keyword:([\w ]+)',key[0])
         if markerKeyword:
            #confirm("marker found: {}\n key: {}".format(markerKeyword.groups(),key[0])) # Debug
            #if markerKeyword.group(1) == 'Barrier' or markerKeyword.group(1) == 'Sentry' or markerKeyword.group(1) == 'Code Gate': #These keywords are mutually exclusive. An Ice can't be more than 1 of these
               #if 'Barrier' in keywordsList: keywordsList.remove('Barrier') # It seems in ANR, they are not so mutually exclusive. See: Tinkering
               #if 'Sentry' in keywordsList: keywordsList.remove('Sentry') 
               #if 'Code Gate' in keywordsList: keywordsList.remove('Code Gate')
            if re.search(r'Breaker',markerKeyword.group(1)):
               if 'Barrier Breaker' in keywordsList: keywordsList.remove('Barrier Breaker')
               if 'Sentry Breaker' in keywordsList: keywordsList.remove('Sentry Breaker')
               if 'Code Gate Breaker' in keywordsList: keywordsList.remove('Code Gate Breaker')
            keywordsList.append(markerKeyword.group(1))
   keywords = ''
   for KW in keywordsList:
      keywords += '{}-'.format(KW)
   Stored_Keywords[card._id] = keywords[:-1] # We also update the global variable for this card, which is used by many functions.
   debugNotify("<<< getKeywords() by returning: {}.".format(keywords[:-1]), 3)
   return keywords[:-1] # We need to remove the trailing dash '-'
   
def pileName(group):
   debugNotify(">>> pileName()") #Debug
   debugNotify("pile name {}".format(group.name), 2) #Debug   
   debugNotify("pile player: {}".format(group.player), 2) #Debug
   if group.name == 'Table': name = 'Table'
   elif group.name == 'Heap/Archives(Face-up)':
      if group.player.getGlobalVariable('ds') == 'corp': name = 'Face-up Archives'
      else: name = 'Heap'
   elif group.name == 'R&D/Stack':
      if group.player.getGlobalVariable('ds') == 'corp': name = 'R&D'
      else: name = 'Stack'
   elif group.name == 'Archives(Hidden)': name = 'Hidden Archives'
   else:
      if group.player.getGlobalVariable('ds') == 'corp': name = 'HQ'
      else: name = 'Grip'
   debugNotify("<<< pileName() by returning: {}".format(name), 3)
   return name

def clearNoise(): # Clears all player's noisy bits. I.e. nobody is considered to have been noisy this turn.
   debugNotify(">>> clearNoise()") #Debug
   for player in players: player.setGlobalVariable('wasNoisy', '0') 
   debugNotify("<<< clearNoise()", 3) #Debug

def storeSpecial(card): 
# Function stores into a shared variable some special cards that other players might look up.
   try:
      debugNotify(">>> storeSpecial(){}".format(extraASDebug())) #Debug
      storeProperties(card, True)
      specialCards = eval(me.getGlobalVariable('specialCards'))
      if card.name == 'HQ' or card.name == 'R&D' or card.name == 'Archives':
         specialCards[card.name] = card._id # The central servers we find via name
      else: specialCards[card.Type] = card._id
      me.setGlobalVariable('specialCards', str(specialCards))
   except: notify("!!!ERROR!!! In storeSpecial()")

def getSpecial(cardType,player = me):
# Functions takes as argument the name of a special card, and the player to whom it belongs, and returns the card object.
   debugNotify(">>> getSpecial() for player: {}".format(me.name)) #Debug
   specialCards = eval(player.getGlobalVariable('specialCards'))
   cardID = specialCards.get(cardType,None)
   if not cardID: 
      debugNotify("No special card of type {} found".format(cardType),2)
      card = None
   else:
      card = Card(specialCards[cardType])
      debugNotify("Stored_Type = {}".format(Stored_Type.get(card._id,'NULL')), 2)
      if Stored_Type.get(card._id,'NULL') == 'NULL':
         #if card.owner == me: delayed_whisper(":::DEBUG::: {} was NULL. Re-storing as an attempt to fix".format(cardType)) # Debug
         debugNotify("card ID = {}".format(card._id))
         debugNotify("Stored Type = {}".format(Stored_Type.get(card._id,'NULL')))
         storeProperties(card, True)
   debugNotify("<<< getSpecial() by returning: {}".format(card), 3)
   return card

def chkRAM(card, action = 'INSTALL', silent = False):
   debugNotify(">>> chkRAM(){}".format(extraASDebug())) #Debug
   MUreq = num(fetchProperty(card,'Requirement'))
   hostCards = eval(getGlobalVariable('Host Cards'))
   if hostCards.has_key(card._id): hostC = Card(hostCards[card._id])
   else: hostC = None
   if (MUreq > 0
         and not (card.markers[mdict['DaemonMU']] and not re.search(r'Daemon',getKeywords(card)))
         and not findMarker(card,'Daemon Hosted MU')
         and not (card.markers[mdict['Cloud']] and card.markers[mdict['Cloud']] >= 1) # If the card is already in the cloud, we do not want to modify the player's MUs
         and not (hostC and findMarker(card, '{} Hosted'.format(hostC.name)) and hostC.name != "Scheherazade") # No idea if this will work.
         and card.highlight != InactiveColor 
         and card.highlight != RevealedColor):
      if action == 'INSTALL':
         card.owner.MU -= MUreq
         chkCloud(card)
         update()
         if not card.markers[mdict['Cloud']]:
            MUtext = ", using up  {}".format(uniMU(MUreq))
         else: MUtext = ''
      elif action == 'UNINSTALL':
         card.owner.MU += MUreq
         MUtext = ", freeing up  {}".format(uniMU(MUreq))
   else: MUtext = ''
   if card.owner.MU < 0 and not silent: 
      notify(":::Warning:::{}'s programs require more memory than they have available. They must trash enough programs to bring their available Memory to at least 0".format(card.controller))
      information(":::ATTENTION:::\n\nYou are now using more MUs than you have available memory!\
                  \nYou need to trash enough programs to bring your Memory to 0 or higher")
   debugNotify("<<< chkRAM() by returning: {}".format(MUtext), 3)
   return MUtext

def chkCloud(cloudCard = None): # A function which checks the table for cards which can be put in the cloud and thus return their used MUs
   debugNotify(">>> chkCloud(){}".format(extraASDebug())) #Debug
   if not cloudCard: cards = [c for c in table if c.Type == 'Program']
   else: cards = [cloudCard] # If we passed a card as a variable, we just check the cloud status of that card
   for card in cards:
      debugNotify("Cloud Checking {} with AS = {}".format(card,fetchProperty(card, 'AutoScripts')), 2) #Debug
      cloudRegex = re.search(r'Cloud([0-9]+)Link',fetchProperty(card, 'AutoScripts'))
      if cloudRegex:
         linkRequired = num(cloudRegex.group(1))
         debugNotify("Found Cloud Regex. linkRequired = {}".format(linkRequired), 2) #Debug
         if linkRequired <= card.controller.counters['Base Link'].value and not card.markers[mdict['Cloud']]:
            card.markers[mdict['Cloud']] = 1
            card.controller.MU += num(card.Requirement)
            notify("-- {}'s {} has been enabled for cloud computing".format(me,card))            
         if linkRequired > card.controller.counters['Base Link'].value and card.markers[mdict['Cloud']] and card.markers[mdict['Cloud']] >= 1:
            card.markers[mdict['Cloud']] = 0
            card.controller.MU -= num(card.Requirement)
            notify("-- {}'s {} has lost connection to the cloud.".format(me,card))
            if card.controller.MU < 0: 
               notify(":::Warning:::{}'s loss of cloud connection means that their programs require more memory than they have available. They must trash enough programs to bring their available Memory to at least 0".format(card.controller))
   debugNotify("<<< chkCloud()", 3)
            
   
def chkHostType(card, seek = 'Targeted', caissa = False):
   debugNotify(">>> chkHostType(){}".format(extraASDebug())) #Debug
   # Checks if the card needs to have a special host targeted before it can come in play.
   if caissa: hostType = re.search(r'CaissaPlace:([A-Za-z1-9:_ -]+)', fetchProperty(card, 'AutoScripts'))
   else: hostType = re.search(r'Placement:([A-Za-z1-9:_ -]+)', fetchProperty(card, 'AutoScripts'))
   if hostType:
      debugNotify("hostType: {}.".format(hostType.group(1)), 2) #Debug
      if hostType.group(1) == 'ICE': host = findTarget('{}-isICE-choose1'.format(seek))
      else: host = findTarget('{}-at{}-choose1'.format(seek,hostType.group(1)),card = card)
      if len(host) == 0:
         delayed_whisper("ABORTING!")
         result = 'ABORT'
      else: result = host[0] # If a propert host is targeted, then we return it to the calling function. We always return just the first result.
   else: result = None
   debugNotify("<<< chkHostType() with result {}".format(result), 3)
   return result
   
def chkDoublePrevention():
   # This function checks for various cards which, if present prevent extra costs from double cards.
   debugNotify(">>> chkDoublePrevention(){}".format(extraASDebug())) #Debug
   fullCostPrev = False
   for c in table: 
      if fullCostPrev: break # If we already prevented the full cost, let's break out of the loop.
      if c.name == 'Starlight Crusade Funding' and c.controller == me: 
         notify("--> {} has allowed {} to ignore the additional costs".format(c,me))
         fullCostPrev = True
   debugNotify("<<< chkDoublePrevention() with fullCostPrev = {}".format(fullCostPrev)) #Debug
   return fullCostPrev
 
def scanTable(group = table, x=0,y=0):
   debugNotify(">>> scanTable(){}".format(extraASDebug())) #Debug
   global Stored_Name, Stored_Type, Stored_Cost, Stored_Keywords, Stored_AutoActions, Stored_AutoScripts
   if not confirm("This action will clear the internal variables and re-scan all cards in the table to fix them.\
                 \nThis action should only be used as a last-ditch effort to fix some weird behaviour in the game (e.g. treating an Ice like Agenda, or something silly like that)\
               \n\nHowever this may take some time, depending on your PC power.\
                 \nAre you sure you want to proceed?"): return
   Stored_Name.clear()
   Stored_Type.clear()
   Stored_Cost.clear()
   Stored_Keywords.clear()
   Stored_AutoActions.clear()
   Stored_AutoScripts.clear()
   cardList = [card for card in table]
   iter = 0
   for c in cardList:
      if iter % 10 == 0: whisper("Working({}/{} done)...".format(iter, len(cardList)))
      storeProperties(c)
      iter += 1
   for c in me.hand: storeProperties(c)
   notify("{} has re-scanned the table and refreshed their internal variables.".format(me))
 
def checkUnique (card, manual = False):
   debugNotify(">>> checkUnique(){}".format(extraASDebug())) #Debug
   mute()
   if not re.search(r'Unique', getKeywords(card)): 
      debugNotify("<<< checkUnique() - Not a unique card", 3) #Debug
      return True #If the played card isn't unique do nothing.
   cName = fetchProperty(card, 'name')
   ExistingUniques = [ c for c in table
                       if c.owner == me 
                       and c.controller == me 
                       and c.isFaceUp 
                       and c.name == cName ]
   if ((not manual and len(ExistingUniques) != 0) or (manual and len(ExistingUniques) != 1)) and not confirm("This unique card is already in play. Are you sure you want to play {}?\n\n(If you do, your existing unique card will be Trashed at no cost)".format(fetchProperty(card, 'name'))) : return False
   else:
      count = len(ExistingUniques)
      for uniqueC in ExistingUniques: 
         if manual and count == 1: break # If it's a manual, the new unique card is already on the table, so we do not want to trash it as well.
         trashForFree(uniqueC)
         count -= 1
   debugNotify("<<< checkUnique() - Returning True", 3) #Debug
   return True   

def chkTargeting(card):
   debugNotify(">>> chkTargeting(){}".format(extraASDebug())) #Debug
   if (re.search(r'on(Rez|Play|Install)[^|]+(?<!Auto)Targeted', CardsAS.get(card.model,''))
         and len(findTarget(CardsAS.get(card.model,''))) == 0
         and not re.search(r'isOptional', CardsAS.get(card.model,''))
         and not confirm("This card requires a valid target for it to work correctly.\
                        \nIf you proceed without a target, strange things might happen.\
                      \n\nProceed anyway?")):
      return 'ABORT'
   if ds == 'corp': runnerPL = findOpponent()
   else: runnerPL = me
   if re.search(r'ifTagged', CardsAS.get(card.model,'')) and runnerPL.Tags == 0 and not re.search(r'isOptional', CardsAS.get(card.model,'')) and not re.search(r'doesNotBlock', CardsAS.get(card.model,'')):
      whisper("{} must be tagged in order to use this card".format(runnerPL))
      return 'ABORT'
   if re.search(r'isExposeTarget', CardsAS.get(card.model,'')) and getSetting('ExposeTargetsWarn',True):
      if confirm("This card will automatically provide a bonus depending on how many non-exposed derezzed cards you've selected.\
                \nMake sure you've selected all the cards you wish to expose and have peeked at them before taking this action\
                \nSince this is the first time you take this action, you have the opportunity now to abort and select your targets before traying it again.\
              \n\nDo you want to abort this action?\
                \n(This message will not appear again)"):
         setSetting('ExposeTargetsWarn',False)
         return 'ABORT'
      else: setSetting('ExposeTargetsWarn',False) # Whatever happens, we don't show this message again.
   if re.search(r'Reveal&Shuffle', CardsAS.get(card.model,'')) and getSetting('RevealandShuffleWarn',True):
      if confirm("This card will automatically provide a bonus depending on how many cards you selected to reveal (i.e. place on the table) from your hand.\
                \nMake sure you've selected all the cards (of any specific type required) you wish to reveal to the other players\
                \nSince this is the first time you take this action, you have the opportunity now to abort and select your targets before trying it again.\
              \n\nDo you want to abort this action?\
                \n(This message will not appear again)"):
         setSetting('RevealandShuffleWarn',False)
         return 'ABORT'
      else: setSetting('RevealandShuffleWarn',False) # Whatever happens, we don't show this message again.
   if re.search(r'HandTarget', CardsAS.get(card.model,'')) or re.search(r'HandTarget', CardsAA.get(card.model,'')):
      hasTarget = False
      for c in me.hand:
         if c.targetedBy and c.targetedBy == me: hasTarget = True
      if not hasTarget:
         whisper(":::Warning::: This card effect requires that you have one of more cards targeted from your hand. Aborting!")
         return 'ABORT'

def checkNotHardwareConsole (card, manual = False):
   debugNotify(">>> checkNotHardwareConsole(){}".format(extraASDebug())) #Debug
   mute()
   if card.Type != "Hardware" or not re.search(r'Console', getKeywords(card)): return True
   ExistingConsoles = [ c for c in table
         if c.owner == me and c.isFaceUp and re.search(r'Console', getKeywords(c)) ]
   if ((not manual and len(ExistingConsoles) != 0) or (manual and len(ExistingConsoles) != 1)) and not confirm("You already have at least one console in play and you're not normally allowed to install a second. Are you sure you want to install {}?".format(fetchProperty(card, 'name'))): return False
   #else:
      #for HWDeck in ExistingConsoles: trashForFree(HWDeck)
   debugNotify(">>> checkNotHardwareConsole()") #Debug
   return True   
   
def chkTags():
# A function which checks if the runner has any tags and puts a tag marker on the runner ID in that case.
   if ds == 'runner': 
      ID = Identity
      player = me
   else: 
      player = findOpponent()
      ID = getSpecial('Identity',player)
   remoteCall(player,'syncTags',[]) # We send the tag update as a remote call, so as not to get complaints from OCTGN
   if player.Tags: return True      
   else: return False
      
def syncTags():
   mute()
   ID = getSpecial('Identity',me)
   if me.Tags: ID.markers[mdict['Tag']] = me.Tags
   else: ID.markers[mdict['Tag']] = 0

def fetchRunnerPL():
   if ds == 'runner': return me
   else: return findOpponent()
   
def fetchCorpPL():
   if ds == 'corp': return me
   else: return findOpponent()
   
def clearAttachLinks(card):
# This function takes care to discard any attachments of a card that left play
# It also clear the card from the host dictionary, if it was itself attached to another card
# If the card was hosted by a Daemon, it also returns the free MU token to that daemon
   debugNotify(">>> clearAttachLinks()") #Debug
   hostCards = eval(getGlobalVariable('Host Cards'))
   cardAttachementsNR = len([att_id for att_id in hostCards if hostCards[att_id] == card._id])
   if cardAttachementsNR >= 1:
      hostCardSnapshot = dict(hostCards)
      for attachment in hostCardSnapshot:
         if hostCardSnapshot[attachment] == card._id:
            if Card(attachment) in table: intTrashCard(Card(attachment),0,cost = "host removed")
            del hostCards[attachment]
      setGlobalVariable('Host Cards',str(hostCards))
   unlinkHosts(card)
   debugNotify("<<< clearAttachLinks()", 3) #Debug   

def unlinkHosts(card): #Checking if the card is attached to unlink.
   debugNotify(">>> returnHostTokens()") #Debug
   hostCards = eval(getGlobalVariable('Host Cards'))
   if hostCards.has_key(card._id):
      hostCard = Card(hostCards[card._id])
      if (re.search(r'Daemon',getKeywords(hostCard)) or re.search(r'CountsAsDaemon', CardsAS.get(hostCard.model,''))) and hostCard.group == table: 
         if card.markers[mdict['DaemonMU']] and not re.search(r'Daemon',getKeywords(card)):
            hostCard.markers[mdict['DaemonMU']] += card.markers[mdict['DaemonMU']] # If the card was hosted by a Daemon, we return any Daemon MU's used.
         DaemonHosted = findMarker(card,'Daemon Hosted MU')
         if DaemonHosted: # if the card just removed was a daemon hosted by a daemon, then it's going to have a different kind of token.
            hostCard.markers[mdict['DaemonMU']] += card.markers[DaemonHosted] # If the card was hosted by a Daemon, we return any Daemon MU's used.
      customMU = findMarker(card, '{} Hosted'.format(hostCard.name)) 
      debugNotify("customMU = {}".format(customMU))
      if customMU and hostCard.group == table: # If the card has a custom hosting marker (e.g. Dinosaurus)
         hostCard.markers[customMU] += 1 # Then we return the custom hosting marker to its original card to signifiy it's free to host another program.
         card.markers[customMU] -= 1
      del hostCards[card._id] # If the card was an attachment, delete the link
      setGlobalVariable('Host Cards',str(hostCards)) # We need to store again before orgAttachments takes over
      if not re.search(r'Daemon',getKeywords(hostCard)) and not customMU: 
         orgAttachments(hostCard) # Reorganize the attachments if the parent is not a daemon-type card.
   debugNotify("<<< returnHostTokens()", 3) #Debug   
   
def sendToTrash(card, pile = None): # A function which takes care of sending a card to the right trash pile and running the appropriate scripts. Doesn't handle costs.
   debugNotify(">>> sendToTrash()") #Debug   
   if pile == None: pile = card.owner.piles['Heap/Archives(Face-up)'] # I can't pass it as a function variable. OCTGN doesn't like it.
   debugNotify("Target Pile: {}'s {}".format(pile.player,pile.name))
   debugNotify("sendToTrash says previous group = {} and highlight = {}".format(card.group.name,card.highlight))
   if pile.controller != me:
      debugNotify("We don't control the discard pile. Taking it over.")
      grabPileControl(pile)
   if card.controller != me and card.group == table: grabCardControl(card) # We take control of the card in order to avoid errors
   if card.group == table: 
      playTrashSound(card)
      autoscriptOtherPlayers('CardTrashed',card)
   if card.group == table or chkModulator(card, 'runTrashScriptWhileInactive', 'onTrash'): 
      executePlayScripts(card,'TRASH') # We don't want to run automations on simply revealed cards, but some of them will like Director Haas.
   clearAttachLinks(card)
   if chkModulator(card, 'preventTrash', 'onTrash'): # IF the card has the preventTrash modulator, it's not supposed to be trashed.
      if chkModulator(card, 'ifAccessed', 'onTrash') and ds != 'runner': card.moveTo(pile) # Unless it only has that modulator active during runner access. Then when the corp trashes it, it should trash normally.
   else: card.moveTo(pile)
   if pile.player != pile.controller: remoteCall(pile.controller,'passPileControl',[pile,pile.player])
   update()
   debugNotify("<<< sendToTrash()", 3) #Debug   
   
def findAgendaRequirement(card):
   mute()
   debugNotify(">>> findAgendaRequirement() for card: {}".format(card)) #Debug
   AdvanceReq = num(fetchProperty(card, 'Cost'))
   for c in table:
      debugNotify("Checking {} for Agenda cost mods".format(c))
      for autoS in CardsAS.get(c.model,'').split('||'):
         if re.search(r'whileInPlay', autoS) or ((re.search(r'whileScored', autoS) or re.search(r'whileLiberated', autoS)) and c.markers[mdict['Scored']]):
            advanceModRegex = re.search(r'(Increase|Decrease)([0-9])Advancement', autoS)
            if advanceModRegex:
               debugNotify("We have a advanceModRegex")
               if c.isFaceUp and not checkCardRestrictions(gatherCardProperties(card), prepareRestrictions(autoS, 'reduce')): continue 
               debugNotify("advanceModRegex = {} ".format(advanceModRegex.groups()))
               if re.search(r'onlyOnce',autoS) and c.orientation == Rot90: continue # If the card has a once per-turn ability which has been used, ignore it
               if (re.search(r'excludeDummy',autoS) or re.search(r'CreateDummy',autoS)) and c.highlight == DummyColor: continue
               advanceMod = num(advanceModRegex.group(2)) * {'Decrease': -1}.get(advanceModRegex.group(1),1) * per(autoS, c, 0, findTarget(autoS, card = card))
               debugNotify("advanceMod = {}".format(advanceMod))
               AdvanceReq += advanceMod
               if advanceMod: 
                  delayed_whisper("-- {} {}s advance requirement by {}".format(c,advanceModRegex.group(1),advanceMod))
   debugNotify("<<< findAgendaRequirement() with return {}".format(AdvanceReq)) #Debug
   return AdvanceReq
   
def resetAll(): # Clears all the global variables in order to start a new game.
   global Stored_Name, Stored_Type, Stored_Cost, Stored_Keywords, Stored_AutoActions, Stored_AutoScripts
   global installedCount, debugVerbosity, newturn,endofturn, currClicks, turn, autoRezFlags
   debugNotify(">>> resetAll(){}".format(extraASDebug())) #Debug
   mute()
   if len(table) > 0: return # This function should only ever run after game start or reset. We abort in case it's a reconnect.
   me.counters['Credits'].value = 5
   me.counters['Hand Size'].value = 5
   me.counters['Tags'].value = 0
   me.counters['Agenda Points'].value = 0
   me.counters['Bad Publicity'].value = 0
   Stored_Name.clear()
   Stored_Type.clear()
   Stored_Cost.clear()
   Stored_Keywords.clear()
   Stored_AutoActions.clear()
   Stored_AutoScripts.clear()
   installedCount.clear()
   setGlobalVariable('CurrentTraceEffect','None')
   setGlobalVariable('CorpTraceValue','None')
   setGlobalVariable('League','')
   setGlobalVariable('Access','DENIED')
   setGlobalVariable('accessAttempts','0')
   newturn = False 
   endofturn = False
   currClicks = 0
   turn = 0
   del autoRezFlags[:]
   ShowDicts()
   if len(players) > 1: debugVerbosity = -1 # Reset means normal game.
   elif debugVerbosity != -1 and confirm("Reset Debug Verbosity?"): debugVerbosity = -1    
   debugNotify("<<< resetAll()") #Debug   
   
def checkQuickAccess():
   debugNotify(">>> checkQuickAccess()") #Debug   
   #if len(players) == 1: 
      #notify(">>> checkQuickAccess") # Debug
      #notify("## currentGameName = {}".format(currentGameName())) # Debug
   if len(players) == 1 or re.search(r'(\[Quick Access\]|\[QA\]|\[FQA\])',currentGameName()):
      #if len(players) == 1: notify("## About to get QuickAccessInfo Setting") # Debug
      if getSetting('QuickAccessInfo',True):
         information(":::INFO::: You have joined a [Quick Access] game for the first time.\
                 \n\n'[Quick Access]' or '[QA]' games allow the runners to access servers without needing a confirmation from the corp that it's OK to access (i.e. using the OK button or F3)\
                    \nAs such the game expects the runner to make use of the 'Access Imminent' button before pressing F3 to allow the corporation a chance to react.\
                  \n\nThe mode was made to facilitate faster play on behalf of the runner. Please run responsibly.")
         setSetting('QuickAccessInfo',False)
      #if len(players) == 1: notify("## About to switchQuickAccess()") # Debug
      switchQuickAccess(forced = True)
   debugNotify("<<< checkQuickAccess()") #Debug   
      
def clearLeftoverEvents():
   debugNotify(">>> clearLeftoverEvents()") #Debug   
   debugNotify("About to clear all events from table")
   hostCards = eval(getGlobalVariable('Host Cards'))
   for card in table: # We discard all events on the table when the player tries to use another click.
      debugNotify("Processing {}".format(card))
      debugNotify("hostCards eval = {}".format(hostCards))
      if card.isFaceUp and (card.Type == 'Operation' or card.Type == 'Event') and card.highlight != DummyColor and card.highlight != RevealedColor and card.highlight != InactiveColor and not card.markers[mdict['Scored']] and not hostCards.has_key(card._id): # We do not trash "scored" events (e.g. see Notoriety) or cards hosted on others card (e.g. see Oversight AI)
         intTrashCard(card,0,"free") # Clearing all Events and operations for players who keep forgeting to clear them.   
   debugNotify("<<< clearLeftoverEvents()") #Debug   
      
#---------------------------------------------------------------------------
# Card Placement
#---------------------------------------------------------------------------

def placeCard(card, action = 'INSTALL', hostCard = None, type = None, retainPos = False):
   debugNotify(">>> placeCard() with action: {}".format(action)) #Debug
   if not hostCard:
      hostCard = chkHostType(card, seek = 'DemiAutoTargeted')
      if hostCard:
         try:
            if hostCard == 'ABORT': 
               delayed_whisper(":::ERROR::: No Valid Host Targeted! Aborting Placement.") # We can pass a host from a previous function (e.g. see Personal Workshop)
               return 'ABORT'
         except: pass
   if hostCard: hostMe(card,hostCard)
   else:
      global installedCount
      if not type: 
         type = fetchProperty(card, 'Type') # We can pass the type of card as a varialbe. This way we can pass one card as another.
         if action != 'INSTALL' and type == 'Agenda':
            if ds == 'corp': type = 'scoredAgenda'
            else: type = 'liberatedAgenda'
         if action == 'INSTALL' and re.search(r'Console',card.Keywords): type = 'Console'
      if action == 'INSTALL' and type in CorporationCardTypes: CfaceDown = True
      else: CfaceDown = False
      debugNotify("Setting installedCount. Type is: {}, CfaceDown: {}".format(type, str(CfaceDown)), 3) #Debug
      if installedCount.get(type,None) == None: installedCount[type] = 0
      else: installedCount[type] += 1
      debugNotify("installedCount is: {}. Setting loops...".format(installedCount[type]), 2) #Debug
      loopsNR = installedCount[type] / (place[type][3]) 
      loopback = place[type][3] * loopsNR 
      if loopsNR and place[type][3] != 1: offset = 15 * (loopsNR % 3) # This means that in one loop the offset is going to be 0 and in another 15.
      else: offset = 0
      debugNotify("installedCount[type] is: {}.\nLoopsNR is: {}.\nLoopback is: {}\nOffset is: {}".format(installedCount[type],offset, loopback, offset), 3) #Debug
      #if not retainPos: card.moveToTable(((place[type][0] + (((cwidth(card,0) + place[type][2]) * (installedCount[type] - loopback)) + offset) * place[type][4]) * flipBoard) + flipModX,(place[type][1] * flipBoard) + flipModY,CfaceDown) 
      if not retainPos: placeOnTable(card,((place[type][0] + (((cwidth(card,0) + place[type][2]) * (installedCount[type] - loopback)) + offset) * place[type][4]) * flipBoard) + flipModX,(place[type][1] * flipBoard) + flipModY,CfaceDown) 
      # To explain the above, we place the card at: Its original location
      #                                             + the width of the card
      #                                             + a predefined distance from each other times the number of other cards of the same type
      #                                             + the special offset in case we've done one or more loops
      #                                             And all of the above, multiplied by +1/-1 (place[type][4]) in order to direct the cards towards the left or the right
      #                                             And finally, the Y axis is always the same in ANR.
      if type == 'Agenda' or type == 'Upgrade' or type == 'Asset': # camouflage until I create function to install them on specific Server, via targeting.
         installedCount['Agenda'] = installedCount[type]
         installedCount['Asset'] = installedCount[type]
         installedCount['Upgrade'] = installedCount[type]
      if not card.isFaceUp: 
         debugNotify("Peeking() at placeCard()")
         card.peek() # Added in octgn 3.0.5.47
   debugNotify("<<< placeCard()", 3) #Debug

def hostMe(card,hostCard):
   debugNotify(">>> hostMe()") #Debug
   unlinkHosts(card) # First we make sure we clear any previous hosting and return any markers to their right place.
   hostCards = eval(getGlobalVariable('Host Cards'))
   hostCards[card._id] = hostCard._id
   setGlobalVariable('Host Cards',str(hostCards))
   orgAttachments(hostCard)
   debugNotify("<<< hostMe()") #Debug

def orgAttachments(card):
# This function takes all the cards attached to the current card and re-places them so that they are all visible
# xAlg, yAlg are the algorithsm which decide how the card is placed relative to its host and the other hosted cards. They are always multiplied by attNR
   debugNotify(">>> orgAttachments()") #Debug
   attNR = 1
   debugNotify(" Card Name : {}".format(card.name), 4)
   if specialHostPlacementAlgs.has_key(card.name):
      debugNotify("Found specialHostPlacementAlgs", 3)
      xAlg = specialHostPlacementAlgs[card.name][0]
      yAlg = specialHostPlacementAlgs[card.name][1]
      debugNotify("Found Special Placement Algs. xAlg = {}, yAlg = {}".format(xAlg,yAlg), 2)
   else: 
      debugNotify("No specialHostPlacementAlgs", 3)
      xAlg = 0 # The Default placement on the X axis, is to place the attachments at the same X as their parent
      if card.controller == me: sideOffset = playerside # If it's our card, we need to assign it towards our side
      else: sideOffset = playerside * -1 # Otherwise we assign it towards the opponent's side
      yAlg =  -(cwidth(card) / 4 * sideOffset) # Defaults
   hostCards = eval(getGlobalVariable('Host Cards'))
   cardAttachements = [Card(att_id) for att_id in hostCards if hostCards[att_id] == card._id]
   x,y = card.position
   for attachment in cardAttachements:
      debugNotify("Checking group of {}".format(attachment))
      debugNotify("group name = {}".format(attachment.group.name))
      if attachment.owner.getGlobalVariable('ds') == 'corp' and pileName(attachment.group) in ['R&D','Face-up Archives','HQ'] and attachment.Type != 'Operation':
         debugNotify("card is faceDown")
         cFaceDown = True
      else: 
         debugNotify("attachment.isFaceUp = {}".format(attachment.isFaceUp))
         cFaceDown = False # If we're moving corp cards to the table, we generally move them face down
      placeOnTable(attachment,x + ((xAlg * attNR) * flipBoard), y + ((yAlg * attNR) * flipBoard),cFaceDown)
      if cFaceDown and attachment.owner == me: 
         debugNotify("Peeking() at orgAttachments()")
         attachment.peek() # If we moved our own card facedown to the table, we peek at it.
      if fetchProperty(attachment, 'Type') == 'ICE': attachment.orientation = Rot90 # If we just moved an ICE to the table, we make sure it's turned sideways.
      indexSet(attachment,len(cardAttachements) - attNR) # This whole thing has become unnecessary complicated because sendToBack() does not work reliably
      debugNotify("{} index = {}".format(attachment,attachment.getIndex), 4) # Debug
      attNR += 1
      debugNotify("Moving {}, Iter = {}".format(attachment,attNR), 4)
   indexSet(card,'front') # Because things don't work as they should :(
   if debugVerbosity >= 4: # Checking Final Indices
      for attachment in cardAttachements: notify("{} index = {}".format(attachment,attachment.getIndex)) # Debug
   debugNotify("<<< orgAttachments()", 3) #Debug      

def possess(daemonCard, programCard, silent = False, force = False):
   debugNotify(">>> possess(){}".format(extraASDebug())) #Debug
   #This function takes as arguments 2 cards. A Daemon and a program requiring MUs, then assigns the program to the Daemon, restoring the used MUs to the player.
   hostType = re.search(r'Placement:([A-Za-z1-9:_ -]+)', fetchProperty(programCard, 'AutoScripts'))
   if hostType and not re.search(r'Daemon',hostType.group(1)):
      delayed_whisper("This card cannot be hosted on a Daemon as it needs a special host type")
      return 'ABORT'
   count = num(programCard.properties["Requirement"])
   debugNotify("Looking for custom hosting marker", 2)
   customHostMarker = findMarker(daemonCard, '{} Hosted'.format(daemonCard.name)) # We check if the card has a custom hosting marker which we use when the hosting is forced
   debugNotify("Custom hosting marker: {}".format(customHostMarker), 2)
   hostCards = eval(getGlobalVariable('Host Cards'))   
   if not force and (count > daemonCard.markers[mdict['DaemonMU']] and not customHostMarker):
      delayed_whisper(":::ERROR::: {} has already hosted the maximum amount of programs it can hold.".format(daemonCard))
      return 'ABORT'
   elif force and not customHostMarker: # .get didn't work on card.markers[] :-(
      delayed_whisper(":::ERROR::: {} has already hosted the maximum amount of programs it can hold.".format(daemonCard))
      return 'ABORT'
   elif hostCards.has_key(programCard._id):
      delayed_whisper(":::ERROR::: {} is already hosted in {}.".format(programCard,Card(hostCards[programCard._id])))
      return 'ABORT'
   else:
      debugNotify("We have a valid daemon host", 2) #Debug
      hostCards[programCard._id] = daemonCard._id
      setGlobalVariable('Host Cards',str(hostCards))
      if not customHostMarker:
         daemonCard.markers[mdict['DaemonMU']] -= count
         if re.search(r'Daemon',fetchProperty(programCard, 'Keywords')): # If it's a daemon, we do not want to give it the same daemon token, as that's going to be reused for other programs and we do not want that.
            TokensX('Put{}Daemon Hosted MU-isSilent'.format(count), '', programCard)
         else: programCard.markers[mdict['DaemonMU']] += count
      else:
         daemonCard.markers[customHostMarker] -= 1 # If this a forced host, the host should have a special counter on top of it...
         programCard.markers[customHostMarker] += 1 # ...that we move to the hosted program to signify it's hosted
         Autoscripts = CardsAS.get(daemonCard.model,'').split('||')
         debugNotify("Daemon Autoscripts found = {}".format(Autoscripts))
         for autoS in Autoscripts:
            markersRegex = re.search(r'onHost:(.*)',autoS)            
            if markersRegex:
               debugNotify("markersRegex groups = {}".format(markersRegex.groups()))
               for autoS in markersRegex.group(1).split('$$'):
                  redirect(autoS, programCard, announceText = None, notificationType = 'Quick', X = 0)
                  #TokensX(markersRegex.group(1),'',programCard)
            else: debugNotify("No onHost scripts found in {}".format(autoS))
      if customHostMarker and customHostMarker[0] == 'Scheherazade Hosted': pass
      else: programCard.owner.MU += count # We return the MUs the card would be otherwise using.
      if not silent: notify("{} installs {} into {}".format(me,programCard,daemonCard))
   debugNotify("<<< possess()", 3) #Debug   
   
def chkDmgSpecialEffects(dmgType, count):
# This function checks for special card effects on the table that hijack normal damage effects and do something extra or differently
# At the moment it's used for the two Chronos Protocol IDs.
   debugNotify(">>> chkDmgSpecialEffects()") #Debug
   usedDMG = 0
   replaceDMGAnnounce = False
   for card in table:
      if card.controller == me and card.model == 'bc0f047c-01b1-427f-a439-d451eda05022' and dmgType == 'Net' and re.search(r'running',getGlobalVariable('status')):
         if confirm("Do you want to pay 2 credits to use {}'s ability to turn this {} Net damage into Brain Damage?\n\n(Unfortunately, OCTGN is not aware where {} is placed. If he's not in the right server, just press No.".format(card.name,count,card.name)):
            if payCost(2, 'not free') != "ABORT":
               usedDMG = count # After this, we don't want any autoscripts to be doing any more damage
               InflictX('Inflict1BrainDamage-onOpponent', '', card)
               notify("--> {} activates {} to turn all their Net Damage into 1 Brain damage".format(me,card))
               replaceDMGAnnounce = True
      if card.name == 'Chronos Protocol':
         if card.Faction == 'Jinteki' and dmgType == 'Net' and oncePerTurn(card, silent = True, act = 'automatic') != 'ABORT':
            if card.controller == me: JintekiCP(card,count)
            else: remoteCall(card.controller,'JintekiCP',[card,count]) # It needs to be the Jinteki player who selects the card.
            usedDMG = count # After this, we don't want any autoscripts to be doing any more damage
         if card.Faction == 'Haas-Bioroid' and dmgType == 'Brain':
            remoteCall(fetchRunnerPL(),'HasbroCP',[card,count])
            usedDMG = count # After this, we don't want any autoscripts to be doing any more damage
   debugNotify("<<< chkDmgSpecialEffects() with return {}".format(usedDMG)) #Debug
   return (usedDMG,replaceDMGAnnounce)

def JintekiCP(card,count): # Function which takes care that the Jinteki Chronos Protocol ID properly asks the Jinteki player for the choice before doing more damage.
   debugNotify(">>> JintekiCP()") #Debug
   mute()
   targetPL = findOpponent()
   if not len(targetPL.hand): remoteCall(targetPL, 'intdamageDiscard',[count]) # If their hand is empty we need to flatline them
   else:
      grabPileControl(targetPL.hand)
      #targetPL.hand.setVisibility('all')
      #update()
      handList = [c for c in targetPL.hand]
      for c in handList: c.moveToTable(0,0)
      for c in handList: loopChk(c,'Type') # Make sure we can see each card's details
      choice = SingleChoice("Choose a card to trash for your first Net Damage", makeChoiceListfromCardList(handList))
      if choice != None: # If the player cancels the choice for some reason, abort the rest of the damage.
         sendToTrash(handList[choice])
         notify("=> {} uses {}'s ability to trash {} with the first net damage".format(me,card,handList[choice]))
      for c in handList: c.moveTo(targetPL.hand)
      passPileControl(targetPL.hand,targetPL)
      #remoteCall(targetPL,'grabVisibility',[targetPL.hand])
      if choice != None: 
         if count - 1: remoteCall(targetPL, 'intdamageDiscard',[count - 1]) # If there's any leftover damage, we inflict it now.
   debugNotify("<<< JintekiCP()") #Debug
   
def HasbroCP(card,count): # A Function called remotely for the runner player which takes care to wipe all cards of the same type as the one trashed from the game.
   debugNotify(">>> HasbroCP()") #Debug
   mute()
   for iter in range(count):
      exiledC = me.hand.random()
      exiledC.moveTo(me.piles['Removed from Game'])
      notify("--DMG: {} is removed from the game due to {}!".format(exiledC,card))
      #me.piles['R&D/Stack'].setVisibility('me')
      for c in me.piles['R&D/Stack']: c.peek()
      for c in me.piles['R&D/Stack']:
         loopChk(c,'Name')
         #notify("### {} c.model == {}".format(c.Name,c.model))
         if c.Name == exiledC.Name: 
            c.moveTo(me.piles['Removed from Game'])
            notify("=> Extra {} scrubbed from Stack".format(exiledC))
      #me.piles['R&D/Stack'].setVisibility('none')      
      shuffle(me.piles['R&D/Stack'])
      for c in me.piles['Heap/Archives(Face-up)']:
         if c.model == exiledC.model: 
            c.moveTo(me.piles['Removed from Game'])      
            notify("=> Extra {} scrubbed from Heap".format(exiledC))
      for c in table:
         if c.model == exiledC.model and not c.markers[mdict['Scored']] and not c.markers[mdict['ScorePenalty']] and c.highlight != DummyColor: # Scored cards like Notoriety are not removed, nor are resident effects.
            exileCard(c, True)
            notify("=> Extra {} scrubbed from the table".format(exiledC))
      for c in me.hand:
         if c.model == exiledC.model: 
            c.moveTo(me.piles['Removed from Game'])      
            notify("=> Extra {} scrubbed from Grip".format(exiledC))
   debugNotify("<<< HasbroCP()") #Debug
#------------------------------------------------------------------------------
# Switches
#------------------------------------------------------------------------------

def switchAutomation(type,command = 'Off'):
   debugNotify(">>> switchAutomation(){}".format(extraASDebug())) #Debug
   global Automations
   if (Automations[type] and command == 'Off') or (not Automations[type] and command == 'Announce'):
      notify ("--> {}'s {} automations are OFF.".format(me,type))
      if command != 'Announce': Automations[type] = False
   else:
      notify ("--> {}'s {} automations are ON.".format(me,type))
      if command != 'Announce': Automations[type] = True
   
def switchPlayAutomation(group,x=0,y=0):
   debugNotify(">>> switchPlayAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Play, Score and Rez')
   
def switchStartEndAutomation(group,x=0,y=0):
   debugNotify(">>> switchStartEndAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Start/End-of-Turn')

def switchDMGAutomation(group,x=0,y=0):
   debugNotify(">>> switchDMGAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Damage')

def switchPreventDMGAutomation(group,x=0,y=0):
   debugNotify(">>> switchDMGAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Damage Prevention')

def switchTriggersAutomation(group,x=0,y=0):
   debugNotify(">>> switchTriggersAutomation(){}".format(extraASDebug())) #Debug
   switchAutomation('Triggers')
   
def switchWinForms(group,x=0,y=0):
   debugNotify(">>> switchWinForms(){}".format(extraASDebug())) #Debug
   switchAutomation('WinForms')
   
def switchUniCode(group,x=0,y=0,command = 'Off'):
   debugNotify(">>> switchUniCode(){}".format(extraASDebug())) #Debug
   global UniCode
   if UniCode and command != 'On':
      whisper("Credits and Clicks will now be displayed as normal ASCII.".format(me))
      UniCode = False
   else:
      whisper("Credits and Clicks will now be displayed as Unicode.".format(me))
      UniCode = True

def switchSounds(group,x=0,y=0):
   debugNotify(">>> switchSounds(){}".format(extraASDebug())) #Debug
   if getSetting('Sounds', True):
      setSetting('Sounds', False)
      whisper("Sound effects have been switched off")
   else:
      setSetting('Sounds', True)
      whisper("Sound effects have been switched on")
        
def switchQuickAccess(group = table,x=0,y=0,forced = False, remoted = False):
   #if len(players) == 1: notify(">>> switchQuickAccess()") # Debug
   debugNotify(">>> switchQuickAccess(){}".format(extraASDebug())) #Debug
   global askedQA
   QAgame = re.search(r'(\[Quick Access\]|\[QA\]|\[FQA\])',currentGameName()) # If the game has [Quick Access] in the title, we don't allow to turn QA off.
   if not forced and QAgame:
      whisper(":::ERROR::: Sorry, you cannot cancel Quick Access in a [Quick Access] game.")
   elif not forced and ds == None:
      whisper(":::ERROR::: Please load a deck first.")
   else:
      QA = getGlobalVariable('Quick Access')
      if ds == 'corp' or forced or len(players) == 1: # Checking that this is not a single-player game to avoid an infinite loop
         if QA == 'False':
            if remoted and not confirm("The runner would like to turn Quick Access on (i.e. not requiring corp confirmation before accessing a server). Do you accept?"): 
               notify(":::INFO::: {} rejected the request to activate Quick Access!".format(me))
            elif re.search(r'\[FQA\]',currentGameName()): 
               setGlobalVariable('Quick Access','Fucking')
               if QAgame: barNotifyAll("#009900",":::INFO::: This is a [Fucking Quick Access] Game!") 
            else: 
               setGlobalVariable('Quick Access','True')
               if QAgame: barNotifyAll("#009900",":::INFO::: This is a [Quick Access] Game!") 
               else: barNotifyAll("#009900",":::INFO::: Quick Access has been activated!")
         else: 
            if remoted and not confirm("The runner would like to turn Quick Access off. Accept?"): 
               notify(":::INFO::: {} rejected the request to disable Quick Access!".format(me))
               return
            setGlobalVariable('Quick Access','False')
            barNotifyAll("#009900",":::INFO::: Quick Access has been disabled!")
      else:
         if askedQA: whisper(":::ERROR::: You've already asked the corp to enable QA once already. Please don't spam them.")
         else:
            whisper(":::INFO::: Asking for corporation confirmation to activate Quick Access...")
            targetPL = findOpponent()
            if targetPL != me: remoteCall(targetPL,'remoteAskQA',[]) # Checking player just in case we end up in an infinite loop.
            askedQA = True # The runner can only ask once for QA in order not to spam the corp
            
def remoteAskQA():
   mute()
   switchQuickAccess(remoted = True)
   
def addGroupVisibility(group,player):
   mute()
   if group.controller != me: 
      remoteCall(group.controller,'addGroupVisibility',[group,player])
   else:    
      debugNotify("{} giving {} visibility to {}. Current Controller == {}".format(me,group.name,player,group.controller))
      group.addViewer(player)
   update()
   debugNotify("<<< addGroupVisibility. {} Viewers == {}".format(group,[pl.name for pl in group.viewers]))
   
def delGroupVisibility(group,player):
   mute()
   if group.controller != me: remoteCall(group.controller,'delGroupVisibility',[group,player])
   else: group.removeViewer(player)
   update()
   debugNotify("<<< delGroupVisibility. {} Viewers == {}".format(group,[pl.name for pl in group.viewers]))

def modGroupVisibility(group,setting):
   mute()
   if group.controller != me: 
      remoteCall(group.controller,'modGroupVisibility',[group,setting])
   else:    
      debugNotify("{} setting {} visibility to {}. Current Controller == {}".format(me,group.name,setting,group.controller))
      group.setVisibility(setting)
   update()
   debugNotify("<<< modGroupVisibility. {} group.visibility == {}".format(group,group.visibility))

   
#------------------------------------------------------------------------------
# Help functions
#------------------------------------------------------------------------------

def HELP_TurnStructure(group,x=0,y=0):
   table.create('8b4f0c4d-4e4a-4d7f-890d-936ef37c8600', x, y, 1)
def HELP_CorpActions(group,x=0,y=0):
   table.create('881ccfad-0da9-4ca8-82e6-29c524f15a7c', x, y, 1)
def HELP_RunnerActions(group,x=0,y=0):
   table.create('6b3c394a-411f-4a1c-b529-9a8772a96db9', x, y, 1)
def HELP_RunAnatomy(group,x=0,y=0):
   table.create('db60308d-0d0e-4891-9954-7c600a7389e1', x, y, 1)
def HELP_RunStructure(group,x=0,y=0):
   table.create('51c3a293-3923-49ee-8c6f-b8c41aaba5f3', x, y, 1)


#------------------------------------------------------------------------------
# Button functions
#------------------------------------------------------------------------------

def BUTTON_Access(group = None,x=0,y=0):
   global AccessBtnNextChoice # Using a global var to avoid running the slow random function
   mute()
   if num(getGlobalVariable('accessAttempts')) == 0:
      AccessMsgs = ["--- Alert: Unauthorized Access Imminent!", 
                    "--- Alert: Runner entry detected!",
                    "--- Alert: Firewalls breached!",
                    "--- Alert: Intrusion in progress!"]
      #AccessTXT = AccessMsgs[rnd(0,len(AccessMsgs) - 1)]
      AccessTXT = AccessMsgs[AccessBtnNextChoice]
      AccessBtnNextChoice += 1
      if AccessBtnNextChoice >= len(AccessMsgs): AccessBtnNextChoice = 0
      notify(AccessTXT + "\n-- {} is about to gain access. Corporate React?".format(me))
      setGlobalVariable('accessAttempts',str(num(getGlobalVariable('accessAttempts')) + 1))  # The runner using the Button counts for an access Attempt. After 3 of them, the runner can bypass an unresponsive corp.
      playButtonSound('Access')
   else: runSuccess()

def BUTTON_NoRez(group = None,x=0,y=0):  
   notify("--- {} does not rez approached ICE".format(me))
   playButtonSound('NoRez')

def BUTTON_OK(group = None,x=0,y=0):
   notify("--- {} has no further reactions.".format(me))
   if re.search(r'running',getGlobalVariable('status')) and ds == 'corp': 
      setGlobalVariable('Access','GRANTED')
      notify("--- ACCESS GRANTED ---")
   playButtonSound('OK')

def BUTTON_Wait(group = None,x=0,y=0):  
   notify("--- Wait! {} wants to react.".format(me))
   playButtonSound('Wait')
#------------------------------------------------------------------------------
#  Online Functions
#------------------------------------------------------------------------------

def versionCheck():
   debugNotify(">>> versionCheck()") #Debug
   global startupMsg
   me.setGlobalVariable('gameVersion',gameVersion)
   if not startupMsg: MOTD() # If we didn't give out any other message , we give out the MOTD instead.
   startupMsg = True
   ### Below code Not needed anymore in 3.1.x
   # if not startupMsg:
      # (url, code) = webRead('https://raw.github.com/db0/Android-Netrunner-OCTGN/master/current_version.txt')
      # debugNotify("url:{}, code: {}".format(url,code), 2) #Debug
      # if code != 200 or not url:
         # whisper(":::WARNING::: Cannot check version at the moment.")
         # return
      # detailsplit = url.split('||')
      # currentVers = detailsplit[0].split('.')
      # installedVers = gameVersion.split('.')
      # debugNotify("Finished version split. About to check", 2) #Debug
      # if len(installedVers) < 3:
         # whisper("Your game definition does not follow the correct version conventions. It is most likely outdated or modified from its official release.")
         # startupMsg = True
      # elif (num(currentVers[0]) > num(installedVers[0]) or 
           # (num(currentVers[0]) == num(installedVers[0]) and num(currentVers[1]) > num(installedVers[1])) or 
           # (num(currentVers[0]) == num(installedVers[0]) and num(currentVers[1]) == num(installedVers[1]) and num(currentVers[2]) > num(installedVers[2]))):
         # notify("{}'s game definition ({}) is out-of-date!".format(me, gameVersion))
         # if confirm("There is a new game definition available!\nYour version: {}.\nCurrent version: {}\n{}\
                     # {}\
                 # \n\nDo you want to be redirected to download the latest version?.\
                   # \n(You'll have to download the game definition, any patch for the current version and the markers if they're newer than what you have installed)\
                     # ".format(gameVersion, detailsplit[0],detailsplit[2],detailsplit[1])):
            # openUrl('http://octgn.gamersjudgement.com/viewtopic.php?f=52&t=494')
         # startupMsg = True
      # debugNotify("Finished version check. Seeing if I should MOTD.", 2) #Debug
   debugNotify("<<< versionCheck()", 3) #Debug
      
      
def MOTD():
   debugNotify(">>> MOTD()") #Debug
   #if me.name == 'db0' or me.name == 'dbzer0': return #I can't be bollocksed
   (MOTDurl, MOTDcode) = webRead('https://raw.github.com/db0/Android-Netrunner-OCTGN/master/MOTD.txt',3000)
   if MOTDcode != 200 or not MOTDurl:
      whisper(":::WARNING::: Cannot fetch MOTD info at the moment.")
      return
   if getSetting('MOTD', 'UNSET') != MOTDurl: # If we've already shown the player the MOTD already, we don't do it again.
      setSetting('MOTD', MOTDurl) # We store the current MOTD so that we can check next time if it's the same.
      (DYKurl, DYKcode) = webRead('https://raw.github.com/db0/Android-Netrunner-OCTGN/master/DidYouKnow.txt',3000)
      if DYKcode !=200 or not DYKurl:
         whisper(":::WARNING::: Cannot fetch DYK info at the moment.")
         return
      DYKlist = DYKurl.split('||')
      DYKrnd = rnd(0,len(DYKlist)-1)
      while MOTDdisplay(MOTDurl,DYKlist[DYKrnd]) == 'MORE': 
         MOTDurl = '' # We don't want to spam the MOTD for the further notifications
         DYKrnd += 1
         if DYKrnd == len(DYKlist): DYKrnd = 0
   debugNotify("<<< MOTD()", 3) #Debug
   
def MOTDdisplay(MOTD,DYK):
   debugNotify(">>> MOTDdisplay()") #Debug
   if re.search(r'http',MOTD): # If the MOTD has a link, then we do not sho DYKs, so that they have a chance to follow the URL
      MOTDweb = MOTD.split('&&')      
      if confirm("{}".format(MOTDweb[0])): openUrl(MOTDweb[1].strip())
   elif re.search(r'http',DYK):
      DYKweb = DYK.split('&&')
      if confirm("{}\
              \n\nDid You Know?:\
                \n------------------\
                \n{}".format(MOTD,DYKweb[0])):
         openUrl(DYKweb[1].strip())
   elif confirm("{}\
              \n\nDid You Know?:\
                \n-------------------\
                \n{}\
                \n-------------------\
              \n\nWould you like to see the next tip?".format(MOTD,DYK)): return 'MORE'
   return 'STOP'

def initGame(): # A function which prepares the game for online submition
   debugNotify(">>> initGame()") #Debug
   if getGlobalVariable('gameGUID') != 'None': return #If we've already grabbed a GUID, then just use that.
   (gameInit, initCode) = webRead('http://84.205.248.92/slaghund/init.slag',3000)
   if initCode != 200:
      #whisper("Cannot grab GameGUID at the moment!") # Maybe no need to inform players yet.
      return
   debugNotify("{}".format(gameInit), 2) #Debug
   GUIDregex = re.search(r'([0-9a-f-]{36}).*?',gameInit)
   if GUIDregex: setGlobalVariable('gameGUID',GUIDregex.group(1))
   else: setGlobalVariable('gameGUID','None') #If for some reason the page does not return a propert GUID, we won't record this game.
   setGlobalVariable('gameEnded','False')
   debugNotify("<<< initGame()", 3) #Debug
   
def reportGame(result = 'AgendaVictory'): # This submits the game results online.
   delayed_whisper("Please wait. Submitting Game Stats...")     
   debugNotify(">>> reportGame()") #Debug
   GUID = getGlobalVariable('gameGUID')
   if GUID == 'None' and debugVerbosity < 0: return # If we don't have a GUID, we can't submit. But if we're debugging, we go through.
   gameEnded = getGlobalVariable('gameEnded')
   if gameEnded == 'True':
     if not confirm("Your game already seems to have finished once before. Do you want to change the results to '{}' for {}?".format(result,me.name)): return
   playGameEndSound(result)
   PLAYER = me.name # Seeting some variables for readability in the URL
   id = getSpecial('Identity',me)
   IDENTITY = id.Subtitle.replace(',','').replace('.','').replace('#','').replace('@','').replace('#','')
   RESULT = result
   GNAME = currentGameName()
   LEAGUE = getGlobalVariable('League')
   if result == 'Flatlined' or result == 'Conceded' or result == 'DeckDefeat' or result == 'AgendaDefeat': WIN = 0
   else: WIN = 1
   SCORE = me.counters['Agenda Points'].value
   deckStats = eval(me.getGlobalVariable('Deck Stats'))
   debugNotify("Retrieved deckStats ", 2) #Debug
   debugNotify("deckStats = {}".format(deckStats), 2) #Debug
   INFLUENCE = deckStats[0]
   CARDSNR = deckStats[1]
   AGENDASNR = deckStats[2]
   TURNS = turn
   VERSION = gameVersion
   debugNotify("About to report player results online.", 2) #Debug
   if (turn < 1 or len(players) == 1) and debugVerbosity < 1:
      notify(":::ATTENTION:::Game stats submit aborted due to number of players ( less than 2 ) or turns played (less than 1)")
      return # You can never win before the first turn is finished and we don't want to submit stats when there's only one player.
   if debugVerbosity < 1: # We only submit stats if we're not in debug mode
      (reportTXT, reportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME),10000)
   else: 
      if confirm('Report URL: http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}\n\nSubmit?'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME)):
         (reportTXT, reportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME),10000)
         notify('Report URL: http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}\n\nSubmit?'.format(GUID,PLAYER,IDENTITY,RESULT,SCORE,INFLUENCE,TURNS,CARDSNR,AGENDASNR,VERSION,WIN,LEAGUE,GNAME))
   try:
      if reportTXT != "Updating result...Ok!" and debugVerbosity >=0: whisper("Failed to submit match results") 
   except: pass
   # The victorious player also reports for their enemy
   enemyPL = ofwhom('-ofOpponent')
   ENEMY = enemyPL.name
   enemyIdent = getSpecial('Identity',enemyPL)
   E_IDENTITY = enemyIdent.Subtitle.replace(',','').replace('.','').replace('#','').replace('@','').replace('#','')
   debugNotify("Enemy Identity Name: {}".format(E_IDENTITY), 2) #Debug
   if result == 'FlatlineVictory': 
      E_RESULT = 'Flatlined'
      E_WIN = 0
   elif result == 'Flatlined': 
      E_RESULT = 'FlatlineVictory'
      E_WIN = 1
   elif result == 'Conceded': 
      E_RESULT = 'ConcedeVictory'
      E_WIN = 1  
   elif result == 'DeckDefeat': 
      E_RESULT = 'DeckVictory'
      E_WIN = 1  
   elif result == 'AgendaVictory': 
      E_RESULT = 'AgendaDefeat'
      E_WIN = 0
   elif result == 'AgendaDefeat': 
      E_RESULT = 'AgendaVictory'
      E_WIN = 1
   else: 
      E_RESULT = 'Unknown'
      E_WIN = 0
   E_SCORE = enemyPL.counters['Agenda Points'].value
   debugNotify("About to retrieve E_deckStats", 2) #Debug
   E_deckStats = eval(enemyPL.getGlobalVariable('Deck Stats'))
   debugNotify("E_deckStats = {}".format(E_deckStats), 2) #Debug
   E_INFLUENCE = E_deckStats[0]
   E_CARDSNR = E_deckStats[1]
   E_AGENDASNR = E_deckStats[2]
   if ds == 'corp': E_TURNS = turn - 1 # If we're a corp, the opponent has played one less turn than we have.
   else: E_TURNS = turn # If we're the runner, the opponent has played one more turn than we have.
   debugNotify("About to report enemy results online.", 2) #Debug
   if debugVerbosity < 1: # We only submit stats if we're not debugging
      (EreportTXT, EreportCode) = webRead('http://84.205.248.92/slaghund/game.slag?g={}&u={}&id={}&r={}&s={}&i={}&t={}&cnr={}&anr={}&v={}&w={}&lid={}&gname={}'.format(GUID,ENEMY,E_IDENTITY,E_RESULT,E_SCORE,E_INFLUENCE,E_TURNS,E_CARDSNR,E_AGENDASNR,VERSION,E_WIN,LEAGUE,GNAME),10000)
   setGlobalVariable('gameEnded','True')
   notify("Thanks for playing. Please submit any bugs or feature requests on github.\n-- https://github.com/db0/Android-Netrunner-OCTGN/issues")
   notify("   \n =+= Please consider supporting the development of this plugin\n =+= http://www.patreon.com/db0\n")
   debugNotify("<<< reportGame()", 3) #Debug

def setleague(group = table, x=0,y=0, manual = True):
   debugNotify(">>> setleague()") #Debug
   mute()
   league = getGlobalVariable('League')
   origLeague = league
   debugNotify("global var = {}".format(league))
   if league == '': # If there is no league set, we attempt to find out the league name from the game name
      for leagueTag in knownLeagues:
         if re.search(r'{}'.format(leagueTag),currentGameName()): league = leagueTag
   debugNotify("League after automatic check: {}".format(league))
   if manual:
      if not confirm("Do you want to set this match to count for an active league\n(Pressing 'No' will unset this match from all leagues)"): league = ''
      else:
         choice = SingleChoice('Please Select One the Active Leagues', [knownLeagues[leagueTag] for leagueTag in knownLeagues])
         if choice != None: league = [leagueTag for leagueTag in knownLeagues][choice]
   debugNotify("League after manual check: {}".format(league))
   debugNotify("Comparing with origLeague: {}".format(origLeague))
   if origLeague != league:
      if manual: 
         if league ==  '': notify("{} sets this match as casual".format(me))
         else: notify("{} sets this match to count for the {}".format(me,knownLeagues[league]))
      elif league != '': notify(":::LEAGUE::: This match will be recorded for the the {}. (press Ctrl+Alt+L to unset)".format(knownLeagues[league]))
   elif manual: 
         if league == '': delayed_whisper("Game is already casual.")
         else: delayed_whisper("Game already counts for the {}".format(me,knownLeagues[league]))
   setGlobalVariable('League',league)
   debugNotify(">>> setleague() with league: {}".format(league)) #Debug
         
def fetchCardScripts(group = table, x=0, y=0, silent = False): # Creates 2 dictionaries with all scripts for all cards stored, based on a web URL or the local version if that doesn't exist.
   debugNotify(">>> fetchCardScripts()") #Debug
   global CardsAA, CardsAS # Global dictionaries holding Card AutoActions and Card AutoScripts for all cards.
   if not silent: whisper("+++ Fetching fresh scripts. Please Wait...")
   if (len(players) > 1 or debugVerbosity == 0) and me.name != 'dbzer0' and not silent: # I put my debug account to always use local scripts.
      try: (ScriptsDownload, code) = webRead('https://raw.github.com/db0/Android-Netrunner-OCTGN/master/o8g/Scripts/CardScripts.py',5000)
      except: 
         debugNotify("Timeout Error when trying to download scripts", 0)
         code = ScriptsDownload = None
   else: # If we have only one player, we assume it's a debug game and load scripts from local to save time.
      debugNotify("Skipping Scripts Download for faster debug", 0)
      code = 0
      ScriptsDownload = None
   debugNotify("code:{}, text: {}".format(code, ScriptsDownload), 4) #Debug
   if code != 200 or not ScriptsDownload or (ScriptsDownload and not re.search(r'ANR CARD SCRIPTS', ScriptsDownload)) or debugVerbosity >= 0: 
      whisper(":::WARNING::: Cannot download card scripts at the moment. Will use locally stored ones.")
      Split_Main = ScriptsLocal.split('=====') # Split_Main is separating the file description from the rest of the code
   else: 
      #WHAT THE FUUUUUCK? Why does it gives me a "value cannot be null" when it doesn't even come into this path with a broken connection?!
      #WHY DOES IT WORK IF I COMMENT THE NEXT LINE. THIS MAKES NO SENSE AAAARGH!
      #ScriptsLocal = ScriptsDownload #If we found the scripts online, then we use those for our scripts
      Split_Main = ScriptsDownload.split('=====')
   if debugVerbosity >= 5:  #Debug
      notify(Split_Main[1])
      notify('=====')
   Split_Cards = Split_Main[1].split('.....') # Split Cards is making a list of a different cards
   if debugVerbosity >= 5: #Debug
      notify(Split_Cards[0]) 
      notify('.....')
   for Full_Card_String in Split_Cards:
      if re.search(r'ENDSCRIPTS',Full_Card_String): break # If we have this string in the Card Details, it means we have no more scripts to load.
      Split_Details = Full_Card_String.split('-----') # Split Details is splitting the card name from its scripts
      if debugVerbosity >= 5:  #Debug
         notify(Split_Details[0])
         notify('-----')
      # A split from the Full_Card_String always should result in a list with 2 entries.
      debugNotify(Split_Details[0].strip(), 2) # If it's the card name, notify us of it.
      Split_Scripts = Split_Details[2].split('+++++') # List item [1] always holds the two scripts. AutoScripts and AutoActions.
      CardsAS[Split_Details[1].strip()] = Split_Scripts[0].strip()
      CardsAA[Split_Details[1].strip()] = Split_Scripts[1].strip()
   if turn > 0: whisper("+++ All card scripts refreshed!")
   if debugVerbosity >= 4: # Debug
      notify("CardsAS Dict:\n{}".format(str(CardsAS)))
      notify("CardsAA Dict:\n{}".format(str(CardsAA))) 
   debugNotify("<<< fetchCardScripts()", 3) #Debug

def concede(group=table,x=0,y=0):
   mute()
   if confirm("Are you sure you want to concede this game?"): 
      reportGame('Conceded')
      notify("{} has conceded the game".format(me))
   else: 
      notify("{} was about to concede the game, but thought better of it...".format(me))
#------------------------------------------------------------------------------
# Debugging
#------------------------------------------------------------------------------
   
def TrialError(group, x=0, y=0): # Debugging
   global ds, debugVerbosity
   mute()
   #test()
   delayed_whisper("## Checking Debug Verbosity")
   if debugVerbosity >=0: 
      if debugVerbosity == 0: 
         debugVerbosity = 1
      elif debugVerbosity == 1: debugVerbosity = 2
      elif debugVerbosity == 2: debugVerbosity = 3
      elif debugVerbosity == 3: debugVerbosity = 4
      else: debugVerbosity = 0
      whisper("Debug verbosity is now: {}".format(debugVerbosity))
      return
   delayed_whisper("## Checking my Name")
   if me.name == 'db0' or me.name == 'dbzer0' or me.name == 'null': 
      debugVerbosity = 0
      fetchCardScripts()
   delayed_whisper("## Checking players array size")
   if not (len(players) == 1 or debugVerbosity >= 0): 
      whisper("This function is only for development purposes")
      return
   ######## Testing Corner ########
   #testHandRandom()
   ###### End Testing Corner ######
   delayed_whisper("## Defining Test Cards")
   testcards = [
                "bc0f047c-01b1-427f-a439-d451eda04061", 
                "bc0f047c-01b1-427f-a439-d451eda04062",
                # "bc0f047c-01b1-427f-a439-d451eda04063",
                # "bc0f047c-01b1-427f-a439-d451eda04064",
                # "bc0f047c-01b1-427f-a439-d451eda04065",
                #"bc0f047c-01b1-427f-a439-d451eda04066",
                #"bc0f047c-01b1-427f-a439-d451eda04067",
                #"bc0f047c-01b1-427f-a439-d451eda04068",
                "bc0f047c-01b1-427f-a439-d451eda04069",
                #"bc0f047c-01b1-427f-a439-d451eda04070",
                #"bc0f047c-01b1-427f-a439-d451eda04071",
                #"bc0f047c-01b1-427f-a439-d451eda04072",
                "bc0f047c-01b1-427f-a439-d451eda04073",
                #"bc0f047c-01b1-427f-a439-d451eda04074",
                #"bc0f047c-01b1-427f-a439-d451eda04075",
                #"bc0f047c-01b1-427f-a439-d451eda04076",
                #"bc0f047c-01b1-427f-a439-d451eda04077",
                #"bc0f047c-01b1-427f-a439-d451eda04078",
                "bc0f047c-01b1-427f-a439-d451eda04079",
                "bc0f047c-01b1-427f-a439-d451eda04058",
                "bc0f047c-01b1-427f-a439-d451eda04080"
                ] 
   if not ds: 
      if confirm("corp?"): ds = "corp"
      else: ds = "runner"
   me.setGlobalVariable('ds', ds) 
   me.counters['Credits'].value = 50
   me.counters['Hand Size'].value = 5
   me.counters['Tags'].value = 1
   me.counters['Agenda Points'].value = 0
   me.counters['Bad Publicity'].value = 10
   me.Clicks = 15
   notify("Variables Reset") #Debug   
   if not playerside:  # If we've already run this command once, don't recreate the cards.
      notify("Playerside not chosen yet. Doing now") #Debug   
      chooseSide()
      notify("About to create starting cards.") #Debug   
      createStartingCards()
   notify("<<< TrialError()") #Debug
   # if debugVerbosity >= 0 and confirm("Spawn Test Cards?"):
      # for idx in range(len(testcards)):
         # test = table.create(testcards[idx], (70 * idx) - 650, 0, 1, True)
         # storeProperties(test)
         # if test.Type == 'ICE' or test.Type == 'Agenda' or test.Type == 'Asset': test.isFaceUp = False

def debugChangeSides(group=table,x=0,y=0):
   global ds
   if debugVerbosity >=0:
      delayed_whisper("## Changing side")
      if ds == "corp": 
         notify("Runner now")
         ds = "runner"
         me.setGlobalVariable('ds','runner')
      else: 
         ds = "corp"
         me.setGlobalVariable('ds','corp')
         notify("Corp Now")
   else: whisper("Sorry, development purposes only")


def ShowDicts():
   if debugVerbosity < 0: return
   notify("Stored_Names:\n {}".format(str(Stored_Name)))
   notify("Stored_Types:\n {}".format(str(Stored_Type)))
   notify("Stored_Costs:\n {}".format(str(Stored_Cost)))
   notify("Stored_Keywords: {}".format(str(Stored_Keywords)))
   debugNotify("Stored_AA: {}".format(str(Stored_AutoActions)), 4)
   debugNotify("Stored_AS: {}".format(str(Stored_AutoScripts)), 4)
   notify("installedCounts: {}".format(str(installedCount)))

def DebugCard(card, x=0, y=0):
   whisper("Stored Card Properties\
          \n----------------------\
          \nStored Name: {}\
          \nPrinted Name: {}\
          \nStored Type: {}\
          \nPrinted Type: {}\
          \nStored Keywords: {}\
          \nPrinted Keywords: {}\
          \nCost: {}\
          \nCard ID: {}\
          \n----------------------\
          ".format(Stored_Name.get(card._id,'NULL'), card.Name, Stored_Type.get(card._id,'NULL'), card.Type, Stored_Keywords.get(card._id,'NULL'), card.Keywords, Stored_Cost.get(card._id,'NULL'),card._id))
   if debugVerbosity >= 4: 
      #notify("Stored_AS: {}".format(str(Stored_AutoScripts)))
      notify("Downloaded AA: {}".format(str(CardsAA)))
      notify("Card's AA: {}".format(CardsAA.get(card.model,'???')))
   storeProperties(card, True)
   if Stored_Type.get(card._id,'?') != 'ICE': card.orientation = Rot0

def addC(cardModel,count = 1): # Quick function to add custom cards on the table depending on their GUID
# Use the following to spawn a card
# remoteCall(me,'addC',['<cardGUID>'])
   card = table.create(cardModel, 0,0, count, True)
   storeProperties(card)
   if card.Type == 'ICE' or card.Type == 'Agenda' or card.Type == 'Asset': card.isFaceUp = False   
   
def extraASDebug(Autoscript = None):
   if Autoscript and debugVerbosity >= 3: return ". Autoscript:{}".format(Autoscript)
   else: return ''

def ShowPos(group, x=0,y=0):
   if debugVerbosity >= 1: 
      notify('x={}, y={}'.format(x,y))
      
def ShowPosC(card, x=0,y=0):
   if debugVerbosity >= 1: 
      notify(">>> ShowPosC(){}".format(extraASDebug())) #Debug
      x,y = card.position
      notify('card x={}, y={}'.format(x,y))      

   
def testHandRandom():
   if confirm("Run Hand random alg?"):
      randomsList = []
      notify("About to fill list")
      for iter in range(len(me.hand)): randomsList.append(0)
      notify("about to iter 100")
      for i in range(500):
         c = me.hand.random()
         for iter in range(len(me.hand)):            
            if c == me.hand[iter]: 
               randomsList[iter] += 1
               break
      notify("randomsList: {}".format(randomsList))

########NEW FILE########
__FILENAME__ = sounds
    # Python Scripts for the Android:Netrunner LCG definition for OCTGN
    # Copyright (C) 2012  Konstantine Thoukydides

    # This python script is free software: you can redistribute it and/or modify
    # it under the terms of the GNU General Public License as published by
    # the Free Software Foundation, either version 3 of the License, or
    # (at your option) any later version.

    # This program is distributed in the hope that it will be useful,
    # but WITHOUT ANY WARRANTY; without even the implied warranty of
    # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    # GNU General Public License for more details.

    # You should have received a copy of the GNU General Public License
    # along with this script.  If not, see <http://www.gnu.org/licenses/>.

import re

def playInstallSound(card, remoted = False):
   debugNotify(">>> playInstallSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if not remoted: remoteCall(findOpponent(),'playInstallSound',[card,True]) # Attempt to fix lag
   else: 
      if re.search(r'Daemon',getKeywords(card)): playSound('Install-Daemon')
      elif re.search(r'Chip',getKeywords(card)): playSound('Install-Chip')
      elif re.search(r'Gear',getKeywords(card)): playSound('Install-Gear')
      elif re.search(r'Console',getKeywords(card)): playSound('Install-Console')
      elif re.search(r'Virus',getKeywords(card)): playSound('Install-Virus')
      elif fetchProperty(card, 'Type') == 'Program': playSound('Install-Program')
      elif fetchProperty(card, 'Type') == 'Hardware': playSound('Install-Hardware')
      elif fetchProperty(card, 'Type') == 'Resource': playSound('Install-Resource')
      elif fetchProperty(card, 'Type') == 'ICE': playSound('Install-ICE')
      elif fetchProperty(card, 'Type') == 'Asset' or fetchProperty(card, 'Type') == 'Upgrade' or fetchProperty(card, 'Type') == 'Agenda': playSound('Install-Root')

def playEvOpSound(card):
   debugNotify(">>> playEvOpSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if fetchProperty(card, 'Type') == 'Event' or fetchProperty(card, 'Type') == 'Operation':
      if card.name == 'Stimhack': playSound('Play-Stimhack')
      elif card.name == 'Push Your Luck': playSound('Play-Push_Your_Luck')
      elif re.search(r'Transaction',getKeywords(card)): playSound('Play-Transaction')
      elif re.search(r'Job',getKeywords(card)): playSound('Play-Job')

def playRezSound(card):
   debugNotify(">>> playRezSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if fetchProperty(card, 'Name') == 'Archer': playSound('Rez-Archer')
   elif re.search(r'Sentry',getKeywords(card)): playSound('Rez-Sentry')
   elif re.search(r'Barrier',getKeywords(card)): playSound('Rez-Barrier')
   elif re.search(r'Code Gate',getKeywords(card)): playSound('Rez-Code_Gate')
   elif re.search(r'Trap',getKeywords(card)): playSound('Rez-Trap')
   elif fetchProperty(card, 'Type') == 'Upgrade': playSound('Rez-Upgrade')
   elif fetchProperty(card, 'Type') == 'Asset': playSound('Rez-Asset')
    
def playDerezSound(card):
   debugNotify(">>> playDerezSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if fetchProperty(card, 'Type') == 'ICE': playSound('Derez-ICE')
    
def playUseSound(card):
   debugNotify(">>> playUseSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   debugNotify("Keywords: {}".format(getKeywords(card)))
   if fetchProperty(card, 'Type') == 'ICE':
      if card.name == 'Pop-up Window':  playSound('Use-ICE_Pop-Up_Window')
      if card.name == 'Archer':  playSound('Use-ICE_Archer')
   elif re.search(r'Icebreaker',getKeywords(card)):  
      if re.search(r'AI',getKeywords(card)): playSound('Use-ICEbreaker_AI')
      elif re.search(r'Killer',getKeywords(card)): playSound('Use-ICEbreaker_Killer')
      elif re.search(r'Decoder',getKeywords(card)): playSound('Use-ICEbreaker_Decoder')
      elif re.search(r'Fracter',getKeywords(card)): playSound('Use-ICEbreaker_Fracter')
    
def playTurnStartSound():
   debugNotify(">>> playTurnStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if ds == 'runner': playSound('Runner-Start')
   else: playSound('Corp-Start')

def playTurnEndSound():
   debugNotify(">>> playTurnEndSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if ds == 'runner': playSound('Runner-End')
   else: playSound('Corp-End')

def playTrashSound(card):
   debugNotify(">>> playTrashSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if fetchProperty(card, 'Type') == 'Upgrade' or fetchProperty(card, 'Type') == 'Asset': 
      if card.controller != me: playSound('Trash-Opposing_Asset')
   if fetchProperty(card, 'Type') == 'Hardware': 
      if card.controller != me: playSound('Trash-Opposing_Hardware')
   if fetchProperty(card, 'Type') == 'Program': 
      if card.controller != me: playSound('Trash-Opposing_Program')
      else: playSound('Trash-Program')
   if fetchProperty(card, 'Type') == 'ICE' or (card.orientation == Rot90 and not card.isFaceUp): 
      if card.controller != me: playSound('Trash-Opposing_ICE')
      else: playSound('Trash-ICE')
   if fetchProperty(card, 'Type') == 'Resource' or (card.orientation == Rot90 and not card.isFaceUp): 
      if card.controller != me: playSound('Trash-Opposing_Resource')
      
def playButtonSound(buttonType):
   debugNotify(">>> playButtonSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if buttonType == 'Access': playSound('BTN-Access_Imminent')
   elif buttonType == 'NoRez': playSound('BTN-No_Rez')
   elif buttonType == 'Wait': playSound('BTN-Wait')  

def playPsiStartSound():
   debugNotify(">>> playTraceStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Psi-Start')
      
def playTraceStartSound():
   debugNotify(">>> playTraceStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Trace-Start')
      
def playTraceAvoidedSound():
   debugNotify(">>> playTraceAvoidedSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if rnd(1,10) == 10: playSound('Trace-Avoided_Zoidberg')
   else: playSound('Trace-Avoided')
   
def playTraceLostSound():
   debugNotify(">>> playTraceLostSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Trace-Lost')
   
def playRemoveTagSound():
   debugNotify(">>> playRemoveTagSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Tag-Remove')
   
def playScoreAgendaSound(card):
   debugNotify(">>> playScoreAgendaSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if ds == 'corp':
      if card.name == 'Breaking News': playSound('Score-Breaking_News')
      else: playSound('Score-Agenda')
   else: playSound('Liberate-Agenda')
   
def playDMGSound(DMGType):
   debugNotify(">>> playDMGSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   mute()
   if DMGType == 'Brain':
      if rnd(1,10) == 5: playSound('DMG-Brains')
      else: playSound('DMG-Brain')
   elif DMGType == 'Net': playSound('DMG-Net')
   elif DMGType == 'Meat':
      if rnd(1,10) == 10: playSound('DMG-Meat_Whilhelm')
      else: playSound('DMG-Meat{}'.format(rnd(1,4)))

def playRunStartSound():
   debugNotify(">>> playRunStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Run-Start')
   
def playRunUnsuccesfulSound():
   debugNotify(">>> playRunStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Run-Unsuccessful')
   
def playCorpEndSound():
   debugNotify(">>> playRunStartSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   #playSound('Run-End') # Disabled for now as it merges with other sounds usually.
   
def playAccessSound(ServerType):
   debugNotify(">>> playAccessSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   mute()
   if ServerType == 'HQ': playSound('Access-HQ')
   elif ServerType == 'R&D': playSound('Access-RD')
   elif ServerType == 'Archives': playSound('Access-Archives')
   
def playVirusPurgeSound():
   debugNotify(">>> playVirusPurgeSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound('Purge-Viruses')
   
def playClickCreditSound(remoted = False):
   debugNotify(">>> playClickCreditSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if remoted: playSound('Credit-Click')
   else: remoteCall(findOpponent(),'playClickCreditSound',[True]) # Attempt to fix lag
   
def playClickDrawSound(remoted = False):
   debugNotify(">>> playClickDrawSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if remoted: playSound('Draw-Card')
   else: remoteCall(findOpponent(),'playClickDrawSound',[True]) # Attempt to fix lag
   
def playDiscardHandCardSound():
   debugNotify(">>> playDiscardHandCardSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if ds == 'runner': playSound('Discard-Card_Runner') 
   else: playSound('Discard-Card_Corp')
   
def playGameEndSound(type = 'AgendaVictory'):
   debugNotify(">>> playGameEndSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   if type == 'Flatlined' or type == 'FlatlineVictory': playSound('Runner-Flatline') 
   
def playSpecialSound(soundName = 'Special-Push_Your_Luck-Fail'):
   debugNotify(">>> playSpecialSound()") #Debug
   if getSetting('Sounds', True) == 'False': return
   playSound(soundName) 

########NEW FILE########
__FILENAME__ = generic_test
#!/usr/bin/python

"""Test Suite for Android:Netrunner module of OCTGN

These tests can be run from the root directory of module with:
python -m scripts.tests.generic_test

There are variables in other modules initialized in OCTGN and thus unavailable
during unit testing. The RUNNING_TEST_SUITE environment variable is set here
and used in other modules to initialize those missing vars.

I suspect there might be another way to handle this, like initializing them
in main() of the test suite, but the current method is sufficient to run the
tests while ensuring these mock objects do not leak when OCTGN is running.
"""
import unittest
try:
    import os
    os.environ['RUNNING_TEST_SUITE'] = 'TRUE'
except ImportError:
    pass

from scripts import generic

class NumOrderTests(unittest.TestCase):

    def test_one_digit(self):
        """Test conversion of single digit ints to ordinals."""
        # These are correct conversions and should pass
        self.assertEqual('1st', generic.numOrder(0))
        self.assertEqual('2nd', generic.numOrder(1))
        self.assertEqual('3rd', generic.numOrder(2))
        self.assertEqual('4th', generic.numOrder(3))

        # These are incorrect conversions and should fail
        self.assertNotEqual('1st', generic.numOrder(1))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = w0nk0
__author__ = 'w0nk0'


def HELP_AddStartEndButtons(group,x=0,y=0): ##TODO w0nk0: implement respective cards -->execute="goToSot",execute="goToEndTurn"
    """
    ##TODO: create GUIDs 5f7ff64b-1df3-4ce8-9153-7d4370fc32b3 / cfc45a19-54ab-46c3-9e51-9b4e01b1bed0
    pngs to /sets-markers-cards
    create cards with ability
    make cards trigger start/end run
    """
    if ds == 'runner':
       table.create('5f7ff64b-1df3-4ce8-9153-7d4370fc32b3', (500 * flipBoard) + flipModX,(-290 * flipBoard) + flipModY, 1) #Start turn
       table.create('cfc45a19-54ab-46c3-9e51-9b4e01b1bed0', (560 * flipBoard) + flipModX, (-290 * flipBoard) + flipModY, 1) #End turn
    else:
       table.create('5f7ff64b-1df3-4ce8-9153-7d4370fc32b3', (500 * flipBoard) + flipModX,(260 * flipBoard) + flipModY, 1) #Start turn
       table.create('cfc45a19-54ab-46c3-9e51-9b4e01b1bed0', (560 * flipBoard) + flipModX, (260 * flipBoard) + flipModY, 1) #End turn
    #table.create('1ce4f50d-2604-4afe-8d8c-551ce0623d70', 0, 0, 1) # Access Granted


########NEW FILE########
