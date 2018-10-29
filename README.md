# Indigo iMessage Plugin

Parse and send iMsg
Works with Mojave
Beta currently
Will need to change System Permissions to access imsg database file

## Basics:

Mojave tested
Indigo 7.2
Signed into iMsg with ideally separate indigo account
Will very likely need to give Indigo and IndigoPluginHost.app and IndigoServer.app
Full Disk Access in the Security and Privacy settings
(sorry - don't believe any way around this)

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

### Ask iMsg QUestion
 Sends question to Buddy - waits the timeout period for response
 If timeout sends a timeout reply
 If confirmation received - then runs the specified action group
 Send specified reply (%%V:112123%%) substitution allowed

#todo

- Have some logic triggers 
Yes / No and returns a condition response - enabling you to ask questions
'Do you want the Gate opened?'  etc and waits for affirmative before triggering.
Still thinking this through



