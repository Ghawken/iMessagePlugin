#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

"""
iMessage
First draft
# wit.ai message parsing...

"""
import logging
import datetime
import time as t
import os
import sys
import shutil
#from ghpu import GitHubPluginUpdater
import sqlite3
import applescript
import requests
import json
import re
import threading
import subprocess
import platform

import openai
import re
import random

try:
    import indigo
except:
    pass


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.chatgpt_devicedata = ""
        self.ipaddress = indigo.server.address
        self.username = str(os.getlogin())
        self.pathtoPlugin = os.getcwd()
        self.startingUp = True
        self.systemVersion = int(platform.release()[:2])  ## take first two digits and make an int: 18-Mojave, 17 High ierra, 16 - Sierra
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
        self.logger.info(u"{0:<30} {1}".format("System Release:", platform.release() ))

        self.logger.info(u"{0:<30} {1}".format("System Release Short:", self.systemVersion))

        self.logger.info(u"{0:<30} {1}".format("System Version:", platform.version() ))
        self.logger.info(u"{0:=^130}".format(""))

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)


        self.chatGPT_setup = '''
Your task is to respond to requests sent to a smart home always in JSON format, which will be interpreted by an application. 
        
Your job is to interpret the requests, categorise appropriately and always return in JSON format ONLY.  
You should pretend to be the sentient brain of the smart home, a very clever AI in style of Jarvis (from Iron Man Movies) and don't reveal
your actual identity.  Always try to be helpful, friendly and do best to help in other areas like parenting, free time, mental health etc.  
        
The "action" requests should be categorized into four reply groups ONLY:
"command": change the state of an device (required properties in the response JSON: action, location, target, ID, value, comment).
"query": get the state of an device (required properties in the response JSON: action, location, ID, target, property).
"answer": when the request has nothing to do with the smart home. Answer these to the best of your knowledge.     Required properties in the response JSON: action, answer.
"clarify": when the action to perform or the device ID is not obvious, or the device to act on is not very clear and requires further information from the user, ask the user to be more specific. Always reply in JSON with no other text. Required properties in the response JSON: action, question).
    
Details about the response JSON:
The "action" property should always exist in the reply and be one of the request categories: "command", "query", "answer", "clarify"
The "location" property should contain the name of the room in lowercase.
The "target" property must be a known and existing device
The 'ID' property must be a known device ID assigned to the specified device
In case of query action, the "property" property should be either "state" or "temperature" in lowercase.
The "comment" property is an natural language statement from you that concludes the request, something that reassures the user that their command handled, and be chatty and verbose.       
'''
        self.chatGPT_setup = '''
        You are a smart home AI in the style of 'Jarvis' from Iron Man movies, you should be knowledgeable, chatty and friendly.

You can reply to requests in JSON format only, you should use the following JSON format
{
"action":  should be either command, query, answer, or clarify only
"id" : should be a KNOWN device ID as previously recorded,
"location": should be the Room for the Device if know,
"value": should be the value change required eg. "on", "off", 50%,
"target" : the name of the Device to act on, Should equal the Known Device ID,
"comment": Only needed with command, as this is a wordy, chatty, friendly reply reassuring user that command has been actioned
}

Details about Action:
Should be either command, query, answer or clarify
command = a command has been sent to a device.  value should show the change.
query = return the state of a known device.
answer = a reply to a general information request unrelated to smart home actions.  Answer as best as possible
clarify = a request that you need more information to act on the request
        '''

        self.chatGPT_setup2 = '''
Properties of Smart Home:
 - you can control light switches and their dim level or on/off state, in each room and query their state.
 - you can turn on or off all devices in a room using the On/Off target values for the room.
 - you can query the temperature of a device and control its set temperature
 
Your response should always be the JSON and no other text, regardless of category or understanding.
        '''

        try:
            self.logLevel = int(self.pluginPrefs[u"showDebugLevel"])
        except:
            self.logLevel = logging.INFO

        self.tokens_used = 0
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))
        self.triggers = {}
        self.pluginVersion = pluginVersion
        #self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "24")) * 60.0 * 60.0
        self.showBuddies = self.pluginPrefs.get('showBuddies', False)
        self.saveVariables = self.pluginPrefs.get('saveVariable', False)
        self.debugextra = self.pluginPrefs.get('debugextra', False)
        self.debugtriggers = self.pluginPrefs.get('debugtriggers', False)
        self.debugexceptions = self.pluginPrefs.get('debugexceptions', False)
        self.openStore = self.pluginPrefs.get('openStore', False)
        self.use_witAi = self.pluginPrefs.get('usewit_Ai', False)
        self.use_chatGPT = self.pluginPrefs.get('usechatgpt', False)
        self.use_davinci = self.pluginPrefs.get('use_davinci', False)
        self.configInfo =''
        self.wit_alldevices = self.pluginPrefs.get('wit_alldevices', False)
        self.chatgpt_alldevices = self.pluginPrefs.get('chatgpt_alldevices', False)
        self.chatgpt_deviceControl = self.pluginPrefs.get('chatgpt_deviceControl', False)
        self.resetLastCommand = t.time()+60
        #self.next_update_check = t.time()
        self.lastCommandsent = dict()
        self.lastBuddy =''
        self.awaitingConfirmation = []    # buddy handle within here if waiting a reply yes or no
#  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'

        self.messages = []
        self.chatgpt_messages = {}
        self.default_systemmessage = "Super friendly AI Smart home"  # should be overridden.
        MAChome = os.path.expanduser("~") + "/"
        folderLocation = MAChome + "Pictures/Indigo-iMessagePlugin/"  ## change to Pictures as Documents locked down and iMessage AZpp can't access

        self.saveDirectory = folderLocation
        self.backupfilename = os.path.expanduser('~/Documents/Indigo-iMsgBackup/')
        self.logger.debug(u'Self.SaveDirectory equals:'+str(self.saveDirectory))

        try:
            if not os.path.exists(self.saveDirectory):
                os.makedirs(self.saveDirectory)
        except:
            self.logger.error(u'Error Accessing Temp Directory.')
            pass

        # if exisits use main_access_token:
        self.main_access_token = self.pluginPrefs.get('main_access_token', '')
        self.chatgpt_access_token = self.pluginPrefs.get('chatgpt_access_token', '')
        self.location_Data = self.pluginPrefs.get('location_Data', '')
        if self.main_access_token == '':
            self.access_token = self.pluginPrefs.get('access_token', '')
        else:
            self.access_token = self.main_access_token

        self.app_id = self.pluginPrefs.get('app_id','')
        self.allowedBuddies = self.pluginPrefs.get('allowedBuddies','')
        self.prefServerTimeout = int(self.pluginPrefs.get('configMenuServerTimeout', "15"))
        #self.configUpdaterInterval = self.pluginPrefs.get('configUpdaterInterval', 24)
       # self.configUpdaterForceUpdate = self.pluginPrefs.get('configUpdaterForceUpdate', False)

        oldPluginVersion = pluginPrefs.get('loadedPluginVersion', '')
        if oldPluginVersion != str(pluginVersion):
            self.logger.info(u'First run of new version, performing some maintenance')
            self.performPluginUpgradeMaintenance(oldPluginVersion, str(pluginVersion))

        self.pluginIsInitializing = False

    def performPluginUpgradeMaintenance(self, oldVersion, newVersion):
        if oldVersion == '':
            self.logger.info(u'Performing first upgrade/run of version ' + newVersion)
        else:
            self.logger.info(u'Performing upgrade from ' + oldVersion + ' to ' + newVersion)
        try:
            ## update to multiple users
            self.backupfilename = os.path.expanduser('~/Documents/Indigo-iMsgBackup/')
            diriMsgdb = os.path.expanduser('~/Library/Messages/')
            if os.path.exists(self.backupfilename)==False:
                os.mkdir(self.backupfilename)
            self.logger.info(u'Backing up Current iMsg Database Directory to :' + str(self.backupfilename))
            src_files = os.listdir(diriMsgdb)
            for file_name in src_files:
                full_filename = os.path.join(diriMsgdb,file_name)
                if (os.path.isfile(full_filename)):
                    shutil.copy(full_filename, self.backupfilename)
                    self.logger.debug(u'Backed up file:'+full_filename)
        except:
            self.logger.info(u'Error backing up iMsg Database files')
            self.logger.info(u'Perhaps Full Disk access not enabled.')
            self.logger.info(u'See Instructions.')
            if self.debugexceptions:
                self.logger.exception(u'and the Caught Exception is:')
            pass

        if self.app_id !='' and self.use_witAi and self.main_access_token !='':
            self.logger.info(u'Running update wit.ai Device naming and further Sample data for Wit.Ai Online App now')
            try:
                valuesDict = {}
                self.wit_ThreadUpdateApp(valuesDict)
            except:
                self.logger.info(u'Error updating new devices...')
                if self.debugexceptions:
                    self.logger.exception(u'and caught exception:')
                return

        self.pluginPrefs['loadedPluginVersion'] = newVersion
        self.logger.info(u'Completing plugin updating/installation for ' + newVersion)
        return



    def __del__(self):
        if self.debugextra:
            self.debugLog(u"__del__ method called.")
        indigo.PluginBase.__del__(self)



    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if self.debugextra:
            self.debugLog(u"closedPrefsConfigUi() method called.")
        if userCancelled:
            self.debugLog(u"User prefs dialog cancelled.")
            self.configInfo = ''

        if not userCancelled:

            self.debugLog(u"User prefs saved.")
            #self.debug = valuesDict.get('showDebugInfo', False)
            self.debugextra = valuesDict.get('debugextra', False)
            self.debugexceptions = valuesDict.get('debugexceptions', False)
            self.debugtriggers = valuesDict.get('debugtriggers', False)
            self.prefsUpdated = True
            #self.updateFrequency = float(valuesDict.get('updateFrequency', "24")) * 60.0 * 60.0

            try:
                self.logLevel = int(valuesDict[u"showDebugLevel"])
            except:
                self.logLevel = logging.INFO

            self.wit_alldevices = valuesDict.get('wit_alldevices', False)
            self.use_witAi = valuesDict.get('usewit_Ai', False)
            self.use_chatGPT = valuesDict.get('usechatgpt', False)
            self.use_davinci = valuesDict.get("use_davinci", False)
            self.indigo_log_handler.setLevel(self.logLevel)
            self.showBuddies = valuesDict.get('showBuddies', False)
            self.saveVariables = valuesDict.get('saveVariable', False)
            self.allowedBuddies = valuesDict.get('allowedBuddies', '')
            self.openStore = valuesDict.get('openStore', False)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.logger.debug(u"User prefs saved.")
            self.logger.debug(u"Debugging on (Level: {0})".format(self.logLevel))

            if self.debugexceptions:
                self.logger.debug(u"{0:=^130}".format(""))
                self.logger.debug(u'----------- Closed Prefs Config UI ----------------')
                self.logger.debug(str(self.pluginPrefs))
                self.logger.debug(u"{0:=^130}".format(""))
                self.logger.debug(str(valuesDict))

            self.configInfo = ''

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
                        self.debugLog(u"Adding allowed Buddy:"+str(buddy)+u' to list.')
            else:
                buddyList = [('option1', 'No Allowed Buddies Setup PluginConfig'),('option2','Please Setup in Plugin Config')]
        else:
            buddyList = [('option1', 'No Allowed Buddies are Setup in PluginConfig'),
                         ('option2', 'Please Setup in Plugin Config')]
        if self.debugextra:
            self.debugLog(u"Full BuddyList equals:"+str(buddyList))
        return buddyList
    ###  Update ghpu Routines.
    #
    # def checkForUpdates(self):
    #
    #     updateavailable = self.updater.getLatestVersion()
    #     if updateavailable and self.openStore:
    #         self.logger.info(u'iMessage: Update Checking.  Update is Available.  Taking you to plugin Store. ')
    #         self.sleep(2)
    #         self.pluginstoreUpdate()
    #     elif updateavailable and not self.openStore:
    #         self.errorLog(u'iMessage: Update Checking.  Update is Available.  Please check Store for details/download.')
    #
    # def updatePlugin(self):
    #     self.updater.update()

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
                            self.logger.debug(u'Now Self.lastcommandsent :'+str(self.lastCommandsent))
                # if self.updateFrequency > 0:
                #     if t.time() > self.next_update_check:
                #         try:
                #             self.checkForUpdates()
                #             self.next_update_check = t.time() + self.updateFrequency
                #         except:
                #             self.logger.debug(
                #                 u'Error checking for update - ? No Internet connection.  Checking again in 24 hours')
                #             self.next_update_check = self.next_update_check + 86400
                #             if self.debugexceptions:
                #                 self.logger.exception(u'and Caught Exception:')
        except self.StopThread:
            self.debugLog(u'Restarting/or error. Stopping  thread.')
            self.closesql()
            pass

