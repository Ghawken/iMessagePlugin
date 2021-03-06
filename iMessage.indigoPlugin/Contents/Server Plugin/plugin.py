#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
iMessage
First draft

"""
import logging
import datetime
import time as t
import os
import sys
import shutil
from ghpu import GitHubPluginUpdater
import sqlite3
import applescript


try:
    import indigo
except:
    pass


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)


        self.startingUp = True
        self.pluginIsInitializing = True
        self.pluginIsShuttingDown = False
        self.prefsUpdated = False
        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Initializing New Plugin Session "))
        self.logger.info(u"{0:<30} {1}".format("Plugin name:", pluginDisplayName))
        self.logger.info(u"{0:<30} {1}".format("Plugin version:", pluginVersion))
        self.logger.info(u"{0:<30} {1}".format("Plugin ID:", pluginId))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:<30} {1}".format("Python Directory:", sys.prefix.replace('\n', '')))
        self.logger.info(u"{0:=^130}".format(""))

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"showDebugLevel"])
        except:
            self.logLevel = logging.INFO

        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.triggers = {}
        self.pluginVersion = pluginVersion
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.showBuddies = self.pluginPrefs.get('showBuddies', False)
        self.debugextra = self.pluginPrefs.get('debugextra', False)
        self.debugtriggers = self.pluginPrefs.get('debugtriggers', False)
        self.debugexceptions = self.pluginPrefs.get('debugexceptions', False)
        self.openStore = self.pluginPrefs.get('openStore', False)

        self.resetLastCommand = t.time()+60
        self.next_update_check = t.time()
        self.lastCommandsent = dict()
        self.lastBuddy =''
        self.awaitingConfirmation = []    # buddy handle within here if waiting a reply yes or no
#  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'

        self.messages = []

        self.allowedBuddies = self.pluginPrefs.get('allowedBuddies','')
        self.prefServerTimeout = int(self.pluginPrefs.get('configMenuServerTimeout', "15"))
        self.configUpdaterInterval = self.pluginPrefs.get('configUpdaterInterval', 24)
        self.configUpdaterForceUpdate = self.pluginPrefs.get('configUpdaterForceUpdate', False)

        self.pluginIsInitializing = False


    def __del__(self):
        if self.debugextra:
            self.debugLog(u"__del__ method called.")
        indigo.PluginBase.__del__(self)

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if self.debugextra:
            self.debugLog(u"closedPrefsConfigUi() method called.")

        if userCancelled:
            self.debugLog(u"User prefs dialog cancelled.")

        if not userCancelled:

            self.debugLog(u"User prefs saved.")
            #self.debug = valuesDict.get('showDebugInfo', False)
            self.debugextra = valuesDict.get('debugextra', False)
            self.debugexceptions = valuesDict.get('debugexceptions', False)
            self.debugtriggers = valuesDict.get('debugtriggers', False)
            self.prefsUpdated = True
            self.updateFrequency = float(valuesDict.get('updateFrequency', "24")) * 60.0 * 60.0

            try:
                self.logLevel = int(valuesDict[u"showDebugLevel"])
            except:
                self.logLevel = logging.INFO

            self.indigo_log_handler.setLevel(self.logLevel)
            self.showBuddies = valuesDict.get('showBuddies', False)
            self.allowedBuddies = valuesDict.get('allowedBuddies', '')
            self.openStore = valuesDict.get('openStore', False)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.logger.debug(u"User prefs saved.")
            self.logger.debug(u"Debugging on (Level: {0})".format(self.logLevel))

        return True

    # Start 'em up.
    def deviceStartComm(self, dev):
        if self.debugextra:
            self.debugLog(u"deviceStartComm() method called.")


    # Shut 'em down.
    def deviceStopComm(self, dev):
        if self.debugextra:
            self.debugLog(u"deviceStopComm() method called.")
        indigo.server.log(u"Stopping device: " + dev.name)

    ###

    def buddyListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        if self.debugextra:
            self.debugLog(u"buddyListGenerator() method called.")
        buddyList = []
        if self.allowedBuddies is not None and self.allowedBuddies !='':
            myBuddies = self.allowedBuddies.split(',')
            if len(myBuddies) >0:
                for buddy in myBuddies:
                    buddyList.append(tuple((buddy, buddy)))
                    if self.debugextra:
                        self.debugLog(u"Adding allowed Buddy:"+unicode(buddy)+u' to list.')
            else:
                buddyList = [('option1', 'No Allowed Buddies Setup PluginConfig'),('option2','Please Setup in Plugin Config')]
        else:
            buddyList = [('option1', 'No Allowed Buddies Setup PluginConfig'),
                         ('option2', 'Please Setup in Plugin Config')]
        if self.debugextra:
            self.debugLog(u"Full BuddyList equals:"+unicode(buddyList))
        return buddyList
    ###  Update ghpu Routines.

    def checkForUpdates(self):

        updateavailable = self.updater.getLatestVersion()
        if updateavailable and self.openStore:
            self.logger.info(u'iMessage: Update Checking.  Update is Available.  Taking you to plugin Store. ')
            self.sleep(2)
            self.pluginstoreUpdate()
        elif updateavailable and not self.openStore:
            self.errorLog(u'iMessage: Update Checking.  Update is Available.  Please check Store for details/download.')

    def updatePlugin(self):
        self.updater.update()

    def pluginstoreUpdate(self):
        iurl = 'http://www.indigodomo.com/pluginstore/195/'
        self.browserOpen(iurl)

    #####

    def runConcurrentThread(self):

        try:
            self.connectsql()
            #x =0
            while True:
                #x=x+1
                self.sleep(5)

                messages = self.sql_fetchmessages()
                if len(messages)>0:
                    self.parsemessages(messages)
                if len(self.awaitingConfirmation)>0:
                    self.checkTimeout()
                if self.lastCommandsent:
                    if t.time() > self.resetLastCommand:
                        if self.debugextra:
                            self.logger.debug(u'Within RunConcurrent Thread: Resetting self.lastcommandsent')
                        self.lastCommandsent.clear()
                        self.resetLastCommand = t.time()+120
                        if self.debugextra:
                            self.logger.debug(u'Now Self.lastcommandsent :'+unicode(self.lastCommandsent))
                if self.updateFrequency > 0:
                    if t.time() > self.next_update_check:
                        try:
                            self.checkForUpdates()
                            self.next_update_check = t.time() + self.updateFrequency
                        except:
                            self.logger.debug(
                                u'Error checking for update - ? No Internet connection.  Checking again in 24 hours')
                            self.next_update_check = self.next_update_check + 86400
                            if self.debugexceptions:
                                self.logger.exception(u'Exception:')
        except self.StopThread:
            self.debugLog(u'Restarting/or error. Stopping  thread.')
            self.closesql()
            pass

#### sql lite connection to iMessage database

    def connectsql(self):
        if self.debugextra:
            self.debugLog(u"connectsql() method called.")
        try:
            ## update to multiple users
            self.backupfilename = os.path.expanduser('~/Documents/Indigo-iMsgBackup/')
            diriMsgdb = os.path.expanduser('~/Library/Messages/')
            if os.path.exists(self.backupfilename)==False:
                #if os.path.exists(self.backupfilename)==False:
                os.mkdir(self.backupfilename)
                self.logger.info(u'Backing up Current iMsg Database Directory to :' + unicode(self.backupfilename))
                src_files = os.listdir(diriMsgdb)
                for file_name in src_files:
                    full_filename = os.path.join(diriMsgdb,file_name)
                    if (os.path.isfile(full_filename)):
                        shutil.copy(full_filename, self.backupfilename)
                        self.logger.debug(u'Backed up file:'+full_filename)

            self.filename = os.path.expanduser('~/Library/Messages/chat.db')
            if self.debugextra:
                self.logger.debug(u'ConnectSQL: Filename location for iMsg chat.db equals:'+unicode(self.filename))
            self.connection = sqlite3.connect(self.filename)
            if self.debugextra:
                self.debugLog(u"Connect to Database Successful.")
            self.logger.info(u'Connection to iMsg Database Successful.')
        except:
            self.logger.error(u'Problem connecting to iMessage database....')
            self.logger.error(u'Most likely you have not allowed IndigoApp and IndigoServer Full Disk Access')
            self.logger.error(u'Please see instructions.  This only needs to be done once.')
            self.logger.error(u'Once done please restart the plugin.')
            if self.debugextra:
                self.logger.exception(u'and here is the Exception (self.debugexceptions is on:)')
            self.sleep(600)
            return

    def closesql(self):
        if self.debugextra:
            self.debugLog(u"connectsql() method called.")
        try:
            self.connection.close()
        except:
            if self.debugexceptions:
                self.logger.exception(u'Exception in closeSql:')
            if self.debugextra:
                self.logger.debug(u'Error in Close Sql - Probably was not connected')

    def sql_fetchmessages(self):
       # if self.debugextra:
       #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()

        sqlcommand = '''
           SELECT handle.id, message.text 
             FROM message INNER JOIN handle 
             ON message.handle_id = handle.ROWID 
             WHERE is_from_me=0 AND 
             datetime(message.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-10 seconds', 'localtime')
             ORDER BY message.date ASC;      
           '''

        # ## Still doesn't help with group chat
        # sqlcommand = '''
        #     SELECT handle.id, message.text , chat.guid
        #       FROM message
        #       INNER JOIN handle
        #         ON message.handle_id = handle.ROWID
        #       INNER JOIN chat
        #         ON handle.ROWID = chat.ROWID
        #       WHERE is_from_me=0 AND
        #       datetime(message.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-10 seconds', 'localtime');
        #     '''
        cursor.execute(sqlcommand)
        result = cursor.fetchall()


        if not result:  # list is empty return empty dict
            return dict()
        else:
            if self.debugextra:
                self.logger.debug(u'sql_fetchmessages: Not empty return:' + unicode(result))
            newmessages = [item for sublist in result for item in sublist]
            if self.debugextra:
                self.logger.debug(u'Flatten Messages first:')
                self.logger.debug(unicode(newmessages))
                self.logger.debug(u'Then convert to Dict:')
            newmessagesdict = dict(zip(*[iter(newmessages)] * 2))

            if self.debugextra:
                self.logger.debug(unicode('Coverted Dict:'))
                self.logger.debug(unicode(newmessagesdict))
            return newmessagesdict

#####

########
#    Applescript communication to iMsg via applescript import
########

    def as_sendmessage(self, imsgUser, imsgMessage):
        if self.debugextra:
            self.debugLog(u"as_sendmessage() method called.")
            self.logger.debug(u'Sending iMsg:'+unicode(imsgMessage)+u' to Buddy/User:'+unicode(imsgUser))

        ascript_string = '''
        set sendThis to "''' + imsgMessage+'''"  
        tell application "Messages"
	        set myid to get id of first service
	        set theBuddy to buddy "''' + imsgUser + '''" of service id myid
	        send sendThis to theBuddy
        end tell
        '''
        my_ascript_from_string = applescript.AppleScript(source=ascript_string)
        reply = my_ascript_from_string.run()
        if self.debugextra:
            self.logger.debug(u'AppleScript Reply:'+unicode(reply))

    def as_sendgroupmessage(self, imsgUser, imsgMessage):
        if self.debugextra:
            self.debugLog(u"as_sendGroupmessage() method called.")
            self.logger.debug(u'Sending GroupiMsg:' + unicode(imsgMessage) + u' to GroupID:' + unicode(imsgUser))

        ascript_string = '''
                set sendThis to "''' + imsgMessage + '''"  
                set myid to "''' + imsgUser + '''" 
                tell application "Messages"
        	        set myid to get id of first service
        	        set theBuddy to a reference to text chat id myid 
        	        send sendThis to theBuddy
                end tell
                '''
        my_ascript_from_string = applescript.AppleScript(source=ascript_string)
        reply = my_ascript_from_string.run()
        if self.debugextra:
            self.logger.debug(unicode(reply))


    def as_sendpicture(self, imsgUser, imsgFile):
        if self.debugextra:
            self.debugLog(u"as_sendpicture() method called.")
            self.logger.debug(u'Sending Picture/File:' + unicode(imsgFile) + u' to Buddy/User:' + unicode(imsgUser))

        ascript_string = '''
        set theAttachment to POSIX file "''' + imsgFile + '''"  
        tell application "Messages"
            set myid to get id of first service
            set theBuddy to buddy "''' + imsgUser + '''" of service id myid
            send theAttachment to theBuddy
        end tell
        '''
        my_ascript_from_string = applescript.AppleScript(source=ascript_string)
        reply = my_ascript_from_string.run()
        if self.debugextra:
            self.logger.debug(unicode(reply))
########
# Parse Messages
########

    def checkTimeout(self):
        if self.debugextra:
            self.debugLog(u"checkTimeout method called.")
        for sublist in self.awaitingConfirmation:
            if t.time() > int(sublist[2]):
                self.logger.debug(u'Timeout for '+unicode(sublist)+' occured.  Removing and sending timeout msg')
                self.as_sendmessage(sublist[0],'Timeout waiting for reply')
                self.awaitingConfirmation = [ subl for subl in self.awaitingConfirmation if subl[0]!=sublist[0] ]
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation modified now equals:' + unicode(self.awaitingConfirmation))
                #make new nested list removing the most recent buddy handle
                #  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'
        return


    def parsemessages(self, messages):

        buddiescurrent = ()

        if self.debugextra:
            self.debugLog(u"parse messages() method called.")
            self.logger.debug(u'Message Received: Message Info:'+unicode(messages))

        # if self.lastcommand == messages:
        #     if self.debugextra:
        #         self.debugLog(u"Checked lastcommand SAME MESSAGE parsing aborted.")
        #     return

        if self.allowedBuddies is None or self.allowedBuddies=='':
            self.logger.info(u'Message Received but Allowed Buddies Empty. Please set in Plugin Config')
            return

        for key,val in messages.items():
            if self.debugextra:
                self.logger.debug(u'Checking messages:  Received: Buddy :'+unicode(key)+ ' Received Message:'+unicode(val))
            if key not in buddiescurrent:
                buddiescurrent = buddiescurrent + (key,)
                if self.debugextra:
                    self.logger.debug(u'Buddies Current now equals:'+unicode(buddiescurrent))

        if self.showBuddies:
            self.logger.error(u'iMessage Received from Buddy(s):  Buddy(s) Handle Below:')
            for buddies in buddiescurrent:
                self.logger.error(unicode(buddies))

        for key, val in messages.items():
            if key in self.allowedBuddies:
                if self.debugextra:
                    self.logger.debug(u'Passed against allowed Buddies: ' + unicode(messages))
                    self.logger.debug(u'Allowed Buddies Equal:'+unicode(self.allowedBuddies))
                    self.logger.debug(u'Received Buddy equals:'+unicode(key))
            else:
                if self.debugextra:
                    self.logger.debug(u'Message Received - but buddyhandle not allowed; Handled received equals:'+unicode(key))
                    self.logger.debug(u'Allowed Buddies Equal:' + unicode(self.allowedBuddies))
                    self.logger.debug(u'Deleting this message, continuing with others parsing')
                messages.pop(key, None)

        #self.lastcommand = messages
        #self.lastBuddy = messages[0]
        for key,value in messages.items():
            for sublist in self.awaitingConfirmation:
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation:'+unicode(self.awaitingConfirmation))
                if sublist[0] == key:
                # Buddle has a outstanding confirmation awaited.
                # check against valid replies
                    if self.checkanswer(key,value,sublist):
                        if self.debugextra:
                            self.logger.debug(u'Confirmation received so deleting this message, ending.  No trigger check on this message.')
                            self.logger.debug(u'messages equals:'+unicode(messages))
                        messages.pop(key, None)
                        self.logger.debug(u'Message part deleted now equals:'+unicode(messages))

        if self.debugextra:
            self.logger.debug(u'SELF.lastcommand PRIOR equals:' + unicode(self.lastCommandsent))

        for keymsg,valmsg in messages.items():
            # now check last message and don't act if the same
            # check if list nested or not
            if self.lastCommandsent:  # check not empty list
                for keylast,vallast in self.lastCommandsent.items():
                    if self.debugextra:
                        self.logger.debug(u'Checking last commands sent:'+unicode(keylast)+' : '+unicode(vallast) )
                        self.logger.debug(u'LastCommandsent Key:'+unicode(keylast)+u' Messages Key:'+unicode(keymsg))
                    if keymsg==keylast:
                        if self.debugextra:
                            self.logger.debug(u'Buddy last command found: Buddy:'+unicode(keylast)+u' and last message:'+unicode(valmsg))
                        if valmsg==vallast:
                            if self.debugextra:
                                self.logger.debug(u'Same Message found.  This repeated message will be ignored. Message ignored: '+unicode(valmsg))
                            messages.pop(keymsg, None)
                            if self.debugextra:
                                self.logger.debug(u'Same Message found.  New Messages equals:'+unicode(messages))
        # last message
        for key,val in messages.items():
            self.lastCommandsent[key]=val
            if self.debugextra:
                self.logger.debug(u'Updated lastCommandsent:' + unicode(self.lastCommandsent))

        # if only one flatten the nest list as was causing issues
        # need now to deal with nested sometimes, list others - above

        #self.lastCommandsent = [subl for subl in self.lastCommandsent if subl[0] != v[0]]

        if self.debugextra:
            self.logger.debug(u'self.lastcommand equals:' + unicode(self.lastCommandsent))

        for key,val in messages.items():
            self.lastBuddy = key
            self.triggerCheck('', 'commandReceived', val.lower() )
            self.resetLastCommand = t.time()+120
            messages.pop(key, None)
            if self.debugextra:
                self.logger.debug(
                    u'Command Sent received so deleting this message, ending.  No trigger check on this message.')
                self.logger.debug(u'messages equals:' + unicode(messages))


        return
#######
    #
    def checkanswer(self, buddyHandle, message, sublist):
        if self.debugextra:
            self.debugLog(u"checkanswer() method called.")

        valid = {"yes": True, "y": True, "ye": True, 'yeah':True, 'ok':True,  "no": False, "n": False, 'nope':False, 'never':False}

        if message.lower() in valid:
            if valid[message.lower()]:
                # if True run actions
                if self.debugextra:
                    self.debugLog(u"checkanswer() Valid Reply Found Calling Action Group and sending reply.")
                indigo.actionGroup.execute(int(sublist[1]))
                self.logger.info(u'iMsg: Postive Answer Received.  Running action group and sending reply.')
                self.as_sendmessage(sublist[0],sublist[3])
                self.awaitingConfirmation = [ subl for subl in self.awaitingConfirmation if subl[0]!=buddyHandle ]
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation now equals:' + unicode(self.awaitingConfirmation))
                #make new nested list removing the most recent buddy handle
                #  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'
                return True
            else:
                if self.debugextra:
                    self.debugLog(u"checkanswer() False Reply Found.")
                self.logger.info(u'iMsg: Negative Answer Received.  No action taken.')
                self.as_sendmessage(sublist[0], 'Ok.  No action Taken.')
                self.awaitingConfirmation = [subl for subl in self.awaitingConfirmation if subl[0] != buddyHandle]
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation now equals:' + unicode(self.awaitingConfirmation))
                return True

        return False

#######

    def shutdown(self):
        if self.debugextra:
            self.debugLog(u"shutdown() method called.")

    def startup(self):
        if self.debugextra:
            self.debugLog(u"Starting Plugin. startup() method called.")

        self.updater = GitHubPluginUpdater(self)

    def validatePrefsConfigUi(self, valuesDict):
        if self.debugextra:
            self.debugLog(u"validatePrefsConfigUi() method called.")

        error_msg_dict = indigo.Dict()

        # self.errorLog(u"Plugin configuration error: ")

        return True, valuesDict



    def setStatestonil(self, dev):
        if self.debugextra:
            self.debugLog(u'setStates to nil run')


    def refreshDataAction(self, valuesDict):
        """
        The refreshDataAction() method refreshes data for all devices based on
        a plugin menu call.
        """
        if self.debugextra:
            self.debugLog(u"refreshDataAction() method called.")
        self.refreshData()
        return True

    def refreshData(self):
        """
        The refreshData() method controls the updating of all plugin
        devices.
        """
        if self.debugextra:
            self.debugLog(u"refreshData() method called.")

        try:
            # Check to see if there have been any devices created.
            if indigo.devices.itervalues(filter="self"):
                if self.debugextra:
                    self.debugLog(u"Updating data...")

                for dev in indigo.devices.itervalues(filter="self"):
                    self.refreshDataForDev(dev)

            else:
                indigo.server.log(u"No Client devices have been created.")

            return True

        except Exception as error:
            self.errorLog(u"Error refreshing devices. Please check settings.")
            self.errorLog(unicode(error.message))
            return False

    def refreshDataForDev(self, dev):

        if dev.configured:
            if self.debugextra:
                self.debugLog(u"Found configured device: {0}".format(dev.name))

            if dev.enabled:
                if self.debugextra:
                    self.debugLog(u"   {0} is enabled.".format(dev.name))
                timeDifference = int(t.time() - t.mktime(dev.lastChanged.timetuple()))

            else:
                if self.debugextra:
                    self.debugLog(u"    Disabled: {0}".format(dev.name))


    def refreshDataForDevAction(self, valuesDict):
        """
        The refreshDataForDevAction() method refreshes data for a selected device based on
        a plugin menu call.
        """
        if self.debugextra:
            self.debugLog(u"refreshDataForDevAction() method called.")

        dev = indigo.devices[valuesDict.deviceId]

        self.refreshDataForDev(dev)
        return True

    def stopSleep(self, start_sleep):
        """
        The stopSleep() method accounts for changes to the user upload interval
        preference. The plugin checks every 2 seconds to see if the sleep
        interval should be updated.
        """
        try:
            total_sleep = float(self.pluginPrefs.get('configMenuUploadInterval', 300))
        except:
            total_sleep = iTimer  # TODO: Note variable iTimer is an unresolved reference.
        if t.time() - start_sleep > total_sleep:
            return True
        return False
##########
#           Action Groups
##########
    def sendiMsgQuestion(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsgQuestion() method called.")
        theMessage = self.substitute(action.props.get("message", ""))
        buddyHandle = action.props.get('buddyId','')
        lastbuddy = action.props.get('lastBuddy', False)
        timeout = action.props.get('timeout',120)
        confirmationmsg = self.substitute(action.props.get('confirmedimsg',''))
        AGtoRun = action.props.get('actiongroup','')
        expiredtime = t.time() + int(timeout)

        if lastbuddy:
            buddyHandle = str(self.lastBuddy)

        if self.debugextra:
            self.debugLog(u"sendImsgQuestion() buddyHandle:" + unicode(buddyHandle) + u' and theMessage:' + unicode(
                theMessage) + u' and use lastBuddy:' + unicode(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddyHandle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return


        try:
            #  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'
            add = [ buddyHandle, AGtoRun, expiredtime, confirmationmsg ]
            buddyalreadywaitingconfirmation = False
            for sublist in self.awaitingConfirmation:
                if sublist[0] == buddyHandle:
                    self.logger.debug(u'buddyhandle already awaiting confirmation - End. Dont ask new Question')
                    if self.debugextra:
                        self.logger.debug(u'self.awaitingConfirmation equals:' + unicode(self.awaitingConfirmation))
                    buddyalreadywaitingconfirmation= True
                    return  #

            self.as_sendmessage(buddyHandle, theMessage)
            if buddyalreadywaitingconfirmation == False:  # check not already waiting - can ask two questions same time..
                self.awaitingConfirmation.append(add)  # if not in there add
            if self.debugextra:
                self.logger.debug(u'self.awaitingConfirmation now equals:'+unicode(self.awaitingConfirmation))
        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+unicode(errortype)+u' occured.  The longer message is :'+unicode(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+unicode(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+unicode(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
            else:
                self.logger.exception(u'An unhandled exception was caught here from SendiMsgQuestion:'+unicode(ex))
        return


    def sendiMsg(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsg() method called.")
        theMessage = self.substitute(action.props.get("message", ""))
        buddyHandle = action.props.get('buddyId','')
        lastbuddy = action.props.get('lastBuddy', False)
        if lastbuddy:
            buddyHandle = str(self.lastBuddy)

        if self.debugextra:
            self.debugLog(u"sendImsg() buddyHandle:" + unicode(buddyHandle) + u' and theMessage:' + unicode(
                theMessage) + u' and use lastBuddy:' + unicode(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddy Handle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendmessage(buddyHandle, theMessage)

        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+unicode(errortype)+' occured.  The longer message is :'+unicode(ex.message))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+unicode(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+unicode(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
            else:
                self.logger.exception(u'An unhandled exception was caught here from SendiMsg:'+unicode(ex))
        return

    def sendiMsgMsgPicture(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsgMsgPicture() method called.")
        theMessage = self.substitute(action.props.get("message", ""))
        buddyHandle = action.props.get('buddyId', '')
        lastbuddy = action.props.get('lastBuddy', False)
        filepath = action.props.get('filepath','')
        if lastbuddy:
            buddyHandle = str(self.lastBuddy)

        if self.debugextra:
            self.debugLog(u"sendImsgMsgPicture() buddyHandle:" + unicode(buddyHandle) + u' and theMessage:' + unicode(
                theMessage) + u' and use lastBuddy:' + unicode(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddy Handle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendmessage(buddyHandle, theMessage)
            self.sleep(1.5)
            self.as_sendpicture(buddyHandle, filepath)

        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(
                u'A error of type :' + unicode(errortype) + ' occured.  The longer message is :' + unicode(ex.message))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  ' + unicode(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :' + unicode(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
            else:
                self.logger.exception(u'An unhandled exception was caught here from SendiMsg:' + unicode(ex))
        return



    def sendiMsgPicture(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsgPicture() method called.")
        theMessage = self.substitute(action.props.get("message", ""))
        buddyHandle = action.props.get('buddyId', '')
        lastbuddy = action.props.get('lastBuddy', False)

        if lastbuddy:
            buddyHandle = str(self.lastBuddy)

        if self.debugextra:
            self.debugLog(u"sendImsgPicture() buddyHandle:" + unicode(buddyHandle) + u' and theMessage:' + unicode(
                theMessage) + u' and use lastBuddy:' + unicode(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddyHandle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendpicture(buddyHandle, theMessage)
        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+unicode(errortype)+' occured.  The longer message is /n:'+unicode(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+unicode(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
                elif "Can?t get POSIX" in str(ex):
                    self.logger.error(u'An error occured sending to buddy :  '+unicode(buddyHandle))
                    self.logger.error(u'It seems that the File is not readable?  File given:'+unicode(theMessage))
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+unicode(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Exception:')
            else:
                self.logger.exception(u'An unhandled exception was caught here from SendiMsgPicture:'+unicode(ex))

        return

#########
    def toggleDebugEnabled(self):
        """ Toggle debug on/off. """


        self.logger.debug(u"toggleDebugEnabled() method called.")

        if self.logLevel == int(logging.INFO):
            self.debug = True
            self.pluginPrefs['showDebugInfo'] = True
            self.pluginPrefs['showDebugLevel'] = int(logging.DEBUG)
            self.logger.info(u"Debugging on.")
            self.logger.debug(u"Debug level: {0}".format(self.logLevel))
            self.logLevel = int(logging.DEBUG)
            self.logger.debug(u"New logLevel = " + str(self.logLevel))
            self.indigo_log_handler.setLevel(self.logLevel)

        else:
            self.debug = False
            self.pluginPrefs['showDebugInfo'] = False
            self.pluginPrefs['showDebugLevel'] = int(logging.INFO)
            self.logger.info(u"Debugging off.  Debug level: {0}".format(self.logLevel))
            self.logLevel = int(logging.INFO)
            self.logger.debug(u"New logLevel = " + str(self.logLevel))
            self.indigo_log_handler.setLevel(self.logLevel)
##################


    def logStatus(self):

        self.logger.debug(u'logStatus Menu Item Called')
        self.logger.info(u"{0:=^130}".format(" Plugin Details "))
        self.logger.info(u"{0:<30} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<30} {1}".format("Python version:", sys.version.replace('\n', '')))
        self.logger.info(u"{0:<30} {1}".format("Python Directory:", sys.prefix.replace('\n', '')))
        self.logger.info(u"{0:<30} {1}".format("Allowed Buddies:", self.allowedBuddies))
        self.logger.info(u"{0:<30} {1}".format("Current Messages:", self.messages))
        self.logger.info(u"{0:<30} {1}".format("Last Buddy:", self.lastBuddy))
        self.logger.info(u"{0:<30} {1}".format("Last Command Sent:", self.lastCommandsent))
        if self.triggers:
            for triggerId, trigger in sorted(self.triggers.iteritems()):
                self.logger.info(u"{0:<30} {1}".format("Triggers:", trigger.pluginTypeId +'  :  '+ trigger.name))
        self.logger.info(u"{0:<30} {1}".format("Awaiting Confirmation:", self.awaitingConfirmation))
        self.logger.info(u"{0:<30} {1}".format("Reset Last Command:", self.resetLastCommand))

        self.logger.info(u"{0:<30} {1}".format("Backup Directory:", self.backupfilename))
        self.logger.info(u"{0:<30} {1}".format("SQL Database Location:", self.filename))

        self.logger.info(u"{0:=^130}".format(""))


##################  Trigger

    def triggerStartProcessing(self, trigger):
        if self.debugtriggers:
            self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        if self.debugtriggers:
            self.logger.debug("Removing Trigger %s (%d)" % (trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device,  triggertype, imsgcmdreceived):
        if self.debugtriggers:
            self.logger.debug('triggerCheck run.  triggertype:'+unicode(triggertype))
        try:
            for triggerId, trigger in sorted(self.triggers.iteritems()):
                if self.debugtriggers:
                    self.logger.debug("Checking Trigger:  %s (%s), Type: %s,  and event : %s" % (trigger.name, trigger.id, trigger.pluginTypeId,  triggertype))
                #self.logger.error(unicode(trigger))
                if trigger.pluginTypeId == "commandReceived" and triggertype =='commandReceived':
                    if self.debugtriggers:
                        self.logger.debug(u'Trigger PluginProps: CommandCalled:'+unicode(trigger.pluginProps['commandCalled']))
                    if trigger.pluginProps['commandCalled'] == (str(imsgcmdreceived).lower()):
                        if self.debugtriggers:
                            self.logger.debug("===== Executing commandReceived Trigger %s (%d)" % (trigger.name, trigger.id))
                        indigo.trigger.execute(trigger)


        except:
            if self.debugexceptions:
                self.logger.exception(u'Exception within Trigger Check:')
            if self.debugextra:
                self.logger.debug(u'Exception within Trigger Check')
            return

