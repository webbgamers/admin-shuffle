# Admin Shuffle
This is a Discord bot that will periodically rotate who is admin. After a configurable amount of time, the bot will reset permissions on all roles, remove existing admins, and add new ones.

## Official Server
There is a server that this bot runs on [here](https://discord.gg/mYgh94r3pm). This invite link may break if someone gets admin and deletes it, theres not much I can do about that.

## Official Hosted Bot
For whatever reason if you want to run your own experiment you can invite the [official hosted bot](https://discord.com/oauth2/authorize?client_id=839562104696602644&scope=bot&permissions=8589934579). Once you have invited it, see the [setup instructions](#bot-setup) for how to get it running.
The hosted bot should be running 24/7 but I cannot guarantee that.

## Self Hosting with Docker (Reccomended)
Running using Docker is extremely easy and only requires Docker to be installed. If you don't know what Docker is, check out [their website](https://www.docker.com/).
### Prerequisites
#### Windows/Mac
* [Docker Desktop](https://www.docker.com/products/docker-desktop)
#### Linux
* `docker` or `docker.io` package
### Instructions
* Clone or download this repo to wherever you want.
* Create a bot account in [the Discord developer portal](https://discord.com/developers) and copy it's token. For help creating a bot account see [this article](https://discordpy.readthedocs.io/en/latest/discord.html).
* In the developer portal, enable the servers member intent.
* In the cloned repository, create a file named `token` and copy the bot token into it.
* Open a shell in the cloned repository and run `docker build -t admin-shuffle .` to build the image.
* Run the command `sudo docker run -d --restart unless-stopped -v admin-shuffle-data:/admin-shuffle/data admin-shuffle` to run the image and set it to restart automatically.
* You can generate an invite for the bot using the application ID on the developer portal and [this website](https://discordapi.com/permissions.html).

## Self Hosting without Docker
Docker is not required to run the bot, it just makes things easier and more secure. The first steps are the same as with using Docker.
### Prerequisites
* [Python 3.8](https://www.python.org/downloads/release/python-3810/) (Newer versions of Python will probably work, I just have not tested them.)
### Instructions
* Clone or download this repo to wherever you want.
* Create a bot account in [the Discord developer portal](https://discord.com/developers) and copy it's token. For help creating a bot account see [this article](https://discordpy.readthedocs.io/en/latest/discord.html).
* In the developer portal, enable the servers member intent.
* In the cloned repository, create a file named `token` and copy the bot token into it.
* It is reccomended to make a virtual environment with `python -m venv .venv` but it is not required. If you do, be sure to activate it using `./.venv/Scripts/activate.bat` on Windows or `source .venv/bin/activate` on Linux or MacOS before running the following commands.
* Install dependencies by running `pip install -r requirements.txt`.
* Run the bot with the command `python Bot.py`.
* If you want to have the bot restart automatically, it will depend on the platform, but on Windows you can set the contents of a folder to start automatically using Win+R and typing `shell:startup`. You would probably want to create a bat script that launches the bot (be sure to use the Python binary in the virtual environment if you are using one). On Linux and MacOS you can create a daemon file and tell your init system to launch it automatically.
* You can generate an invite for the bot using the application ID on the developer portal and [this website](https://discordapi.com/permissions.html).

## Bot Setup
* Once you have added the bot to your server, you should move its role higher than the role you will use for the admins.
* Tell the bot about the admin role by sending `$setadmin <role>` where `<role>` is the role name, mention, or ID.
* Set any roles you would not like to be reset at the end of each cycle with `$ignore <role>` where `<role>` is the role name, mention, or ID. You can remove roles with the `$unignore <role>` command and check the current ignored roles with `$ignoredroles`.
* Tweak the settings how you like with `$setmin <minimum admins>`, `$setmax <maximum admins>`, `$setratio <members per admin>`, and `$settime <hours between swaps>`. For more information on each command, use the `$help` command.
* Once everything is setup, run `$toggle` to enable the swapping. Members will be messaged when they are selected, recieve a warning when there is 1 hour left, and a message when their time is up.
