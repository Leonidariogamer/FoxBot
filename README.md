# FoxBot Source Code

The Source code of the bot that probably no one waited

if you want to invite the bot and not do allat [Click Here]( https://discord.com/oauth2/authorize?client_id=1020262027224166451&scope=bot&permissions=8).

# Overview
Discord Bot is a customizable bot built with the Discord.py library, providing various features including moderation commands, utility functions, and fun commands. The bot offers a rich set of commands to help manage your server, including issuing warnings, banning users, fetching fun posts from e621.net, and more. Additionally, the bot includes a custom help command displayed in a categorized, user-friendly embed.

# Features:
Moderation: Issue warnings, ban, kick, timeout, and manage user infractions.
Utility Commands: Snipe deleted messages, translate text, and more.
Fun Commands: Fetch random posts from e621.net and steal emojis or stickers.
Custom Help: A neatly organized help command that categorizes commands into different sections.
Rich Presence: Displays custom bot status with the number of servers it is helping in, including optional streaming presence. (currently setup to cringe people with a button to KSI - Thick of it)
Features Breakdown:
Moderation Commands:

!warn <user> <reason>: Warn a member with a reason.
!unwarn <user> <warning_id>: Remove a specific warning based on the warning ID.
!ban <user> <reason>: Ban a user from the server.
!kick <user> <reason>: Kick a user from the server.
!timeout <user> <duration>: Temporarily timeout a user.
!untimeout <user>: Remove timeout from a user.
Utility Commands:

!snipe - Retrieve the last deleted message.
!translate <text> - Translate a message to English.
!help - Display this help message.
!server_settings - Lets you either set a safe tag on e621 for all non NSFW channels and the ability to disable bot announcements
!steal - Steal stickers and emojis from other servers

# SETUP

If you dont want the original bot and instead want to install it on your own you can just install the source code and have the following:

**MariaDB**

**Python3**

**requirments.txt**

# INSTRUCTIONS

It would be reccomended to host both the bot and the Database on a server doesnt matter if its a different server **(as long as you know what your are doing)**

# Ubuntu Server

## First install python3 and MariaDB

### Python3

```sudo apt update```

```sudo apt install python3```

```sudo apt install python3-pip```

```sudo apt install python-venv```

### MariaDB
```sudo apt install mariadb-server```

```sudo mysql_secure_installation```

Now you need to make a database

```sudo mariaDB```

```DATABASE CREATE <your database name(Remember than name for later)>```

```CREATE USER 'USER'@'localhost' IDENTIFIED BY 'yourpassword';```

```GRANT ALL PRIVILEGES ON <your database name>.* TO 'LINK'@'localhost';```

```FLUSH PRIVILAGES```

Create the tables for the database

```USE <your database name>```

Settings table

    CREATE TABLE settings (

    guild_id BIGINT PRIMARY KEY,

    e621_safe_mode BOOLEAN DEFAULT FALSE,

    broadcast_enabled BOOLEAN DEFAULT TRUE

    );

Warnings database

    CREATE TABLE IF NOT EXISTS warnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    reason VARCHAR(255),  
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );

exit from mariaDB

```EXIT```

###Head into the ```Database.py``` and edit the login info of the database to the one you set up

```conn = mariadb.connect(```
    
```user="USER",```
    
```password="yourpassword",```
    
```host="localhost",```(if its on the same server)```
    
```port=3306,```(default port for mariaDB)```
    
```database="<your database name>"```

```)```

> [!WARNING]
> Dont copy this code in instead just fill in with the stuff theres already on ```Database.py```.


### Now make a virtual environment

```python3 -m venv myenv```

And enter it

```source myenv/bin/activate```

Assuming that you are in the same directory as where you extracted the file you will need to do

```pip install -r requirments.txt```

And finally if you setup your database correctly

```python3 -u main.py```

> [!NOTE]
> I will probably not post a Windows setup since i dont know how to use windows version of MariaDB but if you really want if you ignore most ubuntu commands and just install everything
