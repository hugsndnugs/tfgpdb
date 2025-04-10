# The Final General Purpose Discord Bot

A feature-rich Discord bot with moderation, fun, utility, leveling, welcome messages, and auto-moderation features similar to popular bots like Probot and MEE6. Uses Discord's slash commands for a modern user experience.

## Features

### Moderation Commands
- `/kick` - Kick a member from the server
- `/ban` - Ban a member from the server
- `/unban` - Unban a member from the server
- `/clear` - Clear a specified number of messages
- `/mute` - Mute a member
- `/unmute` - Unmute a member

### Fun Commands
- `/roll` - Roll dice in NdN format (e.g., 2d6)
- `/choose` - Choose between multiple options
- `/rps` - Play rock paper scissors
- `/meme` - Get a random meme
- `/quote` - Get a random inspirational quote

### Utility Commands
- `/ping` - Check bot latency
- `/serverinfo` - Display server information
- `/userinfo` - Display user information
- `/time` - Get current time
- `/weather` - Get weather information

### Leveling System
- Auto XP gain from chatting
- Level up notifications
- `/rank` - Check your or someone else's level and XP
- `/leaderboard` - View the server's XP leaderboard

### Welcome System
- Customizable welcome/goodbye messages
- Welcome DMs to new members
- `/setwelcomechannel` - Set the channel for welcome messages
- `/setgoodbyechannel` - Set the channel for goodbye messages
- `/setwelcomemessage` - Customize welcome messages
- `/setgoodbyemessage` - Customize goodbye messages
- `/togglewelcomedm` - Toggle welcome DMs
- `/setwelcomedmmessage` - Customize welcome DM messages

### Auto-Moderation
- Anti-spam protection
- Bad word filtering
- Anti-mention spam
- Discord invite filtering
- Configurable punishments
- `/automod` - Toggle auto-moderation
- `/automodlog` - Set logging channel
- `/addfilterword` - Add words to filter
- `/removefilterword` - Remove words from filter
- `/filterwords` - List filtered words
- `/allowserver` - Allow Discord invites from specific servers
- `/disallowserver` - Disallow invites from servers

### Polls
- Create polls with up to 9 options
- Simple Yes/No polls
- Automatic vote counting
- Visual results with progress bars
- Poll duration control
- Early poll ending by creator
- `/poll` - Create a poll with multiple options
- `/quickpoll` - Create a simple yes/no poll
- `/endpoll` - End a poll early and display results

### Reaction Roles
- Role assignment based on message reactions
- Custom embeds for role menus
- Add/remove roles with custom emojis
- Role descriptions
- `/reactionrole` - Create a reaction role message
- `/addrole` - Add a role to a reaction role message
- `/removerole` - Remove a role from a reaction role message
- `/listroles` - List all roles in a reaction role message

### Custom Commands
- Server-specific custom commands
- Simple text responses
- Command descriptions and metadata
- Command usage statistics
- `/addcmd` - Add a custom command
- `/editcmd` - Edit an existing custom command
- `/removecmd` - Remove a custom command
- `/listcmds` - List all custom commands
- `/cmdinfo` - View detailed information about a command

### Giveaways
- Easy-to-setup giveaways with reaction entry
- Multiple winner support
- Customizable duration and descriptions
- Winner rerolling
- Automatic winner announcement
- `/giveaway` - Start a new giveaway
- `/giveaway_end` - End a giveaway early
- `/giveaway_reroll` - Reroll winners for a giveaway
- `/giveaway_list` - List all active giveaways

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy the `.env.example` file to `.env`:
   ```
   cp .env.example .env
   ```
4. Edit the `.env` file and update the values:
   - Replace `your_discord_bot_token_here` with your actual Discord bot token
   - Replace `your_openweathermap_api_key_here` with your OpenWeatherMap API key if you want the weather command to work
   - Replace `your_discord_user_id_here` with your Discord user ID if you want to access owner-only commands
5. Make sure to enable the "MESSAGE CONTENT INTENT" in your Discord Developer Portal for your bot
6. When inviting the bot to your server, make sure to include the `applications.commands` scope to allow slash commands
7. Run the bot:
   ```
   python bot.py
   ```
   or if using a virtual environment:
   ```
   .venv\Scripts\python bot.py
   ```

## Required Permissions

When adding the bot to your server, ensure it has the following permissions:
- Send Messages
- Manage Messages (for clear command and auto-moderation)
- Kick Members (for kick command)
- Ban Members (for ban command)
- Manage Roles (for mute/unmute commands)
- Read Message History
- View Channels
- Embed Links (for rich embeds)

## Requirements

- Python 3.8 or higher
- discord.py
- python-dotenv
- aiohttp
- python-dateutil
- pytz

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