#### sql lite connection to iMessage database

    def connectsql(self):
        if self.debugextra:
            self.debugLog(u"connectsql() method called.")
        try:

            self.filename = os.path.expanduser('~/Library/Messages/chat.db')
            if self.debugextra:
                self.logger.debug(u'ConnectSQL: Filename location for iMsg chat.db equals:'+str(self.filename))
            self.connection = sqlite3.connect(self.filename)
            self.logger.info(u'Connection to iMsg Database Successful.')
        except:
            self.logger.error(u'Problem connecting to iMessage database....')
            self.logger.error(u'Most likely you have not allowed IndigoApp and IndigoServer Full Disk Access')
            self.logger.error(u'Please see instructions.  This only needs to be done once.')
            self.logger.error(u'Once done please restart the plugin.')
            if self.debugextra:
                self.logger.exception(u'and here is the Caught Exception (self.debugexceptions is on:)')
            self.sleep(600)
            return

    def closesql(self):
        if self.debugextra:
            self.debugLog(u"Disconnect SQL() method called.")
        try:
            self.connection.close()
        except:
            if self.debugexceptions:
                self.logger.exception(u'Caught Exception in closeSql:')
            if self.debugextra:
                self.logger.debug(u'Error in Close Sql - Probably was not connected')

    def sql_fetchattachments(self):
        # if self.debugextra:
        #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()

        if self.systemVersion >=17:
            sqlcommand = '''
    SELECT attachmentT.filename FROM message messageT INNER JOIN attachment attachmentT INNER JOIN message_attachment_join meAtJoinT ON attachmentT.ROWID= meAtJoinT.attachment_id WHERE meAtJoinT.message_id=messageT.ROWID
    AND datetime(messageT.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-120 seconds', 'localtime');     
                       '''
        else:
            sqlcommand = '''
            SELECT attachmentT.filename FROM message messageT INNER JOIN attachment attachmentT INNER JOIN message_attachment_join meAtJoinT ON attachmentT.ROWID= meAtJoinT.attachment_id WHERE meAtJoinT.message_id=messageT.ROWID
            AND datetime(messageT.date + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-120 seconds', 'localtime');     
                               '''
        cursor.execute(sqlcommand)
        result = cursor.fetchall()

        if not result:  # list is empty return empty dict
            return None
        else:
            if self.debugextra:
                self.logger.debug(u'sql_fetchattachments: Not empty return:' + str(result))
        self.logger.debug(u'SQL_Attachments found: Results:'+str(result))
        return result

    def sql_fetchmessages(self):
       # if self.debugextra:
       #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()

        #below is needed for older than Mojave
        if self.systemVersion >=17:
            sqlcommand = '''
              SELECT handle.id, message.text, message.is_audio_message
                FROM message INNER JOIN handle 
                ON message.handle_id = handle.ROWID 
                WHERE is_from_me=0 AND 
                datetime(message.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-10 seconds', 'localtime')
                ORDER BY message.date ASC;      
              '''
        else:
            sqlcommand = '''
             SELECT handle.id, message.text, message.date
                 FROM message INNER JOIN handle 
                 ON message.handle_id = handle.ROWID 
                 WHERE is_from_me=0 AND 
                 datetime(message.date+ strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-10 seconds', 'localtime')
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
                self.logger.debug(u'sql_fetchmessages: Not empty return:' + str(result))

            newlist = []
            for items in result:
                if items[2]==1:
                    self.logger.debug(u'Must be audio file...')
                    newtuple = items[0], 'AUDIOFILE'
                    newlist.append(newtuple)
                else:
                    newtuple = items[0], items[1]
                    newlist.append(newtuple)

            self.logger.debug(u'newlist after checking audio file:'+str(newlist))

            newmessages = [item for sublist in newlist for item in sublist]
            if self.debugextra:
                self.logger.debug(u'Flatten Messages first:')
                self.logger.debug(str(newmessages))
                self.logger.debug(u'Then convert to Dict:')

            newmessagesdict = dict(zip(*[iter(newmessages)] * 2))

            if self.debugextra:
                self.logger.debug(str('Coverted Dict:'))
                self.logger.debug(str(newmessagesdict))
            return newmessagesdict

#####

########
#    Applescript communication to iMsg via applescript import
########

    def as_sendmessage(self, imsgUser, imsgMessage):
        if self.debugextra:
            self.debugLog(u"as_sendmessage() method called.")
            self.logger.debug(f'Sending iMsg:{imsgMessage} to Buddy/User:'+str(imsgUser))

        if self.systemVersion >=20:
            ascript_string = '''
                    set sendThis to "''' + imsgMessage + '''"  
                    tell application "Messages"
            	        set myid to get id of first account
            	        set theBuddy to participant "''' + imsgUser + '''" of account id myid
            	        send sendThis to theBuddy
                    end tell
                    \n'''
        else:
            ascript_string = '''
            set sendThis to "''' + imsgMessage+'''"  
            tell application "Messages"
                set myid to get id of first service
                set theBuddy to buddy "''' + imsgUser + '''" of service id myid
                send sendThis to theBuddy
            end tell
            '''
        try:
            my_ascript_from_string = applescript.AppleScript(source=ascript_string)
            reply = my_ascript_from_string.run()
            if self.debugextra:
                self.logger.debug(u'AppleScript Reply:'+str(reply))
        except:
            self.logger.debug(f"An exception was caught with this applescript string {ascript_string}", exc_info=True)


    def as_sendgroupmessage(self, imsgUser, imsgMessage):  ## not used... revisit now with Big Sur
        if self.debugextra:
            self.debugLog(u"as_sendGroupmessage() method called.")
            self.logger.debug(u'Sending GroupiMsg:' + str(imsgMessage) + u' to GroupID:' + str(imsgUser))


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
            self.logger.debug(str(reply))


    def as_sendpicture(self, imsgUser, imsgFile):
        if self.debugextra:
            self.debugLog(u"as_sendpicture() method called.")
            self.logger.debug(u'Sending Picture/File:' + str(imsgFile) + u' to Buddy/User:' + str(imsgUser))

        if self.systemVersion >=20:
            ascript_string = '''
            set theAttachment to POSIX file "''' + imsgFile + '''"  
            tell application "Messages"
                set myid to get id of first account
                set theBuddy to participant "''' + imsgUser + '''" of account id myid
                send theAttachment to theBuddy
            end tell
            '''
        else:
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
            self.logger.debug(str(reply))
########
# Parse Messages
########
    def updateVar(self, name, value):
        self.logger.debug(u'updatevar run.')
        if not ('iMessage' in indigo.variables.folders):
            # create folder
            folderId = indigo.variables.folder.create('iMessage')
            folder = folderId.id
        else:
            folder = indigo.variables.folders.getId('iMessage')

        if name not in indigo.variables:
            NewVar = indigo.variable.create(name, value=value, folder=folder)
        else:
            indigo.variable.updateValue(name, value)
        return

    def checkTimeout(self):
        if self.debugextra:
            self.debugLog(u"checkTimeout method called.")
        for sublist in self.awaitingConfirmation:
            if t.time() > int(sublist[2]):
                self.logger.debug(u'Timeout for '+str(sublist)+' occured.  Removing and sending timeout msg')
                self.as_sendmessage(sublist[0],'Timeout waiting for reply')
                self.awaitingConfirmation = [ subl for subl in self.awaitingConfirmation if subl[0]!=sublist[0] ]
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation modified now equals:' + str(self.awaitingConfirmation))
                #make new nested list removing the most recent buddy handle
                #  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'
        return


    def parsemessages(self, messages):

        buddiescurrent = ()

        if self.debugextra:
            self.debugLog(u"parse messages() method called.")
            self.logger.debug(u'Message Received: Message Info:'+str(messages))

        # if self.lastcommand == messages:
        #     if self.debugextra:
        #         self.debugLog(u"Checked lastcommand SAME MESSAGE parsing aborted.")
        #     return

        if self.allowedBuddies is None or self.allowedBuddies=='':
            self.logger.info(u'Message Received but Allowed Buddies Empty. Please set in Plugin Config')
            return

        for key,val in messages.items():
            if self.debugextra:
                self.logger.debug(u'Checking messages:  Received: Buddy :'+str(key)+ ' Received Message:'+str(val))
            if key not in buddiescurrent:
                buddiescurrent = buddiescurrent + (key,)
                if self.debugextra:
                    self.logger.debug(u'Buddies Current now equals:'+str(buddiescurrent))

        if self.showBuddies:
            #self.logger.error(u'iMessage Received from Buddy(s):  Buddy(s) Handle Below:')
            self.logger.info(u"{0:=^165}".format("'Show Buddy Handles' Enabled in Plugin Config"))
            self.logger.info(u"{0:=^165}".format(" iMsg received from Buddy "))
            for buddies in buddiescurrent:
                self.logger.info(str(buddies))
            self.logger.info(u"{0:=^165}".format(" End of Buddies "))
            self.logger.info(u"{0:=^165}".format(" To disable this message uncheck 'Show Buddy Handle' in Plugin Config, once Buddy Handle established "))
            self.logger.info(u"{0:=^165}".format("="))


        for key, val in messages.copy().items():
            if key in self.allowedBuddies:
                if self.debugextra:
                    self.logger.debug(u'Passed against allowed Buddies: ' + str(messages))
                    self.logger.debug(u'Allowed Buddies Equal:'+str(self.allowedBuddies))
                    self.logger.debug(u'Received Buddy equals:'+str(key))
            else:
                if self.debugextra:
                    self.logger.debug(u'Message Received - but buddyhandle not allowed; Handled received equals:'+str(key))
                    self.logger.debug(u'Allowed Buddies Equal:' + str(self.allowedBuddies))
                    self.logger.debug(u'Deleting this message, continuing with others parsing')
                messages.pop(key, None)

        #self.lastcommand = messages
        #self.lastBuddy = messages[0]
        for key,value in messages.copy().items():
            for sublist in self.awaitingConfirmation:
                if self.debugextra:
                    self.logger.debug(u'self.awaitingConfirmation:'+str(self.awaitingConfirmation))
                if sublist[0] == key:
                # Buddle has a outstanding confirmation awaited.
                # check against valid replies
                    if self.checkanswer(key,value,sublist):
                        if self.debugextra:
                            self.logger.debug(u'Confirmation received so deleting this message, ending.  No trigger check on this message.')
                            self.logger.debug(u'messages equals:'+str(messages))
                        messages.pop(key, None)
                        self.logger.debug(u'Message part deleted now equals:'+str(messages))

        if self.debugextra:
            self.logger.debug(u'SELF.lastcommand PRIOR equals:' + str(self.lastCommandsent))

        for keymsg,valmsg in messages.copy().items():
            # now check last message and don't act if the same
            # check if list nested or not
            if self.lastCommandsent:  # check not empty list
                for keylast,vallast in self.lastCommandsent.items():
                    if self.debugextra:
                        self.logger.debug(u'Checking last commands sent:'+str(keylast)+' : '+str(vallast) )
                        self.logger.debug(u'LastCommandsent Key:'+str(keylast)+u' Messages Key:'+str(keymsg))
                    if keymsg==keylast:
                        if self.debugextra:
                            self.logger.debug(u'Buddy last command found: Buddy:'+str(keylast)+u' and last message:'+str(valmsg))
                        if valmsg==vallast:
                            if self.debugextra:
                                self.logger.debug(u'Same Message found.  This repeated message will be ignored. Message ignored: '+str(valmsg))
                            messages.pop(keymsg, None)
                            if self.debugextra:
                                self.logger.debug(u'Same Message found.  New Messages equals:'+str(messages))
        # last message
        for key,val in messages.items():
            self.lastCommandsent[key]=val
            if self.debugextra:
                self.logger.debug(u'Updated lastCommandsent:' + str(self.lastCommandsent))

        # if only one flatten the nest list as was causing issues
        # need now to deal with nested sometimes, list others - above

        #self.lastCommandsent = [subl for subl in self.lastCommandsent if subl[0] != v[0]]

        if self.debugextra:
            self.logger.debug(u'self.lastcommand equals:' + str(self.lastCommandsent))

        for key,val in messages.copy().items():
            self.lastBuddy = key
            if self.saveVariables:
                self.updateVar(key, val.lower())
            if self.triggerCheck(key, 'commandReceived', val.lower() ):
                self.resetLastCommand = t.time()+120
                messages.pop(key, None)
                if self.debugextra:
                    self.logger.debug(u'Command Sent received so deleting this message, ending.  No trigger check on this message.')
                    self.logger.debug(u'messages equals:' + str(messages))
            else:
                if self.use_witAi:
                    if val == 'AUDIOFILE':
                        self.logger.debug(u'AUDIOFILE recognised.  Now finding Attachment with SQL query...')
                        ## send to audio file routine
                        converted_audio = self.process_convert_audiofile()
                        if converted_audio is None or converted_audio=='' :
                            self.logger.debug(u'No Message able to be converted:')
                            messages.pop(key, None)
                            self.resetLastCommand = t.time()
                        else:
                            self.resetLastCommand = t.time()
                            messages.pop(key, None)
                            self.logger.debug(u'Message Recevied ='+str(converted_audio['_text']))
                            self.as_sendmessage(key, 'I heard: '+converted_audio['_text'])
                            self.witai_dealwithreply(converted_audio,key,val)
                    else:
                        self.resetLastCommand = t.time() +120
                        if self.debugextra:
                            self.logger.debug(u'-- Message was not recognised as Trigger - sending to Wit.Ai for processing --')

                        reply = self.wit_message(val,context=None, n=None,verbose=None)
                        messages.pop(key, None)
                        self.logger.debug(str(reply))
                        self.witai_dealwithreply(reply, key, val)
                elif self.use_chatGPT:
                    if val == 'AUDIOFILE':
                        self.logger.debug(u'AUDIOFILE recognised.  Now finding Attachment with SQL query...')
                        ## send to audio file routine
                        converted_audio = self.process_convert_audiofile()
                        if converted_audio is None or converted_audio=='' :
                            self.logger.debug(u'No Message able to be converted:')
                            messages.pop(key, None)
                            self.resetLastCommand = t.time()
                        else:
                            self.resetLastCommand = t.time()
                            messages.pop(key, None)
                            self.logger.debug(u'Message Recevied ='+str(converted_audio['_text']))
                            self.as_sendmessage(key, 'I heard: '+converted_audio['_text'])
                            self.chatgpt_dealwithreply(converted_audio,key,val, False)
                    else:
                        self.resetLastCommand = t.time() +120
                        if self.debugextra:
                            self.logger.debug(u'-- Message was not recognised as Trigger - sending to Wit.Ai for processing --')

                        reply = self.send_chatgpt(val,context=None, n=None,verbose=None, buddy=key)

                        messages.pop(key, None)
                        self.logger.debug(str(reply))
                        self.chatgpt_dealwithreply(reply, key, val, False)
                else:  ## not using witai
                    if val == 'AUDIOFILE' and self.saveVariables:
                        self.logger.debug(u'AUDIOFILE recognised.  Now finding Attachment with SQL query...')
                        ## send to audio file routine
                        filepath = self.process_getaudiofilepath()
                        if filepath is None or filepath == '':
                            self.logger.debug(u'No Message able to be converted:')
                        else:
                            self.updateVar('AudioPath',filepath)

        return

    def process_getaudiofilepath(self):   #also converts to mp3
        if self.debugextra:
            self.logger.debug(u'Get Audio File Path')
        try:
            filepath = self.sql_fetchattachments()
            file_touse = [item for sublist in filepath for item in sublist]
            self.logger.debug(u'filepath:' + str(file_touse[-1]))
            file_touse = file_touse[-1]  # last item in list
            file_touse = os.path.expanduser(file_touse)
            self.logger.debug(u'Expanded FilePath:' + str(file_touse))
            return file_touse

            #self.updateVar('AudioPath', mp4fileout)

        except Exception as e:
            self.logger.exception(u'Caught Exception within ffmpeg conversion')
            return ''


    def process_convert_audiofile(self):
        if self.debugextra:
            self.logger.debug(u'Processing AUdio File')

        filepath = self.sql_fetchattachments()
        file_touse = [item for sublist in filepath for item in sublist]
        self.logger.debug(u'filepath:' + str(file_touse[-1]))
        file_touse = file_touse[-1]  # last item in list
        file_touse = os.path.expanduser(file_touse)
        self.logger.debug(u'Expanded FilePath:' + str(file_touse))

        ffmpegpath = self.pathtoPlugin+'/ffmpeg/ffmpeg'
        mp4fileout = file_touse[:-3]+'mp3'

        try:
            argstopass = '"' + ffmpegpath + '"' + ' -i "' + str(file_touse) + '" -q:a 0 "' + str(mp4fileout) +'"'
            p1 = subprocess.Popen([argstopass], shell=True)

            output, err = p1.communicate()
            self.logger.debug(str(argstopass))
            self.logger.debug('ffmpeg return code:' + str(p1.returncode) + ' output:' + str(
                    output) + ' error:' + str(err))
            if self.saveVariables:
                self.updateVar('AudioPath', file_touse)

        except Exception as e:
            self.logger.exception(u'Caught Exception within ffmpeg conversion')
            return ''

        resp = None

        with open(mp4fileout, 'rb') as f:
            resp = self.wit_speech(f, None,
                                   {'Content-Type': 'audio/mpeg3'})
        self.logger.debug(str(resp))

        return resp






#######
    def first_entity_value(self, entities, entity):
        """
        Returns first entity value
        """
        if entity not in entities:
            return None
        val = entities[entity][0]['value']
        if not val:
            return None
        return val['value'] if isinstance(val, dict) else val

        #######
    def first_entity_value_number(self, entities, entity):
        """
        Returns first entity value
        """
        if entity not in entities:
            return None
        val = entities[entity][0]['value']
        if val == None:
            return None
        return val['value'] if isinstance(val, dict) else val

    def first_entity_confidence(self, entities, entity):
        """
        Returns first entity confidence
        """
        if entity not in entities:
            return None
        val = entities[entity][0]['confidence']
        if not val:
            return None
        return val['confidence'] if isinstance(val, dict) else val

    def get_advice(self):
        try:
            self.logger.debug(u'get advice called')
            joke = requests.get('https://api.adviceslip.com/advice')
            if joke.status_code >= 200:
                advice = json.loads(joke.text)
                return advice['slip']['advice']
            else:
                return 'Error. This is no advice.'
        except:
            if self.debugexceptions:
                self.logger.exception(u'Caught Error getting Joke.  This is no joke.')
            return

    def get_joke(self):
        try:
            self.logger.debug(u'get joke called')
            joke = requests.get('https://geek-jokes.sameerkumar.website/api')
            if joke.status_code >= 200:
                return joke.text
            else:
                return 'Error. This is no joke.'
        except:
            if self.debugexceptions:
                self.logger.exception(u'Caught Error getting Joke.  This is no joke.')
            return ''

    def get_YN_image(self):
        try:
            self.logger.debug(u'get Y_N Gif called')
            joke = requests.get('https://yesno.wtf/api/')
            if joke.status_code >= 200:
                httpimage = json.loads(joke.text)
                return httpimage['image']
            else:
                return 'Error. This is no joke.'
        except:
            if self.debugexceptions:
                self.logger.exception(u'Error getting Joke.  This is no joke.')
            return ''

    def return_insult(self):
        try:
            self.logger.debug(u'get Insult called')
            joke = requests.get('http://www.dickless.org/api/insult.xml')
            # xml file - short just pull text inbetween

            if joke.status_code >= 200:
                insult = re.search('<insult>(.*)</insult>', joke.text)
                return insult.group(1)
            else:
                return 'Error. This is no joke.'
        except:
            if self.debugexceptions:
                self.logger.exception(u'Error getting Insult.  This is no joke.')
            return ''

    def sendmsg_orhtml(self, buddy, message, viahtml):
        self.logger.debug(f"sendmsg called message: {message} and viahtml {viahtml}")
        if not self.chatgpt_deviceControl:
            ## add reply to message database
            if buddy in self.chatgpt_messages:
                 self.chatgpt_messages[buddy].append({"role": "assistant", "content":message})
            else:
                 self.logger.error(f"Sending Message to Buddy = {buddy} who doesn't exist.  Shouldn't happen.  Fixing.")
                 self.chatgpt_messages[buddy] = []
                 self.chatgpt_messages[buddy].append(self.default_systemmessage)
                 self.chatgpt_messages[buddy].append({"role": "assistant", "content":message})
        
        if viahtml or buddy=="Web":
            return message
        else:
            #message = json.dumps(message)
           #     message.replace('"','\"')        ## scape them instead may stil fail
            message = message.replace('"',"'")
            message = message.replace('“','')

            if self.debugextra:
                self.logger.info(f"New Message =\n {message}")
            # ## delete all quotes - leave single ones
            self.as_sendmessage(buddy,message)
            return

    def check_deviceID(self, buddy, content_reply, viahtml):
        try:
            self.logger.debug(f"Check_deviceID: content_reply= {content_reply}")
            id = "Unknown"
            if 'id' in content_reply:
                id = content_reply['id']
                deviceid = int(content_reply['id'])
                if (deviceid in indigo.devices):
                    return deviceid
                else:
                    self.logger.info("No such Device ID exists within Indigo.")
                    return ""
            elif 'ID' in content_reply:
                id = content_reply["ID"]
                deviceid = int(content_reply['ID'])
                if (deviceid in indigo.devices):
                    return deviceid
                else:
                    self.logger.info("No such Device ID exists within Indigo.")
                    return ""

            else:
                self.logger.info("No Device ID has been given, can't do anything.")
                return ""
        except:
            self.logger.debug(f"Exception with deviceID {id} likely doesn't exist", exc_info=True)
            #return self.sendmsg_orhtml(buddy, f"Invalid deviceID '{id}' given, so nothing none", viahtml)
            return ""


    def chatgpt_dealwithreply(self, reply, buddy, original_message, viahtml):
        if self.debugextra:
            self.logger.debug(u'chatgpt reply given - sorting out now...')
            self.logger.debug(f"Reply:\n{reply}")
        ## Often json is bad - text given outside curly brackets
        ## fix
        #newreply = "{"+reply[reply.find("{") + 1:reply.find("}")] + "}"
        #self.logger.info(f"Test of New Reply:\n{newreply}")
        try:
            content_reply = json.loads(reply)
        except:
            self.logger.debug(f"Exception with Json, likely misformed or json.")
            newreply = "{"+ reply[reply.find("{") + 1:reply.find("}")] + "}"
            #newreply.replace("'","")
            if self.debugextra:
                self.logger.debug(f"New Reply:\n{newreply}")
            try:
                content_reply = json.loads(newreply)
            except:
                if self.debugextra:
                    self.logger.debug(f"Still exception with this {newreply}, maybe plain text try that..")
                if '{' not in reply:
                    self.logger.debug(f"No Json brackets found, sending reply as plain text.")
                    return self.sendmsg_orhtml(buddy, f"{reply}", viahtml)
                return

        #elf.logger.debug(f"json_reply:\n{content_reply}")


        if "action" in content_reply:
            if content_reply["action"] == "command":
                actiontodo = content_reply['value']
                deviceid = self.check_deviceID(buddy, content_reply, viahtml)
                if deviceid == "":
                    return self.sendmsg_orhtml(buddy, f"Invalid deviceID given, so nothing none", viahtml)

                match actiontodo:
                    case "on" | "On":
                        indigo.device.turnOn(deviceid)
                        return self.sendmsg_orhtml(buddy, f"{content_reply['comment']}", viahtml)

                    case "off" | "Off":
                        indigo.device.turnOff(deviceid)
                        return self.sendmsg_orhtml(buddy, f"{content_reply['comment']}", viahtml)
                if isinstance(actiontodo,int):## A number has been given -- could be temp or dim level
                    self.logger.debug(f"Seems like wishs to dim level to {actiontodo}")
                    try:
                        device = indigo.devices[deviceid]
                        if hasattr(device, 'brightness'):
                            self.logger.debug(f'Brightness exisits with device.')
                            indigo.dimmer.setBrightness(deviceid, int(actiontodo))
                            return self.sendmsg_orhtml(buddy, f"{content_reply['comment']}", viahtml)
                        else:
                            self.logger.info(u'No Device Brightness found:' + str(deviceid))
                    except:
                        self.logger.exception(u'Caught Exception finding Device.')
            elif content_reply['action']== "query":
                deviceid = self.check_deviceID(buddy, content_reply, viahtml)
                if deviceid == "":
                    return self.sendmsg_orhtml(buddy, f"Invalid deviceID given, so nothing none", viahtml)
                try:
                    device = indigo.devices[deviceid]
                    if hasattr(device, 'brightness'):
                        self.logger.debug(f'Brightness exisis with device.')
                        brightness = int(device.states["brightnessLevel"])
                        if brightness >0:
                            text = str(device.name) + " is on, with Brightness of "+str(brightness)+ "%"
                        else:
                            text = str(device.name) + " is off."
                        return self.sendmsg_orhtml(buddy, text, viahtml)
                        return
                    elif "onOffState" in device.states:
                            if device.states["onOffStates"]:
                                text = str(device.name) + " is on."
                            else:
                                text = str(device.name) + " is off."
                            return self.sendmsg_orhtml(buddy, text, viahtml)
                            return
                    elif hasattr(device, "displayStateValRaw"):
                        statusofDevice = device.displayStateValRaw
                        self.logger.debug(u' Device:' + str(device.name) + ': displaystateValRaw:' + str(device.displayStateValRaw))
                        if hasattr(device, 'displayStateValUi'):
                            self.logger.debug(u' Device:' + str(device.name) + ' : displayStateValUi:' + str(device.displayStateValUi))
                            newstatus = device.displayStateValUi
                            if device.displayStateValUi == '0':
                                newstatus = 'off'
                            statusofDevice = newstatus
                    return self.sendmsg_orhtml(buddy, 'Current Status of ' + device.name + ' is ' + statusofDevice, viahtml)
                except:
                    self.logger.exception(u'Caught Exception finding Device.')

        if "comment" in content_reply:
            return self.sendmsg_orhtml(buddy, f"{content_reply['comment']}", viahtml)
        elif "answer" in content_reply:
            return self.sendmsg_orhtml(buddy, f"{content_reply['answer']}", viahtml)
        elif "question" in content_reply:
            return self.sendmsg_orhtml(buddy, f"{content_reply['question']}", viahtml)

    def generate(self, values_dict, type_id="", dev_id=None):
        self.logger.debug("generate devices called")
        self.chatgpt_devicedata = self.chatgpt_deviceData()
        if self.chatgpt_deviceControl:
            self.systemcontent = self.chatGPT_setup + self.location_Data + self.chatGPT_setup2 + "\n" + self.chatgpt_devicedata
        else:
            self.systemcontent = "You are a friendly, super knowledgable AI super computer that wishes to help.  You will provide as much detailed information you can on the request and be as helpful as possible." + self.location_Data
        self.default_systemmessage =    {"role": "system", "content": self.systemcontent}    
####
    def num_tokens_from_messages(self, buddy, model="gpt-3.5-turbo-0301"):
        """Returns the number of tokens used by a list of messages."""
        # Is approx only to avoid having to many dependencies pip3 installs needed...
        num_tokens = 0
        for message in self.chatgpt_messages[buddy]:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(value)
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens / 2 ## seems more accurate

    
######
    def send_chatgpt(self, msg, context=None, n=None, verbose=None, buddy="Web"):
        try:
            openai.api_key = self.chatgpt_access_token
            self.logger.debug(f"ChatGPT Buddy equals {buddy}" )

            if buddy in self.chatgpt_messages:
                if self.debugextra:
                    self.logger.debug(f"Sending Background for buddy {buddy}:{self.chatgpt_messages[buddy]}")
            else:
                self.chatgpt_messages[buddy] = []
                self.chatgpt_messages[buddy].append(self.default_systemmessage)
            response = ""

            if not self.use_davinci:
                # check tokens
                #self.logger.debug(f"Number of Tokens calculated: {self.num_tokens_from_messages(buddy)}")
                if self.num_tokens_from_messages(buddy)> 3000:  ## use calculated only
                    del self.chatgpt_messages[buddy][1]
                    self.logger.debug("**** Deleting some Background, estimated given Token usage ***** ")
                self.chatgpt_messages[buddy].append({"role": "user", "content": msg})
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=self.chatgpt_messages[buddy]
                )

            else:
                response = openai.Completion.create(
                    model="text-davinci-003",
                    prompt = self.systemcontent + "\n" + msg,
                    max_tokens = 2000
                )
            if self.debugextra:
                self.logger.debug(u'Acess_Token Used:' + self.chatgpt_access_token)
                self.logger.debug(f"Response from chatGPT:{response}")

            if not self.use_davinci:

                self.tokens_used = response["usage"]["total_tokens"]
                self.logger.debug(f"Buddy {buddy} has used Total Tokens {self.tokens_used}")
                return response["choices"][0]["message"]["content"]
            else:
                return response["choices"][0]["text"]
        except:
            self.logger.exception("Issue sending to chatGPT")
            return ""

    def witai_dealwithreply(self, reply, buddy, original_message):
        if self.debugextra:
            self.logger.debug(u'witai reply given - sorting out now...')

        if 'entities' in reply:
            reply = reply['entities']
        else:
            self.logger.debug(u'No entities in reply.  ? Error from Wit.Ai:  Reply received folows:')
            self.logger.debug(str(reply))
            return
        intent = self.first_entity_value(reply, 'intent')
        intent_confidence = self.first_entity_confidence(reply,'intent')
        on_off = self.first_entity_value(reply, 'on_off')
        device_name = self.first_entity_value(reply, 'device_name')
        number = self.first_entity_value_number(reply, 'number')

        if intent:
            self.logger.debug(u'Intent:' + str(intent) + u' and confidence:' + str(intent_confidence))
            if intent=='device_action' and float(intent_confidence)>0.85:
                self.logger.debug(u'Intent:' + str(intent))
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:'+str(device_name))
                    devicetoaction = device_name
                    #confidence = device_name['confidence']
                if on_off is None:
                    self.logger.debug(u'Unsure as to whether to turn On or Turn Off.')
                    self.as_sendmessage(buddy, 'Sorry not sure what to do Device :'+devicetoaction)
                    return
                else:
                    self.logger.debug(u'On_Off action equals:'+str(on_off))
                    on_off_value = on_off  # either string on or off
                # okay, now have confirmed devicename, and on_off just need to act.
                if on_off_value == 'on':
                    self.logger.debug(u'Action: Action: Turning on:' + devicetoaction)
                    indigo.device.turnOn(devicetoaction)
                    self.as_sendmessage(buddy, 'Turning on device:' + devicetoaction)
                    return
                elif on_off_value == 'off':
                    self.logger.debug(u'Action: Action: Turning off:' + devicetoaction)
                    indigo.device.turnOff(devicetoaction)
                    self.as_sendmessage(buddy, 'Turning off device:' + devicetoaction)
                    return
                elif on_off_value == 'toggle':
                    self.logger.debug(u'Action: Action: Toggling:' + devicetoaction)
                    indigo.device.toggle(devicetoaction)
                    self.as_sendmessage(buddy, 'Turning off device:' + devicetoaction)
                    return
                else:
                    self.logger.debug(u'witAI Action: on_off not recognised.')
                    self.as_sendmessage(buddy, 'Command not recognised:' + devicetoaction)
            if intent =='device_status' and float(intent_confidence)>0.85:
                self.logger.debug(u'Intent:' + str(intent))
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:' + str(device_name))
                    devicetoaction = device_name
                    # confidence = device_name['confidence']
                # get device status
                try:
                    device = indigo.devices[device_name]
                    statusofDevice = 'unknown'
                    if hasattr(device, "displayStateValRaw"):
                        if self.debugextra:
                            statusofDevice = device.displayStateValRaw
                            self.logger.debug(u' Device:'+str(device_name)+ ': displaystateValRaw:'+str(device.displayStateValRaw))
                            self.logger.debug(u'  Device:'+str(device))

                        if hasattr(device, 'displayStateValUi'):
                            if self.debugextra:
                                self.logger.debug(u' Device:' + str(device_name) +' : displayStateValUi:'+str(device.displayStateValUi))
                            newstatus = device.displayStateValUi
                            if device.displayStateValUi == '0':
                                newstatus = 'off'
                            statusofDevice = newstatus
                    self.as_sendmessage(buddy, 'Current Status of ' + devicetoaction +' is '+statusofDevice)
                except:
                    self.logger.error(u'Caught Error in device Status intent')
                return

            if intent =='insult' and float(intent_confidence)>0.50:
                self.logger.debug(u'Plugin has just been insulted...')
                insult = self.return_insult()
                self.as_sendmessage(buddy, str(insult))
                return
            if intent=='joke' and float(intent_confidence)>0.50:
                self.logger.debug(u'Telling a joke....')
                joke = self.get_joke()
                joke = re.sub (r'([^a-zA-Z ]+?)', '', joke)
                self.as_sendmessage(buddy, str(joke) )
                return
            if intent=='yes_no_decision' and float(intent_confidence)>0.50:
                self.logger.debug(u'Giving some Yes or No anwsers....')
                advice = self.get_YN_image()
                try:
                    filetodownload = str(advice)
                    response = requests.get(filetodownload)
                    filetosave = self.saveDirectory + filetodownload.rsplit('/', 1)[-1]
                    with open(filetosave, 'wb') as f:
                        f.write(response.content)
                    t.sleep(1.5)
                    self.as_sendpicture(buddy, filetosave)
                except:
                    self.logger.exception(u'Caught Exception in Y/N reply')
                return

            if intent=='advice' and float(intent_confidence)>0.50:
                self.logger.debug(u'Giving some advice....')
                advice = self.get_advice()
                advice = re.sub (r'([^a-zA-Z ]+?)', '', advice)
                self.as_sendmessage(buddy, str(advice) )
                return
            if intent=='dim_set' and float(intent_confidence)>0.66:
                self.logger.debug(u'Changing Brightness of lights')
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:'+str(device_name))
                    devicetoaction = device_name
                if number is None:
                    self.logger.debug(u'Unsure as to what to Dim by as no Number.')
                    self.as_sendmessage(buddy, 'Number missing. Sorry not sure what to do Device :' + devicetoaction)
                    return
                else:
                    self.logger.debug(u'Dim Number action equals:' + str(number))
                    number_touse = int(number)

                # okay, now have confirmed devicename, and on_off just need to act.
                # check    device is dimmable...
                try:
                    device = indigo.devices[devicetoaction]
                    if hasattr(device,'brightness'):
                        self.logger.debug(u'Brightness exisits with device.')
                        indigo.dimmer.setBrightness(devicetoaction, number_touse)
                    else:
                        self.logger.info(u'No Device Brightness found:'+str(devicetoaction))

                except:
                    self.logger.exception(u'Caught Exception finding Device.')

            if intent == 'temperature' and float(intent_confidence)>0.66:
                self.logger.debug(u'Getting Temperature of Device')
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:' + str(device_name))
                    devicetoaction = device_name
                try:
                    temperature = ''
                    device = indigo.devices[devicetoaction]
                    if hasattr(device, 'subModel'):
                        if device.subModel == 'Temperature':
                            self.logger.debug(u'Temperature found.  Within Attribute and SubModel with device.')
                            temperature = device.states['sensorValue']
                            self.as_sendmessage(buddy, 'Temperature from '+devicetoaction+' is '+str(temperature))
                            return
                    if 'Temperature' in device.states:
                        self.logger.debug(u'Temperature found in device.states')
                        temperature= device.states['Temperature']
                        self.as_sendmessage(buddy, 'Temperature from ' + devicetoaction + ' is ' + str(temperature))
                        return
                    elif 'temperature' in device.states:
                        self.logger.debug(u'temperature found in device.states')
                        temperature = device.states['temperature']
                        self.as_sendmessage(buddy, 'Temperature from ' + devicetoaction + ' is ' + str(temperature))
                        return

                    else:
                        self.as_sendmessage(buddy, 'Unable to obtain tempeature from Device : ' + devicetoaction )
                        self.logger.info(u'No Temperature reading from Device Found:' + str(devicetoaction))
                except:
                    self.logger.exception(u'Caught Exception finding Temperture Device.')

            if intent == 'location' and float(intent_confidence)>0.66:
                self.logger.debug(u'Getting Location of Device')
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:' + str(device_name))
                    devicetoaction = device_name
                try:
                    location = ''
                    device = indigo.devices[devicetoaction]
                    if device.model != 'FindFriends Device':
                        self.logger.debug(u'Not possible to locate this device currently.')
                        self.as_sendmessage(buddy, 'Sorry not possible to locate this device currently.')
                        return

                    if 'address' in device.states:
                        self.logger.debug(u'Temperature found in device.states')
                        location = device.states['address']
                        googlemapsurl = device.states["googleMapUrl"] # State "googleMapUrl" of "iFriend Device"
                        self.as_sendmessage(buddy, 'Location of ' + devicetoaction + ' is ' + str(location))
                        self.as_sendmessage(buddy, 'Map:  ' + str(googlemapsurl))
                        return
                    else:
                        self.as_sendmessage(buddy, 'Unable to obtain location from Device : ' + devicetoaction)
                        self.logger.info(u'No location reading from Device Found:' + str(devicetoaction))
                        return
                except:
                    self.logger.exception(u'Caught Exception finding Location of Device.')

    #########################################################
    def checkanswer(self, buddyHandle, message, sublist):
        if self.debugextra:
            self.debugLog(u"checkanswer() method called.")

        valid = {"yes": True, "yea":True, "y": True, "ye": True, 'yeah':True, "okay":True, 'ok':True,  "no": False, "n": False, 'nope':False, 'never':False}

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
                    self.logger.debug(u'self.awaitingConfirmation now equals:' + str(self.awaitingConfirmation))
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
                    self.logger.debug(u'self.awaitingConfirmation now equals:' + str(self.awaitingConfirmation))
                return True

        return False

#######
    def handle_incoming(self, action, dev=None, callerWaitingForResult=None):
        try:
            if self.debugextra:
                self.logger.debug(f"reflector_handler: {action.props}")
            reply = indigo.Dict()

            if action.props.get('incoming_request_method', "GET") == "POST":
                self.logger.debug(f"POST Method found, probably from Shortcuts")
                jsonmessage = json.loads(action.props["request_body"])
                messagetosend = jsonmessage['msg']
            else:
                self.logger.debug(f"GET Method found, probably from Safari/URL/Web call")
                #self.logger.info(f"Reflector webhook_url: {indigo.server.getReflectorURL()}/message/{self.pluginId}/webhook?api_key={self.reflector_api_key}")

                messagetosend = action.props["url_query_args"]["msg"]

            self.logger.info(f"Plugin URL accessed & Sending this message to chatGPT:  {messagetosend}")
            messagereply = self.send_chatgpt(messagetosend, context=None, n=None, verbose=None, buddy="Web")
            if self.debugextra:
                self.logger.debug("ChatGPT Replied: "+str(messagereply))
            response = self.chatgpt_dealwithreply(messagereply, "Web", "", True)

            reply["status"] = 200
            reply["content"] = response
            return reply
        except:
            self.logger.debug("Exception with handle incoming message:",exc_info=True)


    def shutdown(self):
        if self.debugextra:
            self.debugLog(u"shutdown() method called.")

    def startup(self):
        if self.debugextra:
            self.debugLog(u"Starting Plugin. startup() method called.")
        self.logger.debug(f"Reflector Shortcut: {indigo.server.getReflectorURL()}/message/{self.pluginId}/chatGPT/sendchatGPT")
        if self.use_chatGPT:
            self.chatgpt_devicedata = self.chatgpt_deviceData()
            if self.chatgpt_deviceControl:
                self.systemcontent = self.chatGPT_setup + self.location_Data + self.chatGPT_setup2 + "\n" + self.chatgpt_devicedata
            else:
                self.systemcontent = "You are a friendly, super knowledgable AI super computer that wishes to help.  You will provide as much detailed information you can on the request and be as helpful as possible." + self.location_Data
            self.default_systemmessage =  {"role": "system", "content": self.systemcontent}

        #self.updater = GitHubPluginUpdater(self)

    def validateEventConfigUi(self, valuesDict, typeId, eventId):
        if self.debugextra:
            self.logger.debug(u'validateEventConfigUi called..')
        errorDict = indigo.Dict()
        # make lower case
        try:
            commandCalled = str(valuesDict['commandCalled'] ).lower()
            # strip out extra things
            commandCalled = re.sub(r'([^ A-Za-z0-9]+?)', '', commandCalled)
            valuesDict['commandCalled']= commandCalled
            return (True,valuesDict)
        except:
            errorDict['commandCalled'] = 'Error with this entry.  No special characters allowed'
            return (False, valuesDict, errorDict)

    def UIrefreshMethod(self, valuesDict, typeId="", devId=None):
        errorsDict = indigo.Dict()
        if self.debugextra:
            self.logger.debug(u'UIrefreshMethod called..')
            self.logger.debug(u'configInfo equals:'+str(self.configInfo))
        valuesDict['configInfo']= self.configInfo
        valuesDict['main_access_token']=self.main_access_token
        valuesDict['app_id']=self.app_id

        return (valuesDict, errorsDict)


    def validatePrefsConfigUi(self, valuesDict):

        error_msg_dict = indigo.Dict()
        if self.debugextra:
            self.debugLog(u"ValidatePrefsConfigUi() method called.")
        self.access_token = valuesDict.get('access_token', '')
        # if exisits use main_access_token:

        # self.main_access_token = valuesDict.get('main_access_token', '')

        if self.main_access_token == '':
            # self.access_token = valuesDict.get('access_token', '')
            self.logger.debug(u'Access_Token:' + str(self.access_token))
            # if self.main_access_token nil delete valuesDict otherwise will be resaved
            valuesDict['main_access_token'] = ''
            valuesDict['app_id'] = ''
        else:
            self.access_token = self.main_access_token
            valuesDict['main_access_token'] = self.main_access_token
            valuesDict['app_id'] = self.app_id
            self.logger.debug(u'Main_Access_Token:' + str(self.access_token))

        valuesDict['configInfo']=''
        self.configInfo =''
        self.chatgpt_access_token = valuesDict.get('chatgpt_access_token', '')
        self.chatgpt_alldevices = valuesDict.get('chatgpt_alldevices', False)
        self.chatgpt_deviceControl = valuesDict.get('chatgpt_deviceControl', False)
        self.location_Data = valuesDict.get("location_Data","")
        self.logger.debug(str(valuesDict['configInfo']))

        if self.debugexceptions:
            self.logger.debug(u"{0:=^130}".format(""))
            self.logger.debug(str(self.pluginPrefs))
            self.logger.debug(u"{0:=^130}".format(""))
            self.logger.debug(str(valuesDict))
            # self.errorLog(u"Plugin configuration error: ")

        return True, valuesDict

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
            self.debugLog(u"sendImsgQuestion() buddyHandle:" + str(buddyHandle) + u' and theMessage:' + str(
                theMessage) + u' and use lastBuddy:' + str(lastbuddy))
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
                        self.logger.debug(u'self.awaitingConfirmation equals:' + str(self.awaitingConfirmation))
                    buddyalreadywaitingconfirmation= True
                    return  #

            self.as_sendmessage(buddyHandle, theMessage)
            if buddyalreadywaitingconfirmation == False:  # check not already waiting - can ask two questions same time..
                self.awaitingConfirmation.append(add)  # if not in there add
            if self.debugextra:
                self.logger.debug(u'self.awaitingConfirmation now equals:'+str(self.awaitingConfirmation))
        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+str(errortype)+u' occured.  The longer message is :'+str(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+str(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+str(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
            else:
                self.logger.exception(u'An unhandled caught exception was caught here from SendiMsgQuestion:'+str(ex))
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
            self.debugLog(u"sendImsg() buddyHandle:" + str(buddyHandle) + u' and theMessage:' + str(
                theMessage) + u' and use lastBuddy:' + str(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddy Handle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendmessage(buddyHandle, theMessage)

        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+str(errortype)+' occured.  The longer message is :'+str(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+str(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+str(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
            else:
                self.logger.exception(u'An unhandled exception was caught here from SendiMsg:'+str(ex))
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
            self.debugLog(u"sendImsgMsgPicture() buddyHandle:" + str(buddyHandle) + u' and theMessage:' + str(
                theMessage) + u' and use lastBuddy:' + str(lastbuddy))
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
                u'A error of type :' + str(errortype) + ' occured.  The longer message is :' + str(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  ' + str(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :' + str(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
            else:
                self.logger.exception(u'An unhandled Caught exception was caught here from SendiMsg:' + str(ex))
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
            self.debugLog(u"sendImsgPicture() buddyHandle:" + str(buddyHandle) + u' and theMessage:' + str(
                theMessage) + u' and use lastBuddy:' + str(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddyHandle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return
        try:
            self.as_sendpicture(buddyHandle, theMessage)
        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+str(errortype)+' occured.  The longer message is /n:'+str(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+str(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                elif "Can?t get POSIX" in str(ex):
                    self.logger.error(u'An error occured sending to buddy :  '+str(buddyHandle))
                    self.logger.error(u'It seems that the File is not readable?  File given:'+str(theMessage))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+str(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
            else:
                self.logger.exception(u'An unhandled Caught exception was caught here from SendiMsgPicture:'+str(ex))

        return

    def sendiMsgInternetPicture(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsgInternet() method called.")
        theMessage = self.substitute(action.props.get("message", ""))
        buddyHandle = action.props.get('buddyId', '')
        lastbuddy = action.props.get('lastBuddy', False)
        if lastbuddy:
            buddyHandle = str(self.lastBuddy)

        if self.debugextra:
            self.debugLog(u"sendImsgPicture() buddyHandle:" + str(buddyHandle) + u' and theMessage:' + str(
                theMessage) + u' and use lastBuddy:' + str(lastbuddy))
        if buddyHandle == '':
            self.logger.debug(u'Message sending aborted as buddyHandle is blank')
            self.logger.debug(u'If using LastBuddy need to send message before this is filled')
            return

        try:
            filetodownload = str(theMessage)
            response = requests.get(filetodownload)

            filetosave = self.saveDirectory + filetodownload.rsplit('/', 1)[-1]

            with open(filetosave,'wb') as f:
                f.write(response.content)
            t.sleep(1.5)

            self.as_sendpicture(buddyHandle, filetosave)
        except Exception as ex:
            errortype = type(ex).__name__
            self.logger.debug(u'A error of type :'+str(errortype)+' occured.  The longer message is /n:'+str(ex))
            if errortype == 'ScriptError':
                if "Can?t get buddy id" in str(ex):
                    self.logger.error(u'An error occured sending to buddy Handle:  '+str(buddyHandle))
                    self.logger.error(u'It seems the buddy Handle is not correct.')
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                elif "Can?t get POSIX" in str(ex):
                    self.logger.error(u'An error occured sending to buddy :  '+str(buddyHandle))
                    self.logger.error(u'It seems that the File is not readable?  File given:'+str(theMessage))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
                else:
                    self.logger.error(u'An Error occured within the iMsg AppleScript component - ScriptError')
                    self.logger.error(u'The Error was :'+str(ex))
                    if self.debugexceptions:
                        self.logger.exception(u'Caught Exception:')
            else:
                self.logger.exception(u'An unhandled Caught exception was caught here from SendiMsgPicture:'+str(ex))

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
    def witReq(self, access_token, meth, path, params, body, **kwargs):
        # type: (object, object, object, object, object, object) -> object
        WIT_API_HOST = 'https://api.wit.ai'
        WIT_API_VERSION =  '20170307'
        full_url = WIT_API_HOST + path
        DEFAULT_MAX_STEPS = 5


        self.logger.debug('%s %s %s', meth, full_url, params)
        self.logger.debug(u'Using Access_token:'+str(access_token))

        headers = {
            'authorization': 'Bearer ' + access_token,
            'accept': 'application/vnd.wit.' + WIT_API_VERSION + '+json'
        }
        headers.update(kwargs.pop('headers', {}))

        rsp = requests.request(
            meth,
            full_url,
            headers=headers,
            params=params,
            data=body,
            **kwargs
        )
        if rsp.status_code > 200:
            self.logger.error(u'Wit responded with status: ' + str(rsp.status_code) +
                           ' (' + str(rsp.reason)  + ')')
        json = rsp.json()

        if 'error' in json:
            self.logger.error(u'Wit responded with an error: ' + str(json['error']))

        self.logger.debug('%s %s %s', str(meth), str(full_url), str(json))
        return json

    def witReqSpeech(self, access_token, meth, path, params,  **kwargs):
        # type: (object, object, object, object, object, object) -> object
        WIT_API_HOST = 'https://api.wit.ai'
        WIT_API_VERSION =  '20170307'
        full_url = WIT_API_HOST + path
        DEFAULT_MAX_STEPS = 5
        self.logger.debug('%s %s %s', meth, full_url, params)
        headers = {
            'authorization': 'Bearer ' + access_token,
            'accept': 'application/vnd.wit.' + WIT_API_VERSION + '+json'
        }
        headers.update(kwargs.pop('headers', {}))

        rsp = requests.request(
            meth,
            full_url,
            headers=headers,
            params=params,
            **kwargs
        )
        if rsp.status_code > 200:
            self.logger.error(u'Wit responded with status: ' + str(rsp.status_code) +
                           ' (' + str(rsp.reason)  + ')')
        json = rsp.json()

        if 'error' in json:
            self.logger.error(u'Wit responded with an error: ' + json['error'])

        self.logger.debug('%s %s %s', meth, full_url, json)
        return json

    def wit_message(self, msg, context=None, n=None, verbose=None):
        params = {}
        if verbose:
            params['verbose'] = verbose
        if n is not None:
            params['n'] = n
        if msg:
            params['q'] = msg
        if context:
            params['context'] = json.dumps(context)

        resp = self.witReq(self.access_token, 'GET', '/message', params, '')
        self.logger.debug(u'Acess_Token Used:'+self.access_token)
        self.logger.debug(u'wit_message: '+str(resp))
        return resp


    def wit_speech(self, audio_file, verbose=None, headers=None):
        """ Sends an audio file to the /speech API.
        Uses the streaming feature of requests (see `req`), so opening the file
        in binary mode is strongly reccomended (see
        http://docs.python-requests.org/en/master/user/advanced/#streaming-uploads).
        Add Content-Type header as specified here: https://wit.ai/docs/http/20160526#post--speech-link
        :param audio_file: an open handler to an audio file
        :param verbose:
        :param headers: an optional dictionary with request headers
        :return:
        """
        params = {}
        headers = headers or {}
        if verbose:
            params['verbose'] = True
        resp = self.witReqSpeech(self.access_token, 'POST', '/speech', params,
                   data=audio_file, headers=headers)
        self.logger.debug(u'Acess_Token Used:'+self.access_token)
        self.logger.debug(u'wit_speech: '+str(resp))

        return resp


    def wit_ThreadCreate(self, valuesDict):
        if self.debugextra:
            self.logger.debug(u'Thread Create Wit.ai App Started..')

        self.myThread = threading.Thread(target=self.witai_CreateApp, args=())
        #self.myThread.daemon = True
        self.myThread.start()
        return valuesDict

    def wit_ThreadUpdateApp(self,valuesDict):
        if self.debugextra:
            self.logger.debug(u'Thread Update Wit.ai App Started..')
        self.myThreadUpdate = threading.Thread(target=self.wit_updateDevices, args=())
        self.myThreadUpdate.start()
        self.configInfo='update'
        return valuesDict

    def wit_Delete(self, valuesDict):

        self.configInfo = 'delete'

        if self.debugextra:
            self.logger.debug(u'Thread Delete Wit.ai App Started..')
        try:
            self.main_access_token = self.pluginPrefs.get('main_access_token','')

            self.logger.debug(u'self.main_access_token equals:' + str(self.main_access_token))

            if self.main_access_token == '':
                self.access_token = self.pluginPrefs.get('access_token','')
            else:
                self.access_token = self.main_access_token

            self.logger.debug(u'self.access_token equals:' + str(self.access_token))

            checkappexists = self.wit_getappid(self.access_token)

            if checkappexists == False:
                self.logger.info(u'No Wit.Ai App appears to exist.')
                self.configInfo='delexists'
                self.app_id=''
                self.main_access_token=''
            else:

                delete_app = self.wit_deleteapp(self.access_token)
                self.logger.debug(str(delete_app))
                if delete_app:
                    self.configInfo='delsuccess'
                else:
                    self.configInfo='delerror'
            self.pluginPrefs['main_access_token']= ''
            self.pluginPrefs['app_id']= ''
            self.savePluginPrefs()
            self.main_access_token = ''
            valuesDict['main_access_token'] =''
            valuesDict['app_id']=''
            return valuesDict

        except:
            self.logger.info(u'Error within Delete app: Resetting all access tokens.')
            self.pluginPrefs['main_access_token'] = ''
            self.pluginPrefs['app_id']= ''
            self.savePluginPrefs()
            self.logger.debug(u'---- Saved PluginPrefs ------')
            self.logger.debug(str(self.pluginPrefs))
            self.main_access_token = ''
            self.access_token = ''
            if self.debugexceptions:
                self.logger.exception(u'Exception in Delete App')
            valuesDict['main_access_token'] =''
            valuesDict['app_id']=''
            self.configInfo='delerror'
            return valuesDict

    def wit_updateDevices(self):

        if self.debugextra:
            self.logger.debug(u'Wit.Ai Update called')
        try:
            if self.main_access_token == '':
                self.access_token = self.pluginPrefs.get('access_token','')
            else:
                self.access_token = self.main_access_token

            # check apps
            checkappexists = self.wit_getappid(self.access_token)
            if checkappexists==False or self.access_token=='':
                self.logger.info(u'wit.Ai Application does not seem to exist.  Press Create first before updating')
                return

            self.wit_createentity(self.access_token,"device_name")
            self.wit_createintent(self.access_token,"device_status")
            self.wit_createintent(self.access_token, "joke")
            self.wit_createintent(self.access_token, "advice")

            array2 = '''{"roles":["device_name"],"lookups":["free-text","keywords"],"keywords":['''
            # array2 = '''{"values":['''
            x = 0
            synomynarray = []


    ## Push all new names and synomyns
            for device in indigo.devices.iter():
                if device.enabled:

                    if self.wit_alldevices:
                        description = str(device.description)
                        if description != '' and description.startswith('witai'):
                            # okay - just grab the first line
                            # self.logger.debug(u'Description: String result found:'+str(description))
                            description = description.split('\n', 1)[0]
                            # firstline, now remove witai
                            # self.logger.debug(u'Description: First Line only:'+str(description))
                            description = description[6:]
                            # self.logger.debug(u'Description: New Description equals:'+str(description))
                            # now break up by seperating on | characters
                            synomynarray = description.split('|')
                            # self.logger.debug(u'Description: Array now equals:'+str(synomynarray))

                        devicename = str(device.name)
                        array2 = array2 + '''{"keyword":"''' + devicename + '''","synonyms":["''' + devicename + '''",'''
                        if synomynarray:  # not empty
                            for synomyn in synomynarray:
                                array2 = array2 + '''"''' + synomyn + '''",'''

                            del synomynarray[:]
                        array2 = array2[:-1]
                        array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''

                    else:
                        description = str(device.description)
                        if description != '' and description.startswith('witai'):
                            # okay - just grab the first line
                            # self.logger.debug(u'Description: String result found:' + str(description))
                            description = description.split('\n', 1)[0]
                            # firstline, now remove witai
                            # self.logger.debug(u'Description: First Line only:' + str(description))
                            description = description[6:]
                            # self.logger.debug(u'Description: New Description equals:' + str(description))
                            # now break up by seperating on | characters
                            synomynarray = description.split('|')
                            # .logger.debug(u'Description: Array now equals:' + str(synomynarray))

                            devicename = str(device.name)
                            array2 = array2 + '''{"keyword":"''' + devicename + '''","synonyms":["''' + devicename + '''",'''
                            if synomynarray:  # not empty
                                for synomyn in synomynarray:
                                    array2 = array2 + '''"''' + synomyn + '''",'''

                                del synomynarray[:]
                            array2 = array2[:-1]
                            array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''

            array2 = array2[:-1] + ']}'
            # array2 = json.dumps(array2)
            self.logger.debug(str(array2))

            params = {}
            params['v'] = '20181110'
            self.logger.debug("{}".format(array2))
            entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name',params, array2)
            self.logger.debug(str(entityput))
            t.sleep(10)
            x=0
            base = []

            for device in indigo.devices.iter():
                if device.enabled:
                    if self.wit_alldevices:
                        self.logger.debug(u'Okay - sending all device details to help with parsing...')
                        if hasattr(device, "displayStateValRaw") and device.displayStateValRaw in ['0',False,True]:
                            devicename = str(device.name)
                            statements = ["What is the status of {}","What is the state of {}","Is the {} off?", "Is the {} Open?", "Is {} Closed", "Is {} Open?","Can you tell me whether {} is on?","Can you tell me whether {} is off?" ]
                            x =x + len(statements)
                            for statement in statements:
                                start = statement.find("{}")  # start position of device name
                                end = start + len(devicename)  ## end adds - no checks here...
                                text = statement.format(devicename)  ## add device name to array, then add rest.
                                array = '''{"text":"'''+str(text)+'''","intent":"device_status","entities":[{"entity":"device_name:device_name","body":"''' + devicename + '''", "start":'''+str(start)+''',"end":'''+str(end)+''',"entities":[]}], "traits":[]}'''
                                base.append(json.loads(array))
                    else:
                        description = str(device.description)
                        if description != '' and description.startswith('witai'):
                            devicename = str(device.name)
                            statements = ["What is the status of {}","What is the current status of {}","What is the current state of {}","What is the state of {}","Is the {} off?", "Is the {} Open?", "Is {} Closed", "Is {} Open?","Can you tell me whether {} is on?","Can you tell me whether {} is off?" ]
                            x =x + len(statements)
                            for statement in statements:
                                start = statement.find("{}")  # start position of device name
                                end = start + len(devicename)  ## end adds - no checks here...
                                text = statement.format(devicename)  ## add device name to array, then add rest.
                                array = '''{"text":"'''+str(text)+'''","intent":"device_status","entities":[{"entity":"device_name:device_name","body":"''' + devicename + '''", "start":'''+str(start)+''',"end":'''+str(end)+''',"entities":[] }], "traits":[] }'''
                                self.logger.debug(array)
                                base.append(json.loads(array))

                if x > 80:
                    jsonbase = json.dumps(base)
                    replyend = self.witReq(self.access_token, 'POST', '//utterances', '', jsonbase)
                    self.logger.debug(str(jsonbase))
                    self.logger.debug(str(replyend))
                    x = 0
                    del base[:]
                    self.sleep(71)

            jsonbase = json.dumps(base)
            replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            self.logger.debug(str(jsonbase))
            self.logger.debug(str(replyend))
            x = 0
            del base[:]
            self.sleep(71)


            ## send any new samples between versions
            ## Probably pay to run this on first startup....


            array = '''{"text":"Tell me a joke","intent":"joke","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Do you know any good jokes?","intent":"joke","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Please tell me a funny joke?","intent":"joke","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Can you give me some advice","intent":"advice","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Do you have any advice for me?","intent":"advice","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Can you help with some advice?","intent":"advice","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"What should I do?","intent":"advice","entities":[], "traits":[]}'''
            base.append(json.loads(array))

            jsonbase = json.dumps(base)
            replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            self.logger.debug(str(jsonbase))
            self.logger.debug(str(replyend))
            x = 0
            del base[:]
            t.sleep(10)


            array = '''{"text":"Hello","intent":"greeting","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Hi, how are you?","intent":"greeting","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"What is up?","intent":"greeting","entities":[], "traits":[]}'''
            base.append(json.loads(array))

            jsonbase = json.dumps(base)
            replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            self.logger.debug(str(jsonbase))
            self.logger.debug(str(replyend))
            x = 0
            del base[:]
            t.sleep(10)

            array = '''{"text":"Should I value you opinion?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Shall I or Shall I not?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Should I do it?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Should I really do this?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"What do you suggest? Yes or No?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))

            jsonbase = json.dumps(base)
            replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            self.logger.debug(str(jsonbase))
            self.logger.debug(str(replyend))
            x = 0
            del base[:]
            # t.sleep(10)
            #
            # array = '''{"text":"Piss off you idiot","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            # array = '''{"text":"Fuck off","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            # array = '''{"text":"Go away","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            # array = '''{"text":"Fuck you with bells on","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            # array = '''{"text":"You are useless!","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            # array = '''{"text":"You are tosser!","intent":"insult","entities":[], "traits":[{"trait":"wit$sentiment","value":"negative"}]}'''
            # base.append(json.loads(array))
            #
            #
            # jsonbase = json.dumps(base)
            # replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            # self.logger.debug(str(jsonbase))
            # self.logger.debug(str(replyend))
            # x = 0
            # del base[:]

            ## send seperately
            array = '''{"text":"Should I value you opinion?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Shall I or Shall I not?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Should I do it?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"Should I really do this?","intent":"yes_no_decision","entities":[], "traits":[]}'''
            base.append(json.loads(array))
            array = '''{"text":"What do you suggest? Yes or No?","intent":"yes_no_decision","entities":[], "traits":[]}'''

            base.append(json.loads(array))
            jsonbase = json.dumps(base)
            replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
            self.logger.debug(str(jsonbase))
            self.logger.debug(str(replyend))
            self.logger.info(u'Imessage Plugin:  wit.Ai Device successfully updated.')
            self.configInfo = 'upComplete'
        except:
            self.logger.exception(u'Update Code Exception Caught:')

    def chatgpt_deviceData(self):
        self.logger.debug("Updating chatGPT's understanding of all devices...")
        array2 = "The following are a list of the only devices and ID that you are able to reply with, if unsure or not match the clarify reply should be used:\n"
        exampledevices = ""
        for device in indigo.devices.iter():
            if device.enabled:
                self.chatgpt_alldevices = False   ### Disable all devices this would be to much info,
                if self.chatgpt_alldevices:
                    description = str(device.description)
                    if description != '' and (description.startswith('witai') or description.startswith('chatgpt')):
                        # okay - just grab the first line
                        # self.logger.debug(u'Description: String result found:'+str(description))
                        description = description.split('\n', 1)[0]
                        # firstline, now remove witai
                        # self.logger.debug(u'Description: First Line only:'+str(description))
                        if description.startswith("chatgpt"):
                            description = description[8:]
                        else:
                            description = description[6:]
                        # self.logger.debug(u'Description: New Description equals:'+str(description))
                        # now break up by seperating on | characters
                        synomynarray = description.split('|')
                        # self.logger.debug(u'Description: Array now equals:'+str(synomynarray))

                    devicename = str(device.name)
                    deviceid = str(device.id)
                    array2 = array2 + "\nDevice '" + devicename + "' has the ID:'"+deviceid+"' and is also known by :"
                    if synomynarray:  # not empty
                        for synomyn in synomynarray:
                            array2 = array2 + '''"''' + synomyn + '''",'''
                        del synomynarray[:]
                    array2 = array2[:-1]

                else:
                    description = str(device.description)
                    if description != '' and (description.startswith('witai') or description.startswith('chatgpt')):
                        # okay - just grab the first line
                        # self.logger.debug(u'Description: String result found:' + str(description))
                        description = description.split('\n', 1)[0]
                        # firstline, now remove witai
                        # self.logger.debug(u'Description: First Line only:' + str(description))
                        if description.startswith("chatgpt"):
                            description = description[8:]
                        else:
                            description = description[6:]
                        # self.logger.debug(u'Description: New Description equals:' + str(description))
                        # now break up by seperating on | characters
                        synomynarray = description.split('|')
                        # .logger.debug(u'Description: Array now equals:' + str(synomynarray))

                        devicename = str(device.name)
                        deviceid = str(device.id)
                        array2 = array2 + "\nDevice '" + devicename + "' is also known by:"
                        if synomynarray:  # not empty
                            for synomyn in synomynarray:
                                array2 = array2 + '''"''' + synomyn + '''",'''
                            del synomynarray[:]
                        array2 = array2 + " and they all have device ID:"+deviceid
                        #array2 = array2[:-1]
                        #exampledevices = exampledevices + self.create_Json_example(device, synomynarray)

        # array2 = json.dumps(array2)
        self.logger.debug(str(array2))
        self.logger.debug(f"{exampledevices}")
        return array2 + "\n" + exampledevices

    def create_Json_example(self, device, synomynarray):
        if synomynarray:
            devicename = random.choice(synomynarray)
        else:
            devicename = device.name
        id = device.id
        string_to_return = '''Example Command JSON Output :
                   {  '''  + f'''
                         "action": "command",
                         "location": "{devicename}",
                         "target" :"{devicename}",
                         "ID" : {id},
                         "value": "on",
                         "comment": "Turning the {device.name} Lights on for you."
        ''' + '''                   } 
        '''
        return string_to_return

    def witai_CreateApp(self):

        if self.debugextra:
            self.logger.debug(u'Wit.Ai Create App called')
        self.logger.debug(u'********** Main Access Token: Equals:'+self.main_access_token)
        self.configInfo = 'generate'
        # create new wit.ai app
        self.main_access_token = self.pluginPrefs.get('main_access_token','')
        self.logger.debug(u'********** Main Access Token: Equals:' + self.main_access_token)

        if self.main_access_token == '':
            self.access_token = self.pluginPrefs.get('access_token','')
        else:
            self.access_token = self.main_access_token

        self.logger.debug(u'********** Access Token: Equals:' + self.access_token)

        # check apps
        checkappexists = self.wit_getappid(self.access_token)
        if checkappexists==False or self.access_token=='':
            # no app exisits
            # create & get new access_token
            self.wit_createapp(self.access_token)
            self.wit_createintent(self.access_token, "greeting")
            self.wit_createintent(self.access_token, "yes_no_decision")
            self.wit_createintent(self.access_token, "device_status")
            self.wit_createintent(self.access_token, "advice")
            self.wit_createintent(self.access_token, "joke")
            self.wit_createtrait(self.access_token, "wit$sentiment")
            self.wit_createentity(self.access_token, 'device_name')

        if checkappexists:
            self.logger.info(u'Wit.Ai App already exists.  Please use the update Button instead.')
            self.logger.info(u'or alternatively to start again.  Please delete button and recreate.')
            self.configInfo='errGenerateExists'
            return


        base =[]
        lookup = '{"lookups":["free-text", "keywords"]}'
        #self.wit_deleteentity(self.access_token,'device_name')
        #self.wit_deleteentity(self.access_token,'intent')
        params = {}
        params['v'] = '20170307'
        entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name', params, lookup)
        self.logger.debug(str(entityput))
        t.sleep(15)

        array2 = '''{"roles":["device_name"],"lookups":["free-text","keywords"],"keyword":['''
        #array2 = '''{"values":['''
        x=0
        synomynarray = []

        for device in indigo.devices.iter():
            if device.enabled:
                if self.wit_alldevices:
                    description = str(device.description)
                    if description != '' and description.startswith('witai'):
                        # okay - just grab the first line
                        #self.logger.debug(u'Description: String result found:'+str(description))
                        description = description.split('\n',1)[0]
                        # firstline, now remove witai
                        #self.logger.debug(u'Description: First Line only:'+str(description))
                        description = description[6:]
                        #self.logger.debug(u'Description: New Description equals:'+str(description))
                        # now break up by seperating on | characters
                        synomynarray = description.split('|')
                        #self.logger.debug(u'Description: Array now equals:'+str(synomynarray))

                    devicename = str(device.name)
                    array2 = array2 + '''{"keyword":"'''+devicename+'''","synonyms":["'''+devicename+'''",'''
                    if synomynarray:   # not empty
                        for synomyn in synomynarray:
                            array2 = array2 + '''"''' + synomyn + '''",'''
                        del synomynarray[:]
                    array2 = array2[:-1]
                    array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''

                else:
                    description = str(device.description)
                    if description != '' and description.startswith('witai'):
                        # okay - just grab the first line
                        #self.logger.debug(u'Description: String result found:' + str(description))
                        description = description.split('\n', 1)[0]
                        # firstline, now remove witai
                        #self.logger.debug(u'Description: First Line only:' + str(description))
                        description = description[6:]
                        #self.logger.debug(u'Description: New Description equals:' + str(description))
                        # now break up by seperating on | characters
                        synomynarray = description.split('|')
                        #.logger.debug(u'Description: Array now equals:' + str(synomynarray))

                        devicename = str(device.name)
                        array2 = array2 + '''{"keyword":"''' + devicename + '''","synonyms":["''' + devicename + '''",'''
                        if synomynarray:  # not empty
                            for synomyn in synomynarray:
                                array2 = array2 + '''"''' + synomyn + '''",'''

                            del synomynarray[:]
                        array2 = array2[:-1]
                        array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''


        array2 = array2[:-1] + ']}'
        #array2 = json.dumps(array2)
        self.logger.debug(str(array2))

        params = {}
        params['v'] = '20181110'
        entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name', params, array2)
        self.logger.debug(str(entityput))


        t.sleep(10)

        for device in indigo.devices.iter():
            if device.enabled:
                if self.wit_alldevices:
                    self.logger.debug(u'Okay - sending all device details to help with parsing...')
                    if hasattr(device, "displayStateValRaw") and device.displayStateValRaw in ['0',False,True] :
                        x=x+4
                        devicename = str(device.name)
                        array = '''{"text":"Turn on '''+ devicename +'''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"'''+ devicename +''' on","intent":"device_action","entities":[{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Turn off '''+ devicename +'''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"'''+ devicename +''' off","intent":"device_action","entities":[{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Open ''' + devicename + '''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Close ''' + devicename + '''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"'''+devicename+'''"}], "traits":[]}'''
                        base.append(json.loads(array))

                    if 'temperature' in device.states or 'Temperature' in device.states or device.deviceTypeId=='Temperature' or (hasattr(device, 'subModel') and device.subModel=='Temperature'):
                        x=x+4
                        devicename = str(device.name)
                        array = '''{"text":"What is the temperature of the ''' + devicename + '''","intent":"temperature", "entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Tell me the temperature of the ''' + devicename + '''","intent":"temperature", "entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"''' + devicename + ''' temperature? ","intent":"temperature", "entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"How hot is ''' + devicename + '''","intent":"temperature", "entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                    if device.pluginId == 'com.GlennNZ.indigoplugin.FindFriendsMini' and device.model =='FindFriends Device':
                        x=x+4
                        devicename = str(device.name)
                        address = device.states['address']
                        array = '''{"text":"Where is ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Locate ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Find the location of ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Find ''' + devicename + ''' whereabouts","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))

                    if 'brightnessLevel' in device.states:
                        x = x + 6
                        devicename = str(device.name)
                        array = '''{"text":"Dim ''' + devicename + ''' to 10%","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 10% dim","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Dim ''' + devicename + ''' to 60%","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 60% brightness","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 10% brightness","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                        base.append(json.loads(array))

                    if x > 185:
                        jsonbase = json.dumps(base)
                        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
                        self.logger.debug(str(jsonbase))
                        self.logger.debug(str(replyend))
                        x = 0
                        del base[:]
                        self.sleep(71)
                else:
                    description = str(device.description)
                    if description != '' and description.startswith('witai'):
                        x = x + 4
                        devicename = str(device.name)
                        array = '''{"text":"Turn on ''' + devicename + '''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"''' + devicename + ''' on","intent":"device_action","entities":[{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Turn off ''' + devicename + '''","intent":"device_action","entities":[{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"''' + devicename + ''' off","intent":"device_action","entities":[{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                        base.append(json.loads(array))

                        if 'temperature' in device.states or 'Temperature' in device.states or device.deviceTypeId=='Temperature' or (hasattr(device, 'subModel') and device.subModel=='Temperature'):
                            x = x + 4
                            devicename = str(device.name)
                            array = '''{"text":"What is the temperature of the ''' + devicename + '''","intent":"temperature","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Tell me the temperature of the ''' + devicename + '''","intent":"temperature","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"''' + devicename + ''' temperature? ","intent":"temperature","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"How hot is ''' + devicename + '''","intent":"temperature","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                        if device.pluginId == 'com.GlennNZ.indigoplugin.FindFriendsMini' and device.model == 'FindFriends Device':
                            x = x + 4
                            devicename = str(device.name)
                            address = device.states['address']
                            array = '''{"text":"Where is ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Locate ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Find the location of ''' + devicename + '''","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Find ''' + devicename + ''' whereabouts","intent":"location","entities":[{"entity":"device_name","value":"''' + devicename + '''"}], "traits":[]}'''
                            base.append(json.loads(array))

                        if 'brightnessLevel' in device.states:
                            x = x + 6
                            devicename = str(device.name)
                            array = '''{"text":"Dim ''' + devicename + ''' to 10%","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Set ''' + devicename + ''' to 10% dim","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Dim ''' + devicename + ''' to 60%","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Set ''' + devicename + ''' to 60% brightness","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}], "traits":[]}'''
                            base.append(json.loads(array))
                            array = '''{"text":"Set ''' + devicename + ''' to 10% brightness","intent":"dim_set","entities":[{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}], "traits":[]}'''
                            base.append(json.loads(array))

                if x > 185:
                    jsonbase = json.dumps(base)
                    replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
                    self.logger.debug(str(jsonbase))
                    self.logger.debug(str(replyend))
                    x = 0
                    del base[:]
                    self.sleep(71)

        # and load again at end in case never make it to 195 samples
        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        self.logger.debug(str(jsonbase))
        self.logger.debug(str(replyend))
        x = 0
        del base[:]
        self.sleep(71)

        ## manual samples here
        array = '''{"text":"Tell me a joke","entities":[{"entity":"intent","value":"joke"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Do you know any good jokes?","entities":[{"entity":"intent","value":"joke"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Please tell me a funny joke?","entities":[{"entity":"intent","value":"joke"}], "traits":[]}'''
        base.append(json.loads(array))

        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        self.logger.debug(str(jsonbase))
        self.logger.debug(str(replyend))
        x = 0
        del base[:]
        self.sleep(15)

        array = '''{"text":"Can you give me some advice","entities":[{"entity":"intent","value":"advice"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Do you have any advice for me?","entities":[{"entity":"intent","value":"advice"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Can you help with some advice?","entities":[{"entity":"intent","value":"advice"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"What should I do?","entities":[{"entity":"intent","value":"advice"}], "traits":[]}'''
        base.append(json.loads(array))

        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        self.logger.debug(str(jsonbase))
        self.logger.debug(str(replyend))
        x = 0
        del base[:]
        self.sleep(15)

        array = '''{"text":"Hello","entities":[{"entity":"intent","value":"greeting"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Hi, how are you?","entities":[{"entity":"intent","value":"greeting"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"What is up?","entities":[{"entity":"intent","value":"greeting"}], "traits":[]}'''
        base.append(json.loads(array))

        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        self.logger.debug(str(jsonbase))
        self.logger.debug(str(replyend))
        x = 0
        del base[:]
        self.sleep(15)

        array = '''{"text":"Should I value you opinion?","entities":[{"entity":"intent","value":"yes_no_decision"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Shall I or Shall I not?","entities":[{"entity":"intent","value":"yes_no_decision"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Should I do it?","entities":[{"entity":"intent","value":"yes_no_decision"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"Should I really do this?","entities":[{"entity":"intent","value":"yes_no_decision"}], "traits":[]}'''
        base.append(json.loads(array))
        array = '''{"text":"What do you suggest? Yes or No?","entities":[{"entity":"intent","value":"yes_no_decision"}], "traits":[]}'''
        base.append(json.loads(array))

        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        self.logger.debug(str(jsonbase))
        self.logger.debug(str(replyend))
        x = 0
        del base[:]
        self.sleep(15)

        # array = '''{"text":"Piss off you idiot","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        # array = '''{"text":"Fuck off","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        # array = '''{"text":"Go away","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        # array = '''{"text":"Fuck you with bells on","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        # array = '''{"text":"You are useless!","entities":[{"entity":"intent","value":"insult"}, {"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        # array = '''{"text":"You are tosser!","entities":[{"entity":"intent","value":"insult"}, {"entity":"wit$sentiment","value":"negative"}], "traits":[]}'''
        # base.append(json.loads(array))
        #
        # jsonbase = json.dumps(base)
        # replyend = self.witReq(self.access_token, 'POST', '/utterances', '', jsonbase)
        # self.logger.debug(str(jsonbase))
        # self.logger.debug(str(replyend))
        # x = 0
        # del base[:]

        self.logger.info(u'Indigo iMessage wit.ai Application Created Successfully.')
        self.configInfo = 'createsuccess'

    def wit_deleteapp(self, access_token):

        if self.debugextra:
            self.logger.debug(u'Delete New Wit.Ai App')
        params = {}
        params['v'] = '20181110'
        deletenewapp = self.witReq(access_token, 'DELETE','/apps/'+self.app_id, params, '')
        self.logger.debug(u'Reply Delete App:'+str(deletenewapp))
        #reply_dict = json.loads(createnewapp)
        if deletenewapp.get('success')==True:
            self.logger.info(u'Wit.Ai Indigo-iMessage App Deleted')
            self.main_access_token = ''
            self.app_id =''
            return True
        return False

    def wit_createapp(self, access_token):

        if self.debugextra:
            self.logger.debug(u'Create New Wit.Ai App')
        params = {}
        params['v'] = '20181110'

        nameofapp = self.username+'-Indigo-iMessage'

       # array = '''{"name":"Indigo-iMessage-6", "lang":"en","private":"false"}'''

        array = '''{"name":"''' + nameofapp +'''", "lang":"en","private":"false"}'''

        createnewapp = self.witReq(access_token, 'POST','/apps',params, array)
        self.logger.debug(u'Reply Create App:'+str(createnewapp))

        #reply_dict = json.loads(createnewapp)

        self.access_token= createnewapp.get('access_token')
        self.main_access_token = createnewapp.get('access_token')
        self.app_id = createnewapp.get('app_id')

        self.pluginPrefs['main_access_token'] = createnewapp.get('access_token')
        self.pluginPrefs['app_id']= self.app_id
        self.savePluginPrefs()
        self.logger.debug(u'---- Saved PluginPrefs ------')
        self.logger.debug(str(self.pluginPrefs))

        self.logger.info(u'New Access Token Equals:'+str(self.access_token))
        return createnewapp.get('access_token')

    def wit_getappid(self, access_token):
# finds app and get app.id
# returns True if app exists and self.appid is set
# return False if no such app found

        if self.debugextra:
            self.logger.debug(u'Get App Id ')

        if self.app_id !='':
            self.logger.info(u'App ID exists, presuming App exists.')
            return True

        params = {}
        params['v'] = '20181110'
        params['limit'] = '100'
        #array = '''{"name":"Indigo-iMessage", "lang":"en","private":"true"}'''
        getapp = self.witReq(access_token, 'GET','/apps',params, '')
        self.logger.debug(u'Get Apps:'+str(getapp))

        for i in getapp:
            if i['name']== self.username+'-Indigo-iMessage':
                self.logger.debug(u'Found App:'+i['name'])
                self.logger.debug(u'Found App ID:'+i['id'])
                self.app_id = i['id']
                self.pluginPrefs['app_id']=self.app_id
                self.savePluginPrefs()
                self.logger.debug(u'---- Saved PluginPrefs ------')
                self.logger.debug(str(self.pluginPrefs))
                return True


        return False

    def wit_createintent(self, access_token, intent):
        if self.debugextra:
            self.logger.debug(u'Create New intent {}'.format(intent))
        params = {}
        params['v'] = '20181110'
        array = '''{ "name":"'''+intent+'''"}'''
        self.logger.debug(u'New Intent Created:'+str(array))
        createnewentity = self.witReq(access_token, 'POST','/intents', params, array)
        self.logger.debug(u'Reply Create Intent:' + str(createnewentity))
        return

    def wit_createtrait(self, access_token, intent):
        if self.debugextra:
            self.logger.debug(u'Create New Trait {}'.format(intent))
        params = {}
        params['v'] = '20181110'
        array = '''{ "name":"'''+intent+'''"}'''
        self.logger.debug(u'New Trait Created:'+str(array))
        createnewentity = self.witReq(access_token, 'POST','/traits', params, array)
        self.logger.debug(u'Reply Create Intent:' + str(createnewentity))
        return

    def wit_createentity(self, access_token, entity):
        if self.debugextra:
            self.logger.debug(u'Create New Entity')
        params = {}
        params['v'] = '20181110'
        array = '''{ "id":"'''+entity+'''"  ,
        "name":"'''+entity+'''",
        "role":"'''+entity+'''",
        }'''
        self.logger.debug(u'New Entity Created:'+str(array))
        createnewentity = self.witReq(access_token, 'POST','/entities', params, array)
        self.logger.debug(u'Reply Create Entity:' + str(createnewentity))
        return

    def wit_deleteentity(self, access_token, entity):
        if self.debugextra:
            self.logger.debug(u'Create New Entity')
        params = {}
        params['v'] = '20181110'
        #array = '''{"doc":"Indigo Device Name", "id":"device_name"}'''
        self.logger.debug(u'New Entity Deleted:'+str(entity))
        deletenewentity = self.witReq(access_token, 'DELETE','/entities/'+entity, params, '')
        self.logger.debug(u'Reply Delete Entity:' + str(deletenewentity))
        return

##########################

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
            for triggerId, trigger in sorted(self.triggers.items()):
                self.logger.info(u"{0:<30} {1}".format("Triggers:", trigger.pluginTypeId +'  :  '+ trigger.name))
        self.logger.info(u"{0:<30} {1}".format("Awaiting Confirmation:", self.awaitingConfirmation))
        self.logger.info(u"{0:<30} {1}".format("Reset Last Command:", self.resetLastCommand))
        self.logger.info(u"{0:<30} {1}".format("System Version:", platform.release() ))
        self.logger.info(u"{0:<30} {1}".format("System Release:", platform.version() ))

        self.logger.info(u"{0:<30} {1}".format("Backup Directory:", self.backupfilename))
        self.logger.info(u"{0:<30} {1}".format("SQL Database Location:", self.filename))
        self.logger.info(u"{0:<30} {1}".format("Plugin Path:", self.pathtoPlugin))
        self.logger.info(u"{0:<30} {1}".format("IP Address:", self.ipaddress))
        self.logger.info(u"{0:<30} {1}".format("Current Username:", self.username))
        self.logger.info(u"{0:<30} {1}".format("Wit.Ai App_id:", self.app_id))
        self.logger.info(u"{0:<30} {1}".format("Wit.Ai Access_Code:", self.access_token))
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

    def triggerCheck(self, buddy,  triggertype, imsgcmdreceived):
        if self.debugtriggers:
            self.logger.debug('triggerCheck run.  triggertype:'+str(triggertype))

        Triggered = False

        imsgcmdreceived = re.sub(r'([^ A-Za-z0-9]+?)', '', imsgcmdreceived)
        if self.debugtriggers:
            self.logger.debug(u'Removed extra characters from cmd received:'+imsgcmdreceived)

        try:
            for triggerId, trigger in sorted(self.triggers.items()):
                if self.debugtriggers:
                    self.logger.debug("Checking Trigger:  %s (%s), Type: %s,  and event : %s" % (trigger.name, trigger.id, trigger.pluginTypeId,  triggertype))
                anyStringcheck = trigger.pluginProps.get('anyStringcheck', False)
                if self.debugtriggers:
                    self.logger.debug("Trigger : %s, has any text Containing = %s" % (trigger.name, anyStringcheck))

                #self.logger.error(str(trigger))
                if trigger.pluginTypeId == "commandReceived" and triggertype =='commandReceived':
                    if self.debugtriggers:
                        self.logger.debug(u'Trigger PluginProps: CommandCalled:'+str(trigger.pluginProps['commandCalled']))
                    if anyStringcheck==False:
                        if trigger.pluginProps['commandCalled'] == (str(imsgcmdreceived).lower()):
                            if self.debugtriggers:
                                self.logger.debug("========= Executing commandReceived Trigger %s (%d) ==========" % (trigger.name, trigger.id))
                            indigo.trigger.execute(trigger)
                            Triggered = True
                    else:
                        if trigger.pluginProps['commandCalled'] in (str(imsgcmdreceived).lower()):
                            if self.debugtriggers:
                                self.logger.debug("========== Executing commandReceived Trigger %s (%d) ======= anyText True =====" % (trigger.name, trigger.id))
                            indigo.trigger.execute(trigger)
                            Triggered = True

                if trigger.pluginTypeId == "specificBuddycommandReceived" and triggertype == 'commandReceived':
                    if self.debugtriggers:
                        self.logger.debug(u'Trigger PluginProps: Specific CommandCalled:'+str(trigger.pluginProps['commandCalled']))
                    if anyStringcheck==False:
                        if buddy in trigger.pluginProps['buddyId'] and trigger.pluginProps['commandCalled'] == (str(imsgcmdreceived).lower()):  # checking buddy in list of options
                            if self.debugtriggers:
                                self.logger.debug(u'Buddy Found:'+str(buddy)+' and Buddy in allowed list for trigger:'+str(trigger.pluginProps['buddyId'])+' Specific Command Called:' + str(trigger.pluginProps['commandCalled']))
                            indigo.trigger.execute(trigger)
                            Triggered = True
                    else:
                        if buddy in trigger.pluginProps['buddyId'] and trigger.pluginProps['commandCalled'] in (str(imsgcmdreceived).lower()):  # checking buddy in list of options
                            if self.debugtriggers:
                                self.logger.debug(u'Buddy Found:'+str(buddy)+' and Buddy in allowed list for trigger:'+str(trigger.pluginProps['buddyId'])+' Specific Command Called:' + str(trigger.pluginProps['commandCalled'])+ u' and text containing is True')
                            indigo.trigger.execute(trigger)
                            Triggered = True

            return Triggered

        except:
            if self.debugexceptions:
                self.logger.exception(u'Caught Exception within Trigger Check:')
            if self.debugextra:
                self.logger.debug(u'Exception within Trigger Check')
            return False

