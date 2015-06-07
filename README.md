i
# What is GTKZabbix?

GTKZabbix is a Python program aiming to bring Zabbix to the Linux desktop. The objective is to have the alerts right on your screen, with visual and sound notifications. This is what Zabbix Web Gui does with an Internet browser but with little desktop integration. I want to change this.

#Who is the author?

Me! My name is Jordi Clariana, I'm from Barcelona, Spain, and I work in a well known (at least in Spain) Internet based company. I'm a Linux System Administrator, and I have some ideas of programming, but I'm not a programmer. A good programmer will notice it at first glance to the code ;). But what I want is not to do a pretty code, but a code that works.

#What do I need to make it work?

A Linux system with a graphical desktop. It can work with any desktop interface as long it work with GTK. I have tested myself with XFCE and GNome. I don't know if it can work with Unity. Additionally, you will need Python and GTKPython libraries. Python is installed in most Linux systems by default and I think GTK modules are as well. Maybe you will have to install some additional Python modules, like python-gst or python-glade2. Anyway, it will be notified by the program when a module is not found.

#How do I get it work with my Zabbix server?

First of all you have to ensure that the Zabbix web is accessible to the program, and that the user you are going to use has granted API access. You can change it in the "Administration" -> "Users" -> "User Groups". Ensure your user group have "Enabled" in the "API access" column.

#I want to configure GTKZabbix to connect to my server!

Yes, yes, I know. That's what I was talking about. Launch the program, and go to the "Settings" menu on the Indicator (usually at the top right, you should see a white "Z" there). Click on "Add Server" and fill the fields as this:

- Server Alias: My Favorite Zabbix Server
- Server Uri: http://zabbix.mydomain.com/zabbix (this have to be the same URL you use to access to your current Zabbix server Web)
- Username: zabbixapi (or whatever your zabbix user is called, but with API permissions, remember!)
- Password: supersecr3t?
- Enabled: I encourage you to have this checked :P

And now click "Save".

That's all, GTKZabbix will begin to collect triggers from your Zabbix Web Server.

#What the hell is "Control Room Mode"?

Well, this is a feature that a workmate of mine asked for, and I really didn't know how to call it :) What "Control Room Mode" does is turn off the display when there are no Zabbix alerts. This is intended to save energy, and is useful when you have a screen only for the program (as I have, by the way, and it has been running several months without any problem, so far).

#What really ACK does?

It does not ACK on the Zabbix Server if that what you were expecting. It just checks the ACK locally in order to stop the trigger from blinking and beeping in the dashboard.

#I have more questions!
Bufff... really? Well, use the Github issues page :)

