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
from ghpu import GitHubPluginUpdater
import sqlite3
import applescript
import requests
import json
import re
import threading
import subprocess

try:
    import indigo
except:
    pass


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.pathtoPlugin = os.getcwd()
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
        self.use_witAi = self.pluginPrefs.get('usewit_Ai', False)

        self.wit_alldevices = self.pluginPrefs.get('wit_alldevices', False)
        self.resetLastCommand = t.time()+60
        self.next_update_check = t.time()
        self.lastCommandsent = dict()
        self.lastBuddy =''
        self.awaitingConfirmation = []    # buddy handle within here if waiting a reply yes or no
#  'buddy', 'AGtorun', 'timestamp', 'iMsgConfirmed'

        self.messages = []

        MAChome = os.path.expanduser("~") + "/"
        folderLocation = MAChome + "Documents/Indigo-iMessagePlugin/"
        self.saveDirectory = folderLocation

        self.logger.debug(u'Self.SaveDirectory equals:'+unicode(self.saveDirectory))

        try:
            if not os.path.exists(self.saveDirectory):
                os.makedirs(self.saveDirectory)
        except:
            self.logger.error(u'Error Accessing Temp Directory.')
            pass


        # if exisits use main_access_token:
        self.main_access_token = self.pluginPrefs.get('main_access_token', '')
        if self.main_access_token == '':
            self.access_token = self.pluginPrefs.get('access_token', '')
        else:
            self.access_token = self.main_access_token


        self.app_id = self.pluginPrefs.get('app_id','')
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

            self.wit_alldevices = valuesDict.get('wit_alldevices', False)
            self.use_witAi = valuesDict.get('usewit_Ai', False)
            self.indigo_log_handler.setLevel(self.logLevel)
            self.showBuddies = valuesDict.get('showBuddies', False)
            self.allowedBuddies = valuesDict.get('allowedBuddies', '')
            self.openStore = valuesDict.get('openStore', False)
            self.logger.debug(u"logLevel = " + str(self.logLevel))
            self.logger.debug(u"User prefs saved.")
            self.logger.debug(u"Debugging on (Level: {0})".format(self.logLevel))
            self.access_token = valuesDict.get('access_token','')
            # if exisits use main_access_token:
            self.main_access_token = valuesDict.get('main_access_token', '')
            if self.main_access_token == '':
                self.access_token = valuesDict.get('access_token', '')
            else:
                self.access_token = self.main_access_token

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
            buddyList = [('option1', 'No Allowed Buddies are Setup in PluginConfig'),
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
            self.debugLog(u"Disconnect SQL() method called.")
        try:
            self.connection.close()
        except:
            if self.debugexceptions:
                self.logger.exception(u'Exception in closeSql:')
            if self.debugextra:
                self.logger.debug(u'Error in Close Sql - Probably was not connected')

    def sql_fetchattachments(self):
        # if self.debugextra:
        #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()

        sqlcommand = '''
SELECT attachmentT.filename FROM message messageT INNER JOIN attachment attachmentT INNER JOIN message_attachment_join meAtJoinT ON attachmentT.ROWID= meAtJoinT.attachment_id WHERE meAtJoinT.message_id=messageT.ROWID
AND datetime(messageT.date/1000000000 + strftime("%s", "2001-01-01") ,"unixepoch","localtime") >= datetime('now','-120 seconds', 'localtime');     
                   '''

        cursor.execute(sqlcommand)
        result = cursor.fetchall()

        if not result:  # list is empty return empty dict
            return None
        else:
            if self.debugextra:
                self.logger.debug(u'sql_fetchattachments: Not empty return:' + unicode(result))
        self.logger.debug(u'SQL_Attachments found: Results:'+unicode(result))
        return result

    def sql_fetchmessages(self):
       # if self.debugextra:
       #     self.debugLog(u"fetch messages() method called.")
        cursor = self.connection.cursor()

        sqlcommand = '''
           SELECT handle.id, message.text, message.is_audio_message
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

            newlist = []
            for items in result:
                if items[2]==1:
                    self.logger.debug(u'Must be audio file...')
                    newtuple = items[0], 'AUDIOFILE'
                    newlist.append(newtuple)
                else:
                    newtuple = items[0], items[1]
                    newlist.append(newtuple)

            self.logger.debug(u'newlist after checking audio file:'+unicode(newlist))

            newmessages = [item for sublist in newlist for item in sublist]
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
            if self.triggerCheck(key, 'commandReceived', val.lower() ):
                self.resetLastCommand = t.time()+120
                messages.pop(key, None)
                if self.debugextra:
                    self.logger.debug(u'Command Sent received so deleting this message, ending.  No trigger check on this message.')
                    self.logger.debug(u'messages equals:' + unicode(messages))
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
                            self.logger.debug(u'Message Recevied ='+unicode(converted_audio['_text']))
                            self.as_sendmessage(key, 'I heard: '+converted_audio['_text'])
                            self.witai_dealwithreply(converted_audio,key,val)
                    else:
                        self.resetLastCommand = t.time() +120
                        if self.debugextra:
                            self.logger.debug(u'-- Message was not recognised as Trigger - sending to Wit.Ai for processing --')

                        reply = self.wit_message(val,context=None, n=None,verbose=None)
                        messages.pop(key, None)
                        self.logger.debug(unicode(reply))
                        self.witai_dealwithreply(reply, key, val)
        return
    def process_convert_audiofile(self):
        if self.debugextra:
            self.logger.debug(u'Processing AUdio File')

        filepath = self.sql_fetchattachments()
        file_touse = [item for sublist in filepath for item in sublist]
        self.logger.debug(u'filepath:' + unicode(file_touse[-1]))
        file_touse = file_touse[-1]  # last item in list
        file_touse = os.path.expanduser(file_touse)
        self.logger.debug(u'Expanded FilePath:' + unicode(file_touse))

        ffmpegpath = self.pathtoPlugin+'/ffmpeg/ffmpeg'
        mp4fileout = file_touse[:-3]+'mp3'

        try:
            argstopass = '"' + ffmpegpath + '"' + ' -i "' + str(file_touse) + '" -q:a 0 "' + str(mp4fileout) +'"'
            p1 = subprocess.Popen([argstopass], shell=True)

            output, err = p1.communicate()
            self.logger.debug(unicode(argstopass))
            self.logger.debug('ffmpeg return code:' + unicode(p1.returncode) + ' output:' + unicode(
                    output) + ' error:' + unicode(err))

        except Exception as e:
            self.logger.exception(u'Caught Exception within ffmpeg conversion')
            return ''

        resp = None

        with open(mp4fileout, 'rb') as f:
            resp = self.wit_speech(f, None,
                                   {'Content-Type': 'audio/mpeg3'})
        self.logger.debug(unicode(resp))

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
            self.logger.exception(u'Error getting Joke.  This is no joke.')
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
            self.logger.exception(u'Error getting Joke.  This is no joke.')
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
            self.logger.exception(u'Error getting Insult.  This is no joke.')
            return ''

######
    def witai_dealwithreply(self, reply, buddy, original_message):
        if self.debugextra:
            self.logger.debug(u'witai reply given - sorting out now...')

        if 'entities' in reply:
            reply = reply['entities']
        else:
            self.logger.debug(u'No entities in reply.  ? Error from Wit.Ai:  Reply received folows:')
            self.logger.debug(unicode(reply))
            return
        intent = self.first_entity_value(reply, 'intent')
        intent_confidence = self.first_entity_confidence(reply,'intent')
        on_off = self.first_entity_value(reply, 'on_off')
        device_name = self.first_entity_value(reply, 'device_name')
        number = self.first_entity_value_number(reply, 'number')

        if intent:
            self.logger.debug(u'Intent:' + unicode(intent) + u' and confidence:' + unicode(intent_confidence))
            if intent=='device_action' and float(intent_confidence)>0.85:
                self.logger.debug(u'Intent:' + unicode(intent))
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:'+unicode(device_name))
                    devicetoaction = device_name
                    #confidence = device_name['confidence']
                if on_off is None:
                    self.logger.debug(u'Unsure as to whether to turn On or Turn Off.')
                    self.as_sendmessage(buddy, 'Sorry not sure what to do Device :'+devicetoaction)
                    return
                else:
                    self.logger.debug(u'On_Off action equals:'+unicode(on_off))
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
                    self.logger.exception(u'Exception in Y/N reply')
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
                    self.logger.debug(u'Acting on Device:'+unicode(device_name))
                    devicetoaction = device_name
                if number is None:
                    self.logger.debug(u'Unsure as to what to Dim by as no Number.')
                    self.as_sendmessage(buddy, 'Number missing. Sorry not sure what to do Device :' + devicetoaction)
                    return
                else:
                    self.logger.debug(u'Dim Number action equals:' + unicode(number))
                    number_touse = int(number)

                # okay, now have confirmed devicename, and on_off just need to act.
                # check    device is dimmable...
                try:
                    device = indigo.devices[devicetoaction]
                    if hasattr(device,'brightness'):
                        self.logger.debug(u'Brightness exisits with device.')
                        indigo.dimmer.setBrightness(devicetoaction, number_touse)
                    else:
                        self.logger.info(u'No Device Brightness found:'+unicode(devicetoaction))

                except:
                    self.logger.exception(u'Exception finding Device.')

            if intent == 'temperature' and float(intent_confidence)>0.66:
                self.logger.debug(u'Getting Temperature of Device')
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:' + unicode(device_name))
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
                        self.logger.info(u'No Temperature reading from Device Found:' + unicode(devicetoaction))
                except:
                    self.logger.exception(u'Caught Exception finding Temperture Device.')

            if intent == 'location' and float(intent_confidence)>0.66:
                self.logger.debug(u'Getting Location of Device')
                if device_name is None:
                    self.logger.debug(u'Unsure as to which Device to act on.')
                    self.as_sendmessage(buddy, 'Sorry not sure which Device to act on.  Nothing done.')
                    return
                else:
                    self.logger.debug(u'Acting on Device:' + unicode(device_name))
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
                        self.logger.info(u'No location reading from Device Found:' + unicode(devicetoaction))
                        return
                except:
                    self.logger.exception(u'Caught Exception finding Location of Device.')

    #########################################################
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

    def sendiMsgInternetPicture(self, action):
        if self.debugextra:
            self.debugLog(u"sendImsgInternet() method called.")
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
            filetodownload = str(theMessage)
            response = requests.get(filetodownload)

            filetosave = self.saveDirectory + filetodownload.rsplit('/', 1)[-1]

            with open(filetosave,'wb') as f:
                f.write(response.content)
            t.sleep(1.5)

            self.as_sendpicture(buddyHandle, filetosave)
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
    def witReq(self, access_token, meth, path, params, body, **kwargs):
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
            data=body,
            **kwargs
        )
        if rsp.status_code > 200:
            self.logger.error(u'Wit responded with status: ' + unicode(rsp.status_code) +
                           ' (' + unicode(rsp.reason)  + ')')
        json = rsp.json()

        if 'error' in json:
            self.logger.error(u'Wit responded with an error: ' + json['error'])

        self.logger.debug('%s %s %s', meth, full_url, json)
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
            self.logger.error(u'Wit responded with status: ' + unicode(rsp.status_code) +
                           ' (' + unicode(rsp.reason)  + ')')
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
        self.logger.debug(u'wit_message: '+unicode(resp))
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
        self.logger.debug(u'wit_speech: '+unicode(resp))

        return resp


    def wit_ThreadCreate(self, valuesDict):
        if self.debugextra:
            self.logger.debug(u'Thread Create Wit.ai App Started..')
        self.myThread = threading.Thread(target=self.witaitesting, args=())
        #self.myThread.daemon = True
        self.myThread.start()

    def wit_Delete(self, valuesDict):

        if self.debugextra:
            self.logger.debug(u'Thread Delete Wit.ai App Started..')

        self.main_access_token = indigo.activePlugin.pluginPrefs.get('main_access_token','')

        if self.main_access_token == '':
            self.access_token = indigo.activePlugin.pluginPrefs.get('access_token','')
        else:
            self.access_token = self.main_access_token

        checkappexists = self.wit_getappid(self.access_token)
        if checkappexists == False:
            self.logger.info(u'No Wit.Ai App appears to exist.')
        else:
            delete_app = self.wit_deleteapp(self.access_token)
            self.logger.debug(unicode(delete_app))

        indigo.activePlugin.pluginPrefs['main_access_token']=''
        indigo.activePlugin.pluginPrefs['app_id']=''
        indigo.server.savePluginPrefs()
        return

    def wit_updateDevices(self, valuesDict):

        if self.debugextra:
            self.logger.debug(u'Wit.Ai Update called')
        if self.main_access_token == '':
            self.access_token = indigo.activePlugin.pluginPrefs.get('access_token','')
        else:
            self.access_token = self.main_access_token

        # check apps
        checkappexists = self.wit_getappid(self.access_token)
        if checkappexists==False or self.access_token=='':
            self.logger.info(u'wit.Ai Application does not seem to exist.  Press Create first before updating')
            return

        array2 = '''{"doc":"Indigo device_name","lookups":["free-text","keywords"],"values":['''
        # array2 = '''{"values":['''
        x = 0
        synomynarray = []


## Push all new names and synomyns
        for device in indigo.devices.itervalues():
            if self.wit_alldevices:
                description = str(device.description)
                if description != '' and description.startswith('witai'):
                    # okay - just grab the first line
                    # self.logger.debug(u'Description: String result found:'+unicode(description))
                    description = description.split('\n', 1)[0]
                    # firstline, now remove witai
                    # self.logger.debug(u'Description: First Line only:'+unicode(description))
                    description = description[6:]
                    # self.logger.debug(u'Description: New Description equals:'+unicode(description))
                    # now break up by seperating on | characters
                    synomynarray = description.split('|')
                    # self.logger.debug(u'Description: Array now equals:'+unicode(synomynarray))

                devicename = str(device.name)
                array2 = array2 + '''{"value":"''' + devicename + '''","expressions":["''' + devicename + '''",'''
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
                    # self.logger.debug(u'Description: String result found:' + unicode(description))
                    description = description.split('\n', 1)[0]
                    # firstline, now remove witai
                    # self.logger.debug(u'Description: First Line only:' + unicode(description))
                    description = description[6:]
                    # self.logger.debug(u'Description: New Description equals:' + unicode(description))
                    # now break up by seperating on | characters
                    synomynarray = description.split('|')
                    # .logger.debug(u'Description: Array now equals:' + unicode(synomynarray))

                    devicename = str(device.name)
                    array2 = array2 + '''{"value":"''' + devicename + '''","expressions":["''' + devicename + '''",'''
                    if synomynarray:  # not empty
                        for synomyn in synomynarray:
                            array2 = array2 + '''"''' + synomyn + '''",'''

                        del synomynarray[:]
                    array2 = array2[:-1]
                    array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''

        array2 = array2[:-1] + ']}'
        # array2 = json.dumps(array2)
        self.logger.debug(unicode(array2))

        params = {}
        params['v'] = '20181110'
        entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name', params, array2)
        self.logger.debug(unicode(entityput))
        t.sleep(10)

        ## send any new samples between versions
        ## Probably pay to run this on first startup....

        base =[]
        array = '''{"text":"Tell me a joke","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Do you know any good jokes?","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Please tell me a funny joke?","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))
        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/samples', '', jsonbase)
        self.logger.debug(unicode(jsonbase))
        self.logger.debug(unicode(replyend))
        x = 0
        del base[:]

        self.logger.info(u'Imessage Plugin:  wit.Ai Device successfully updated.')


    def witaitesting(self):

        if self.debugextra:
            self.logger.debug(u'Wit.Ai Create App called')

        # create new wit.ai app
        self.main_access_token = self.pluginPrefs.get('main_access_token','')

        if self.main_access_token == '':
            self.access_token = indigo.activePlugin.pluginPrefs.get('access_token','')
        else:
            self.access_token = self.main_access_token

        # check apps
        checkappexists = self.wit_getappid(self.access_token)
        if checkappexists==False or self.access_token=='':
            # no app exisits
            # create & get new access_token
            access_token = self.wit_createapp(self.access_token)
            indigo.activePlugin.pluginPrefs['main_access_token'] = self.access_token
            indigo.server.savePluginPrefs()
            self.wit_createentity(self.access_token, 'device_name')
        base =[]
        lookup = '{"lookups":["free-text", "keywords"]}'
        #self.wit_deleteentity(self.access_token,'device_name')
        #self.wit_deleteentity(self.access_token,'intent')
        params = {}
        params['v'] = '20170307'
        entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name', params, lookup)
        self.logger.debug(unicode(entityput))
        t.sleep(15)

        array2 = '''{"doc":"Indigo device_name","lookups":["free-text","keywords"],"values":['''
        #array2 = '''{"values":['''
        x=0
        synomynarray = []

        for device in indigo.devices.itervalues():
            if self.wit_alldevices:
                description = str(device.description)
                if description != '' and description.startswith('witai'):
                    # okay - just grab the first line
                    #self.logger.debug(u'Description: String result found:'+unicode(description))
                    description = description.split('\n',1)[0]
                    # firstline, now remove witai
                    #self.logger.debug(u'Description: First Line only:'+unicode(description))
                    description = description[6:]
                    #self.logger.debug(u'Description: New Description equals:'+unicode(description))
                    # now break up by seperating on | characters
                    synomynarray = description.split('|')
                    #self.logger.debug(u'Description: Array now equals:'+unicode(synomynarray))

                devicename = str(device.name)
                array2 = array2 + '''{"value":"'''+devicename+'''","expressions":["'''+devicename+'''",'''
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
                    #self.logger.debug(u'Description: String result found:' + unicode(description))
                    description = description.split('\n', 1)[0]
                    # firstline, now remove witai
                    #self.logger.debug(u'Description: First Line only:' + unicode(description))
                    description = description[6:]
                    #self.logger.debug(u'Description: New Description equals:' + unicode(description))
                    # now break up by seperating on | characters
                    synomynarray = description.split('|')
                    #.logger.debug(u'Description: Array now equals:' + unicode(synomynarray))

                    devicename = str(device.name)
                    array2 = array2 + '''{"value":"''' + devicename + '''","expressions":["''' + devicename + '''",'''
                    if synomynarray:  # not empty
                        for synomyn in synomynarray:
                            array2 = array2 + '''"''' + synomyn + '''",'''

                        del synomynarray[:]
                    array2 = array2[:-1]
                    array2 = array2 + '''],"metadata" :  "''' + str(device.id) + '''"},'''


        array2 = array2[:-1] + ']}'
        #array2 = json.dumps(array2)
        self.logger.debug(unicode(array2))

        params = {}
        params['v'] = '20181110'
        entityput = self.witReq(self.access_token, 'PUT', '/entities/device_name', params, array2)
        self.logger.debug(unicode(entityput))

        t.sleep(10)

        for device in indigo.devices.itervalues():
            if self.wit_alldevices:
                self.logger.debug(u'Okay - sending all device details to help with parsing...')
                if hasattr(device, "displayStateValRaw") and device.displayStateValRaw in ['0',False,True] :
                    x=x+4
                    devicename = str(device.name)
                    array = '''{"text":"Turn on '''+ devicename +'''","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"'''+devicename+'''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"'''+ devicename +''' on","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"'''+devicename+'''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Turn off '''+ devicename +'''","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"'''+devicename+'''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"'''+ devicename +''' off","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"'''+devicename+'''"}]}'''
                    base.append(json.loads(array))
                if 'temperature' in device.states or 'Temperature' in device.states or device.deviceTypeId=='Temperature' or (hasattr(device, 'subModel') and device.subModel=='Temperature'):
                    x=x+4
                    devicename = str(device.name)
                    array = '''{"text":"What is the temperature of the ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Tell me the temperature of the ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"''' + devicename + ''' temperature? ","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"How hot is ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                if device.pluginId == 'com.GlennNZ.indigoplugin.FindFriendsMini' and device.model =='FindFriends Device':
                    x=x+4
                    devicename = str(device.name)
                    address = device.states['address']
                    array = '''{"text":"Where is ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Locate ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Find the location of ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Find ''' + devicename + ''' whereabouts","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))

                if 'brightnessLevel' in device.states:
                    x = x + 6
                    devicename = str(device.name)
                    array = '''{"text":"Dim ''' + devicename + ''' to 10%","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Set ''' + devicename + ''' to 10% dim","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Dim ''' + devicename + ''' to 60%","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Set ''' + devicename + ''' to 60% brightness","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Set ''' + devicename + ''' to 10% brightness","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                    base.append(json.loads(array))

                if x > 185:
                    jsonbase = json.dumps(base)
                    replyend = self.witReq(self.access_token, 'POST', '/samples', '', jsonbase)
                    self.logger.debug(unicode(jsonbase))
                    self.logger.debug(unicode(replyend))
                    x = 0
                    del base[:]
                    self.sleep(71)
            else:
                description = str(device.description)
                if description != '' and description.startswith('witai'):
                    x = x + 4
                    devicename = str(device.name)
                    array = '''{"text":"Turn on ''' + devicename + '''","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"''' + devicename + ''' on","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"true"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"Turn off ''' + devicename + '''","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))
                    array = '''{"text":"''' + devicename + ''' off","entities":[{"entity":"intent","value":"device_action"},{"entity":"wit$on_off","value":"false"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                    base.append(json.loads(array))

                    if 'temperature' in device.states or 'Temperature' in device.states or device.deviceTypeId=='Temperature' or (hasattr(device, 'subModel') and device.subModel=='Temperature'):
                        x = x + 4
                        devicename = str(device.name)
                        array = '''{"text":"What is the temperature of the ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Tell me the temperature of the ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"''' + devicename + ''' temperature? ","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"How hot is ''' + devicename + '''","entities":[{"entity":"intent","value":"temperature"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                    if device.pluginId == 'com.GlennNZ.indigoplugin.FindFriendsMini' and device.model == 'FindFriends Device':
                        x = x + 4
                        devicename = str(device.name)
                        address = device.states['address']
                        array = '''{"text":"Where is ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Locate ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Find the location of ''' + devicename + '''","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Find ''' + devicename + ''' whereabouts","entities":[{"entity":"intent","value":"location"},{"entity":"device_name","value":"''' + devicename + '''"}]}'''
                        base.append(json.loads(array))

                    if 'brightnessLevel' in device.states:
                        x = x + 6
                        devicename = str(device.name)
                        array = '''{"text":"Dim ''' + devicename + ''' to 10%","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 10% dim","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Dim ''' + devicename + ''' to 60%","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 60% brightness","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"60"}]}'''
                        base.append(json.loads(array))
                        array = '''{"text":"Set ''' + devicename + ''' to 10% brightness","entities":[{"entity":"intent","value":"dim_set"},{"entity":"device_name","value":"''' + devicename + '''"},{"entity":"wit$number","value":"10"}]}'''
                        base.append(json.loads(array))

                if x > 185:
                    jsonbase = json.dumps(base)
                    replyend = self.witReq(self.access_token, 'POST', '/samples', '', jsonbase)
                    self.logger.debug(unicode(jsonbase))
                    self.logger.debug(unicode(replyend))
                    x = 0
                    del base[:]
                    self.sleep(71)

        # and load again at end in case never make it to 195 samples
        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/samples', '', jsonbase)
        self.logger.debug(unicode(jsonbase))
        self.logger.debug(unicode(replyend))
        x = 0
        del base[:]
        self.sleep(71)

        ## manual samples here
        array = '''{"text":"Tell me a joke","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Do you know any good jokes?","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Please tell me a funny joke?","entities":[{"entity":"intent","value":"joke"}]}'''
        base.append(json.loads(array))

        array = '''{"text":"Can you give me some advice","entities":[{"entity":"intent","value":"advice"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Do you have any advice for me?","entities":[{"entity":"intent","value":"advice"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Can you help with some advice?","entities":[{"entity":"intent","value":"advice"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"What should I do?","entities":[{"entity":"intent","value":"advice"}]}'''
        base.append(json.loads(array))

        array = '''{"text":"Hello","entities":[{"entity":"intent","value":"greeting"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Hi, how are you?","entities":[{"entity":"intent","value":"greeting"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"What is up?","entities":[{"entity":"intent","value":"greeting"}]}'''
        base.append(json.loads(array))

        array = '''{"text":"Should I value you opinion?","entities":[{"entity":"intent","value":"yes_no_decision"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Shall I or Shall I not?","entities":[{"entity":"intent","value":"yes_no_decision"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Should I do it?","entities":[{"entity":"intent","value":"yes_no_decision"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Should I really do this?","entities":[{"entity":"intent","value":"yes_no_decision"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"What do you suggest? Yes or No?","entities":[{"entity":"intent","value":"yes_no_decision"}]}'''
        base.append(json.loads(array))

        array = '''{"text":"Piss off you idiot","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Fuck off","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Go away","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"Fuck you with bells on","entities":[{"entity":"intent","value":"insult"},{"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"You are useless!","entities":[{"entity":"intent","value":"insult"}, {"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))
        array = '''{"text":"You are tosser!","entities":[{"entity":"intent","value":"insult"}, {"entity":"wit$sentiment","value":"negative"}]}'''
        base.append(json.loads(array))

        jsonbase = json.dumps(base)
        replyend = self.witReq(self.access_token, 'POST', '/samples', '', jsonbase)
        self.logger.debug(unicode(jsonbase))
        self.logger.debug(unicode(replyend))
        x = 0
        del base[:]
        self.sleep(71)

        self.logger.error(u'Indigo iMessage wit.ai Application Created Successfully.')

    def wit_deleteapp(self, access_token):

        if self.debugextra:
            self.logger.debug(u'Delete New Wit.Ai App')
        params = {}
        params['v'] = '20181110'
        deletenewapp = self.witReq(access_token, 'DELETE','/apps/'+self.app_id, params, '')
        self.logger.debug(u'Reply Delete App:'+unicode(deletenewapp))
        #reply_dict = json.loads(createnewapp)
        if deletenewapp.get('success')==True:
            self.logger.info(u'Wit.Ai Indigo-iMessage App Deleted')

    def wit_createapp(self, access_token):

        if self.debugextra:
            self.logger.debug(u'Create New Wit.Ai App')
        params = {}
        params['v'] = '20181110'
        array = '''{"name":"Indigo-iMessage", "lang":"en","private":"true"}'''
        createnewapp = self.witReq(access_token, 'POST','/apps',params, array)
        self.logger.debug(u'Reply Create App:'+unicode(createnewapp))

        #reply_dict = json.loads(createnewapp)

        self.access_token= createnewapp.get('access_token')
        self.main_access_token = createnewapp.get('access_token')
        self.app_id = createnewapp.get('app_id')

        indigo.activePlugin.pluginPrefs['main_access_token'] = createnewapp.get('access_token')
        indigo.activePlugin.pluginPrefs['app_id']= self.app_id
        indigo.server.savePluginPrefs()

        self.logger.error(u'New Access Token Equals:'+unicode(self.access_token))
        return createnewapp.get('access_token')

    def wit_getappid(self, access_token):
# finds app and get app.id
# returns True if app exists and self.appid is set
# return False if no such app found

        if self.debugextra:
            self.logger.debug(u'Get App Id ')
        params = {}
        params['v'] = '20181110'
        params['limit'] = '100'
        #array = '''{"name":"Indigo-iMessage", "lang":"en","private":"true"}'''
        getapp = self.witReq(access_token, 'GET','/apps',params, '')
        self.logger.debug(u'Get Apps:'+unicode(getapp))

        for i in getapp:
            if i['name']== 'Indigo-iMessage':
                self.logger.debug(u'Found App:'+i['name'])
                self.logger.debug(u'Found App ID:'+i['id'])
                self.app_id = i['id']
                indigo.activePlugin.pluginPrefs['app_id']=self.app_id
                indigo.server.savePluginPrefs()
                return True
        return False


    def wit_createentity(self, access_token, entity):
        if self.debugextra:
            self.logger.debug(u'Create New Entity')
        params = {}
        params['v'] = '20181110'
        array = '''{"doc":"Indigo '''+entity+'''", "id":"'''+entity+'''"}'''
        self.logger.debug(u'New Entity Created:'+unicode(array))
        createnewentity = self.witReq(access_token, 'POST','/entities', params, array)
        self.logger.debug(u'Reply Create Entity:' + unicode(createnewentity))
        return

    def wit_deleteentity(self, access_token, entity):
        if self.debugextra:
            self.logger.debug(u'Create New Entity')
        params = {}
        params['v'] = '20181110'
        #array = '''{"doc":"Indigo Device Name", "id":"device_name"}'''
        self.logger.debug(u'New Entity Deleted:'+unicode(entity))
        deletenewentity = self.witReq(access_token, 'DELETE','/entities/'+entity, params, '')
        self.logger.debug(u'Reply Delete Entity:' + unicode(deletenewentity))
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
            for triggerId, trigger in sorted(self.triggers.iteritems()):
                self.logger.info(u"{0:<30} {1}".format("Triggers:", trigger.pluginTypeId +'  :  '+ trigger.name))
        self.logger.info(u"{0:<30} {1}".format("Awaiting Confirmation:", self.awaitingConfirmation))
        self.logger.info(u"{0:<30} {1}".format("Reset Last Command:", self.resetLastCommand))

        self.logger.info(u"{0:<30} {1}".format("Backup Directory:", self.backupfilename))
        self.logger.info(u"{0:<30} {1}".format("SQL Database Location:", self.filename))
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
            self.logger.debug('triggerCheck run.  triggertype:'+unicode(triggertype))

        Triggered = False

        imsgcmdreceived = re.sub(r'([^a-zA-Z ]+?)', '', imsgcmdreceived)
        if self.debugtriggers:
            self.logger.debug(u'Removed extra characters from cmd received:'+imsgcmdreceived)

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
                        Triggered = True
                if trigger.pluginTypeId == "specificBuddycommandReceived" and triggertype == 'commandReceived':
                    if self.debugtriggers:
                        self.logger.debug(u'Trigger PluginProps: Specific CommandCalled:'+unicode(trigger.pluginProps['commandCalled']))
                    if buddy in trigger.pluginProps['buddyId']:  # checking buddy in list of options
                        if self.debugtriggers:
                            self.logger.debug(u'Buddy Found:'+unicode(buddy)+' and Buddy in allowed list for trigger:'+unicode(trigger.pluginProps['buddyId'])+' Specific Command Called:' + unicode(trigger.pluginProps['commandCalled']))
                        indigo.trigger.execute(trigger)
                        Triggered = True

            return Triggered

        except:
            if self.debugexceptions:
                self.logger.exception(u'Exception within Trigger Check:')
            if self.debugextra:
                self.logger.debug(u'Exception within Trigger Check')
            return False

