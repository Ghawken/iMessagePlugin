# Indigo iMessage Plugin

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/icon.png?raw=true)

What it can do:

Parse and send iMessages from within Indigo
Send Animated GIFs/pdf files etc from within Indigo

Works with Mojave, untested on below - but shouldn't be issue
Indigo 7.1 and above

Beta currently

For Mojave will need to change System Permissions to access imsg database file

## Basics:

Mojave tested
Indigo 7.2
Need to be signed into Messages/iMsg on Indigo Mac with ideally separate indigo account
Will very likely need to give Indigo and IndigoPluginHost.app and IndigoServer.app Full Disk Access in the Security and Privacy settings

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/SecurityScreen.png?raw=true)


(sorry - don't believe any way around this - and probably needed for other plugins)

See here:
https://www.macworld.com/article/3311982/macs/the-difference-between-accessibility-and-full-disk-access.html


Install

Go to plugin Config screen to set allowed Buddies...
Any questions turn debug logging on and check 3 checkboxes - should supply useful information
(including Buddy Handles as sometimes email sometimes phone numbers.)

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/PluginConfigScreen.png?raw=true)

## So far

Connects to chat.db via sql and parse messages received
Checks every few seconds - so far no problems in my testing
Need to set allowed Buddies in Plugin Config
No devices needed.

## Setup Commands Recognised

Enables you to recognise any iMsg received from Buddy as something to act on
No formatting of message
Just simple whole text recognisation
Felt best to use Indigo itself for actions with Triggers

Create Separate Triggers for iMsg Plugin for each command want recognised

Edit the Command Received
Then can create any indigo action passed on the command recevied.
eg.
All off
Gate Open
Lock House
Alarm on

## Two current actions

### Send Imsg 

Allow to send imsg text to any buddy you know
Tick box - to send reply to last buddy received message from enabling ongoing discussion
Allows variable and device state substitution

### Send iMsgFile
- sends file/image/animated gif to buddy 
(again has tickbox for last buddy)

### Ask iMsg Question
![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/AskiMsgQuestion.png?raw=true)


 Sends question to Buddy - waits the timeout period for response
 If timeout sends a timeout reply
 If confirmation received - then runs the specified action group
 Send specified reply (%%V:112123%%) substitution allowed

## Additional

Messages accept indigo substitution for both variables and devices.

So can send message:
'Glenn is located %%d:1490780461:address%% and has about %%d:1490780461:homeTimeText%% to travel to get home'

with Number referring to FindFriends Device:
Indigo will substitute both the address and the travel time in these places.



## Python Script Control (if needed for full flexibility)

Via a Python script you can access the Plugin actions to send and reply to Imsgs.
So can via script create question and send via the following standard message. 
```
    imessageID = 'com.GlennNZ.indigoplugin.iMessage'
    imsgPlugin = indigo.server.getPlugin(imessageID)
    imsgPlugin.executeAction('sendQuestion', props={'message':'The question you wish to ask', 'buddyId':'example@email.com', 'lastBuddy':False, 'timeout':600,'confirmedimsg':'All done.','actiongroup':AGtoRun})
    return;
```

Here is an example script that list devices on, saves this list to a variable and then sends message, via the plugin waiting for confirmation,  before running the confirmation AG to turn off all listed in variable.


```
on_name = []
on_id = []

def AskQuestionGlenn(question, AGtoRun, replyifsuccess) :
    
    imessageID = 'com.GlennNZ.indigoplugin.iMessage'
    imsgPlugin = indigo.server.getPlugin(imessageID)
    imsgPlugin.executeAction('sendQuestion', props={'message':question, 'buddyId':'example@.com', 'lastBuddy':False, 'timeout':600,'confirmedimsg':replyifsuccess,'actiongroup':AGtoRun})
    return;

def CheckModulesRunning() :
    acceptable_modules = ["Smart Switch (DSC24)","RGBW LED Bulb (ZW098)","Smart Energy Switch (DSC24-2E)","Dimmer Switch (FGD211)","Smart Energy Illuminator (DSC08101)",                     "Relay Power Switch","Smart Energy Switch (DSC06106)", "Double Relay Switch (FGS221)", "Hue Bulb (Original, Downlight, Spotlight, LightStrip Plus)" ]

    notallowedid = [1049034630, 879903489, 1732408457, 1618015973,1595081762,660021281,1509636685,90390894,1047676499,614856779,1373207126,1332040796,1797065670]

    dev_list = indigo.devices.iter()
    for x in dev_list:
        if hasattr(x, "displayStateValRaw") and x.displayStateValRaw not in ["off", 0] and x.model in acceptable_modules and x.id not in notallowedid :
            on_name.append(x.name)
            on_id.append(x.id)
    return;

CheckModulesRunning();

numberon = len(on_id)

if numberon == 0 :
    indigo.server.log("Checking Running devices - None found on.")

if numberon > 0 :
    indigo.server.log("Checking Running devices - Modules running - iMsg sent")
    Question = "Attention\n I have noticed that you are both away and \nThe following lights/devices are on \n"
    ListModules = " , ".join(on_name)
    idsoff = indigo.variables[1410863016] # "MsgOnDevices"
    indigo.variable.updateValue(idsoff, unicode(on_id))
    Statement = Question + ListModules + "\n Would you like me to turn them off?"
    AskQuestionGlenn(Statement, 95680424, "They have all been turned off");
    
```

and for completeness here is the Action Group that is called when above is run
```
onid = indigo.variables[1410863016] # "MsgOnDevices"

onidstring = onid.value
onidstring = onidstring.replace("[","")
onidstring = onidstring.replace("]","")  # Covert indigo string variable back to list
onidstring = onidstring.replace(" ","")

if len(onidstring) > 1:
    onidlist = onidstring.split(",")
else:
    onidlist = onidstring


if len(onidlist) >= 1 :
    indigo.server.log("iMsg: Turning off All Devices ")
    indigo.server.log(unicode(onidstring))
    for i in range(len(onidlist)):
	    indigo.device.turnOff(int(onidlist[i]))
elif len(onidlist) < 1 :
    indigo.server.log("iMsg: No Devices On ")  
```




