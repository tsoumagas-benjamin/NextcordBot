# NextcordBot
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Visual Studio Code](https://img.shields.io/badge/Visual_Studio_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

This repo is a personal project to develop my skills and make a bot for Discord/Stoat. Previously made with Nextcord, MongoDB, and hosted on Fly.io (previously Heroku), now migrated to Stoat.py, PostgreSQL, and intended to be locally hosted. Currently being maintained/developed!

The library used is [Stoat.py](https://github.com/MCausc78/stoat.py).

Stoat.py documentation: https://stoatpy.readthedocs.io/en/latest/index.html

📺 Python Discord Tutorial: https://www.youtube.com/playlist?list=PL9YUC9AZJGFG6larkQJYio_f0V-O1NRjy


## How to use

Initialize a git repo and clone the files into the directory.

```bash
# Create a new folder (replace my-stoat-bot with your bot's name)
mkdir my-stoat-bot
cd my-stoat-bot
# Initialize the folder as a git repository and clone the repo
git init
git clone https://github.com/tsoumagas-benjamin/NextcordBot.git
```

## Environment variables

To run your bot, you'll need a token and other secrets set in a `.env` file.

Create a file called `.env` and place it in the root of your project.

(You can do this by creating a copy of `.env.sample` and renaming it to `.env`)

The contents should look something like this (where the part after `=` is the token you received from the Stoat bots section in the settings)

```
STOAT_TOKEN="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

If you require additional API keys or variables specific to an environment, they should also be added here. You can access them by adding a line such as `SERVER_ID = os.getenv("SERVER_ID", "")`.

Once you have everything set up you should be able to run everything using `python main.py` using a terminal from the folder containing `main.py`

## IDE Configuration

IDE config such as the `.vscode` folder do not normally belong on GitHub since they are often specific to a particular environment. To make sure GitHub will ignore the `.vscode` folder uncomment the line at the end of the `.gitignore`.

## Other Setup

- You will have to make a new bot through the My Bots option in Stoat's settings
- You will have to set up a PostgreSQL server if you are running this locally. I'm on an Arch-based distro so I followed this guide by Nick McSweeney: https://gist.github.com/NickMcSweeney/3444ce99209ee9bd9393ae6ab48599d8
    - You can then further modify this database using either the Python library psycopg (https://www.psycopg.org/) or a database admin of your choice such as  pgAdmin or DBeaver.
    - Note that your database must be active to interact with it so follow Nick's guide above to ensure that!
- You must fill out the `.env` fields shown at minimum for the bot to work
    - `STOAT_ID` and `STOAT_TOKEN` can be obtained from Stoat's My Bots settings
    - `DB_NAME` and `DB_USER` are chosen by you when following Nick McSweeney's guide/setting up PostgreSQL
    - `DEAL_KEY`, `DEAL_ID`, and `DEAL_SECRET` can be obtained after registering an app on IsThereAnyDeal here: https://isthereanydeal.com/apps/

## Credit

- FreeCodeCamp: https://www.youtube.com/c/Freecodecamp
- Glowstik: https://www.youtube.com/c/Glowstik
- Code With Swastik: https://www.youtube.com/c/CodeWithSwastik
- Jonah Lawrence • Dev Pro Tips: https://www.youtube.com/c/DevProTips
- Warframe Community Developers for help parsing worldstate data: https://github.com/WFCD/warframe-worldstate-data
- Special thanks to the Stoat and Stoat.py servers!