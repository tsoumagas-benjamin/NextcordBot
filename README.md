# NextcordBot

[![Discord](https://img.shields.io/discord/819650821314052106?color=7289DA&logo=discord&logoColor=white)](https://discord.gg/4eSAwMNvW2 "Ben's Server")
[![Powered by Nextcord](https://custom-icon-badges.herokuapp.com/badge/-Powered%20by%20Nextcord-0d1620?logo=nextcord)](https://github.com/nextcord/nextcord "Powered by Nextcord Python API Wrapper")
[![Heroku](https://img.shields.io/badge/Heroku-430098?style=for-the-badge&logo=heroku&logoColor=white)](https://dashboard.heroku.com/)

![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb&logoColor=white)
![Visual Studio Code](https://img.shields.io/badge/Visual_Studio_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white)
![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)

This repo is a personal project to work with Python, nextcord, mongoDB, and Heroku to make a Discord bot. Currently undergoing development.

The library used is [Nextcord](https://github.com/nextcord/nextcord), a maintained fork of Discord.py.

Nextcord documentation: https://nextcord.readthedocs.io/en/latest/

📺 Python Discord Tutorial: https://www.youtube.com/playlist?list=PL9YUC9AZJGFG6larkQJYio_f0V-O1NRjy


## How to use

Initialize a git repo and clone the files into the directory.

```bash
# Create a new folder (replace my-discord-bot with your bot's name)
mkdir my-discord-bot
cd my-discord-bot
# Initialize the folder as a git repository and clone the repo
git init
git clone https://github.com/tsoumagas-benjamin/NextcordBot.git
```

## Environment variables

To run your bot, you'll need a token and other secrets set in a `.env` file.

Create a file called `.env` and place it in the root of your project.

(You can do this by creating a copy of `.env.sample` and renaming it to `.env`)

The contents should look something like this (where the part after `=` is the token you received from the Discord Developer Portal)

```
DISCORD_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

If you require additional API keys or variables specific to an enviroment, they should also be added here. You can access them by adding a line such as `GUILD_ID = os.getenv("GUILD_ID", "")` to `config.py`.

## Heroku

`runtime.txt` and `Procfile` are used for Heroku configuration and can be deleted in case you do not plan on hosting there.

## IDE Configuration

IDE config such as the `.vscode` folder do not normally belong on GitHub since they are often specific to a particular environment. To make sure GitHub will ignore the `.vscode` folder uncomment the line at the end of the `.gitignore`.

## Other Setup

- You will have to make a new application and bot at https://discord.com/developers/applications
- Create an account with MongoDB Atlas for a free cluster. Once you have set up you'll be needing your MongoDB password and connection string(with your username, password, and database name inserted) for the .env.

## Credit

- FreeCodeCamp: https://www.youtube.com/c/Freecodecamp
- Glowstik: https://www.youtube.com/c/Glowstik
- Code With Swastik: https://www.youtube.com/c/CodeWithSwastik
- Jonah Lawrence • Dev Pro Tips: https://www.youtube.com/c/DevProTips
- Special thanks to the Official Nextcord Discord server!
