# Indigo iMessage Plugin

Parse and send iMsg
Works with Mojave
Beta currently
Will need to change System Permissions to access imsg database file

## Basics:

Mojave tested
Indigo 7.2
Signed into Messages/iMsg on Mac with ideally separate indigo account
Will very likely need to give Indigo and IndigoPluginHost.app and IndigoServer.app
Full Disk Access in the Security and Privacy settings

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

#todo

- Have some logic triggers 
Yes / No and returns a condition response - enabling you to ask questions
'Do you want the Gate opened?'  etc and waits for affirmative before triggering.
Still thinking this through



