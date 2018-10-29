#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
iMessage
First draft

"""
import logging
import datetime
import time as t
import urllib2
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

        self.debugextra = self.pluginPrefs.get('debugextra', False)
        self.debugtriggers = self.pluginPrefs.get('debugtriggers', False)

        self.lastcommand = ()
        self.lastBuddy =''
        self.awaitingConfirmation = []    # buddy handle within here if waiting a reply yes or no
#  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'

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
            self.debugtriggers = valuesDict.get('debugtriggers', False)
            self.prefsUpdated = True
            self.updateFrequency = float(valuesDict.get('updateFrequency', "24")) * 60.0 * 60.0

            try:
                self.logLevel = int(valuesDict[u"showDebugLevel"])
            except:
                self.logLevel = logging.INFO

            self.indigo_log_handler.setLevel(self.logLevel)

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
        iurl = 'http://www.indigodomo.com/pluginstore/'
        self.browserOpen(iurl)

    #####

    def runConcurrentThread(self):

        try:
            self.connectsql()
            x =0
            while True:
                x=x+1
                self.sleep(5)

                messages = self.sql_fetchmessages()
                if len(messages)>0:
                    self.parsemessages(messages)
                if len(self.awaitingConfirmation)>0:
                    self.checkTimeout()
                if x>4:
                    x=0
                    self.lastcommand = ''

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

            filename = os.path.expanduser('~/Library/Messages/chat.db')
            if self.debugextra:
                self.logger.debug(u'ConnectSQL: Filename location for iMsg chat.db equals:'+unicode(filename))
            #filename = '/Users/Indigo/Library/Messages/chat.db'
          #  fd = os.open(filename, os.O_RDONLY)

           # self.logger.debug(unicode(fd))
            #self.connection = sqlite3.connect('/dev/fd/%d' % fd)
            self.connection = sqlite3.connect(filename)
            if self.debugextra:
                self.debugLog(u"Connect to Database Successful.")
        except:
            self.logger.exception(u'Exception connecting to database....')
            self.sleep(15)
            return

    def closesql(self):
        if self.debugextra:
            self.debugLog(u"connectsql() method called.")
        try:
            self.connection.close()
        except:
            self.logger.exception(u'Exception in CloseSQL')


    def sql_fetchmessages(self):
       # if self.debugextra:
       #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()
        sqlcommand = '''
            SELECT handle.id, message.text 
              FROM message INNER JOIN handle 
              ON message.handle_id = handle.ROWID 
              WHERE is_from_me=0 AND 
              datetime(message.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-10 seconds', 'localtime');      
            '''
        cursor.execute(sqlcommand)
        result = cursor.fetchall()
        if len(result)>0:
            ## just return very last message received
            ## if no messages return all
            if self.debugextra:
                self.logger.debug(unicode(result))
            return result[-1]
        return result
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
        if self.debugextra:
            self.debugLog(u"parse messages() method called.")
            self.logger.debug(u'Message Received: Message Info:'+unicode(messages))

        if self.lastcommand == messages:
            if self.debugextra:
                self.debugLog(u"Checked lastcommand SAME MESSAGE parsing aborted.")
            return

        if self.allowedBuddies is None or self.allowedBuddies=='':
            self.logger.info(u'Message Received but Allowed Buddies nil please set in Config')
            return

        if messages[0] in self.allowedBuddies:
            if self.debugextra:
                self.logger.debug(u'Passed against allowed Buddies: ' + unicode(messages))
                self.logger.debug(u'Allowed Buddies Equal:'+unicode(self.allowedBuddies))
        else:
            if self.debugextra:
                self.logger.debug(u'Message Received - but buddyhandle not allowed; Handled received equals:'+unicode(messages[0]))
                self.logger.debug(u'Allowed Buddies Equal:' + unicode(self.allowedBuddies))
                return

        if self.debugextra:
            self.logger.debug( u'self.lastcommand : '+ unicode(self.lastcommand )+ ' & message =:' + unicode(messages))

        self.lastcommand = messages
        self.lastBuddy = messages[0]

        for sublist in self.awaitingConfirmation:
            if sublist[0] == messages[0]:
                # Buddle has a outstanding confirmation awaited.
                # check against valid replies
                if self.checkanswer(messages[0],messages[1],sublist):
                    if self.debugextra:
                        self.logger.debug(u'Confirmation received so parsing message ending.  No trigger check.')

                    return

        self.triggerCheck('', 'commandReceived', messages[1] )

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


        except:
            self.logger.exception(u'Exception in SendImsgQuestion')
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
            self.logger.debug(u'Message sending aborted as buddyHandle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendmessage(buddyHandle, theMessage)
        except:
            self.logger.exception(u'Exception in SendImsg')
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
        except:
            self.logger.exception(u'Exception in SendImsgPicture')
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

##################  Trigger

    def triggerStartProcessing(self, trigger):
        self.logger.debug("Adding Trigger %s (%d) - %s" % (trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
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
            self.logger.exception(u'Exception within Trigger Check')
            return
