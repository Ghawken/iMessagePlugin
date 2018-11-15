# Indigo iMessage Plugin

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/icon.png?raw=true)

What it can do:

- Parse and send iMessages from within Indigo
- Send Animated GIFs/pdf files etc from within Indigo
- Works with Mojave, untested on below versions - but shouldn't be issue
- Indigo 7.1 and above
- Beta currently:
    - Additionally with 0.2.2 Natural Language processing and ability to interface with all or selected Indigo Devices
    - Uses Wit.Ai NLP
    - See 0.2.2 for details

For Mojave will need to change System Permissions to access imsg database file

## Basics

- Mojave tested
- Indigo 7.2
- Need to be signed into Messages/iMsg on Indigo Mac with ideally separate indigo account
- Will very likely need to give Indigo and IndigoPluginHost.app and IndigoServer.app Full Disk Access in the Security and Privacy settings

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/SecurityScreen.png?raw=true)


**/Library/Application Support/Perceptive Automation/Indigo 7 (or 7.2)**

IndigoPluginHost.app

IndigoServer.app

Both located there to drag and drop into Security & Privacy Full Disk Access


(sorry - don't believe any way around this - and probably needed for other plugins)

See here:

https://www.macworld.com/article/3311982/macs/the-difference-between-accessibility-and-full-disk-access.html


## Installation

- Download latest release and enable
- Go to plugin Config screen to set allowed Buddies...

- If hard to find out Buddy Handle (sometimes email, sometimes phone) enable Config checkbox 'Show Buddy Handle in Log'.  Send indigo Mac and iMsg if all is functioning correctly, the Plugin will highlight for you the correct Buddy Handle to use in the Plugin Config and the send iMessage boxes as required.

- Any issues turn debug logging on and check 3 checkboxes - should supply useful information
(including Buddy Handles as sometimes email sometimes phone numbers.)

![](https://github.com/Ghawken/iMessagePlugin/blob/wit.ai/DocumentPics/PluginConfigScreen.png?raw=true)

## Works

- Connects to iMessage chat.db via sql and parse messages received via regular simple, read-only SQL command
- At first run will backup the iMsg database to Users/Documents file - just in case... (haven't had any issues)
- Checks every few seconds - so far no problems in my testing
- Need to set allowed Buddies in Plugin Config otherwise any received iMsg will be ignored
- No Indigo devices needed - works solely through triggers and action 

## Setup Commands Recognised

- Enables you to recognise any iMsg received from Buddy as something to act on
- No formatting of message
- Just simple whole text 

Felt best to use Indigo itself for actions with Triggers being the message itself - means very familiar

Create Separate Indigo Triggers for iMsg Plugin for each command want recognised

### Via individual Trigger for each iMessage text wish to action on


eg. this an Indigo Trigger
![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/TriggerEg.png?raw=true)

Type of trigger is IMessage Plugin Event, Command Received

Edit the command Received, then standard indigo conditions and actions performed.

Then can create any indigo action passed on the command received, including a iMsg reply to confirm.

eg.  One Indigo Action from same Trigger

![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/TriggerAction.png?raw=true)


Example Commands (any text you wish can be a trigger)
- All off
- Gate Open
- Lock House
- Alarm on


### New from 0.2.4

Add Specific Buddy Command Trigger: 

Multiple Buddies can be selected and will only trigger if Buddy selected 


![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/TriggerSpecificBuddyCommand.png)



## Three current Plugin Actions

### Send Imsg 

- Allow to send imsg text to any buddy you know
- Tick box - to send reply to last buddy received message from enabling ongoing conversation
- Allows variable and device state substitution
- So can send message:
 - 'Glenn is located %%d:1490780461:address%% and has about %%d:1490780461:homeTimeText%% to travel to get home'
& clever indigo will fill in the blanks

### Send iMsgFile/iMsgImage
- sends file/image/animated gif to buddy 
(again has tickbox for last buddy)
- Allows sending Animated Gifs via BlueIris or other Security plugin.
- Just need path to file location,or %%v:112312%% Variable substition and save to path
- eg.
The BlueIris lastAnimGif path variable which is updated by BlueIris plugin when AnimatedGif created.

### Send iMsgMessgae and file
- sends a message with an associated file/image/animated gif to buddy 
(again has tickbox for last buddy)
- Allows sending Animated Gifs via BlueIris or other Security plugin.
- Just need path to file location,or %%v:112312%% Variable substition and save to path
- eg.
The BlueIris lastAnimGif path variable which is updated by BlueIris plugin when AnimatedGif created.

### Ask iMsg Question
![](https://github.com/Ghawken/iMessagePlugin/blob/master/DocumentPics/AskiMsgQuestion.png?raw=true)


 - Sends a question to Buddy - waits the timeout period for a positive or negative response
 - If timeout sends a timeout reply
 - If confirmation received - then runs the specified action group

- Following are valid confirmation replies - anything else will be ignored, OR if matches trigger acted on whilst waiting.

 valid = {"yes": True, "y": True, "ye": True, 'yeah':True, 'ok':True,  "no": False, "n": False, 'nope':False, 'never':False}

Sorry only english currently - but easy to add as many confirmation 'Oui' 'Non' that anyone needs down the track.

- Also allows - for specified reply (%%V:112123%%) substitution allowed

## Additional

### Messages accept indigo substitution for both variables and devices.

- So can send message:
'Glenn is located %%d:1490780461:address%% and has about %%d:1490780461:homeTimeText%% to travel to get home'

- with Number referring to FindFriends Device:
Indigo will substitute both the address and the travel time in these places.


# Beta Functions: From Version 0.2.2

As a mechanism of controlling all indigo devices and requesting information with minimal setup I have turned to a free service wit.ai

![](http://ectolus.com/wp-content/uploads/2017/06/WITAI.png)

The aim of this internet service is to process any text messages you might send and enable the Plugin to reply, recognising what you want to do but also which device to apply this to.

e.g
Aiming to bring to life.. the following with minimal setup.

- Turn off pool Pump.
- Dim the living room light to 20%
- Set Living Room light to 100% brightness
- What is the temperature in Maxs Room?
- Tell me a joke?
- What is the temperature of the pool?
- Can you help with some advice?
- How hot is the Living Room?
- What is Glenn's Location?

It also enables speech->text via audioMessage, and a few fun extras perhaps I got carried away with.

Basically Wit.ai - recognises message:
 **intent**, currently options: device_action, insult, yes_no_decision, joke, dim_set, temperature, advice
& **entities** such as device_name (which is Indigo Device), plus others such as number/sentiment/on_off etc.
This parsed result is sent back to the plugin to action. (very quickly)

So if message is sent *'Please Indigo could you be a dear and turn on the living room light?'*

The (Plugin after suitable wit.ai training/samples) should recognise **intent**: *device_action*, **device_name**:*'Living Room light'*, and **on_off** = *on*

The plugin parses the reply and then Turns on living room light for example.

Within Wit.ai you can train any sentence structure to the correct intent and result.  The aim is for the plugin to probably do this at Wit.ai app creation which is what currently happens, obviously others may speak in a different manner. :roll: and I can add any samples/sentence structures wished.


**Consider this beta - BUT if disable wit.ai in PluginConfig - rest of plugin unchanged and none of this is run**

## Requirements:

Need your own Wit.Ai API Key (free)
We each need our own as our devices are named something different
So while the NLP logic may be the same the devices referred to will be different.

## Setup:

### New Plugin Config Settings

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/PluginConfigScreen.png)


1. Create Wit.AI Api
- Log in to, with either github or facebook.

https://wit.ai

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/wit.aiWebPage.png)


2/ Next Go to the already existing App called 'MyFirstApp'
- Go to Settings, top Right
- Find the 'Server Access Token' and copy this in the PluginConfig

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/WitAIAccess_token.png)


Enable Use Wit.Ai Processing to use this service for processing of Messages received.

Checkbox:
## Use all Indigo Devices  (important)

- This will send every indigo device name to Wit.Ai to be recognised as a device down the track.
- This is fine if you have limited devices and the names make sense.
- But if like me you have hundreds will names like (U) Computer Room Light, or PiBeacon_Pool Temperature
- These names make sending a text message 'what is the PBeacon_Pool Temperature' will work but isn't much fun.

- I have added the ability for WitAI to recognise synomyns for the same device 
- eg. device is PiBeacon_Pool Temperature, other names can be 'Pool Temp', 'Pool Temperature' or even 'Pool'

This is performed via the individual Device Notes:  
On the first line of the notes (the other lines are ignored)
a :

```witai|Pool|Pool Temp|Pool Temperature```

- Must start with witai and then Vertical bar Characters seperating names 
- Sorry the character is the | Vertical Bar Character

eg.

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/witai_Example_device.png)


- This will give different names which refer to the same device for all future commands

### Coming back to the Checkbox - if this is unchecked only those devices so marked with witai| in device notes will be included.

Okay:

So ideally - give you funny named devices some better names, mark those you want to send, or send all

## Then:

1. Press the Button called 'Generate Wit.Ai App'  [once we are dne only need to do this once]

This will send a whole lot of text based data to Wit.ai naming devices, and setting up you wit.ai device which the plugin uses
You can access this online at wit.ai if needed but really only for finetuning.

This will take a while as can only send a few devices/samples at once; so will take at least 5 if not 10 minutes to be done.
Once finished also takes a while at Wit.Ai end as well - before everything is recognised probably - probably at least 1/2 hou

If any issues or want to resend different devices following some playing - press the delete wit.ai App button and then recreate after a short pause.


Following this
- You should be able to 'turn on INDIGODEVICE', 'turn off INDIGODEVICE',  'set INDIGODEVICE brightness to 50%',
- 'What is the Temperature of INDIGODEVICE',
- 'Tell me a joke'
- 'What is  IFRIENDEVICE location'
-  amongst others

I have also added AudioMessage Uploading - which works okay within limits of speech recognition.
From within iMSG press and hole down microphone - say command and viola!

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/record-audio-message-ios.jpg)


