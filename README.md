Indigo Imessage Plugin

Parse and send iMsg
Works with Mojave
Beta currently
Will need to change System Permissions to access imsg database file

Basics:

Mojave tested
Indigo 7.2
Signed into iMsg with ideally separate indigo account


So far

Connects to chat.db via sql and parse messages received
Need to set allowed Buddies in Plugin Config

To setup Commands

Create Trigger for iMsg Plugin
Edit the Command Recevied
Then can create any indigo action passed on the command recevied.
eg.
All off
Gate Open
Lock House
Alarm on

Two current actions
- send Imsg and send iMsgFile
Allow to send imsg to any buddy you know
Tick box - to send reply to last buddy received message from enabling ongoing discussion

send iMsgFile
- sends file/image/animated gif to buddy 
(again has tickbox for last buddy)


#todo

- Have some logic triggers Yes / No and returns a condition response - enabling you to ask questions
'Do you want the Gate opened?'  etc and waits for affirmative before triggering.