### Fine Tuning:

- Probably more to come I suspect.
- From within Wit.ai - can go to Inbox and validate audio received for training
- Can also can to device_name and add any extra synomyms for this device you wish - pays to do it in Indigo Notes though/so survices delete and recreate

### Other changes:
- Add send HTTP Image - takes http/web location downloads fine and sends it to buddy.




## Changelog:

### 0.2.4
Changes to PluginConfig - hide the scary wit.ai stuff if not using
Allow Wit.ai device to be updated with app - update button
Update Images Documentation

### 0.2.3
Add Specific Buddy Command Received Trigger:

![](https://raw.githubusercontent.com/Ghawken/iMessagePlugin/wit.ai/DocumentPics/TriggerSpecificBuddyCommand.png)


Potential bug fix as will Continue checking triggers even if one is triggered (might be multiple triggers same)



.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.
.


































### Python Script Control (if needed for full flexibility)

- Via a Python script you can access the Plugin actions to send and reply to Imsgs.
- So can via script create question and send via the following standard message. 
```
    imessageID = 'com.GlennNZ.indigoplugin.iMessage'
    imsgPlugin = indigo.server.getPlugin(imessageID)
    imsgPlugin.executeAction('sendQuestion', props={'message':'The question you wish to ask', 'buddyId':'example@email.com', 'lastBuddy':False, 'timeout':600,'confirmedimsg':'All done.','actiongroup':ActionGroupIDtoRunwhenConfirmed})
    return;
```

Props to send:
- message: the question to ask
- buddyId: the buddy handle
- lastBuddy: just the last buddy msg received from 
- timeout : timeout in seconds
- confirmedimsg: message if confirmation is received
- actiongroup:  the ID number of the action group to run if confirmed.

Here is an example script that list devices on  (via allowed list, and notallowed list), saves this list to a variable and then sends message listing devices on, via the plugin waits for confirmation,  before running the confirmation AG to turn off all listed in variable.


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




