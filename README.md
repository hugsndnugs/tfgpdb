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

### Scheduled Announcements
- Schedule one-time or recurring messages
- Support for multiple time formats
- Embed or plain text messages
- Schedule management with list and cancel features
- Natural language time parsing
- `/schedule` - Schedule a message to be sent later
- `/schedulelist` - List all scheduled messages
- `/cancelschedule` - Cancel a scheduled message

### Music
- Play music from YouTube
- Music queue management
- Volume control
- Loop mode
- Auto-disconnect when channel is empty
- Detailed now playing information
- `/play` - Play a song from YouTube
- `/pause` - Pause the current song
- `/resume` - Resume playback
- `/skip` - Skip to the next song
- `/stop` - Stop playback and clear queue
- `/queue` - View the music queue
- `/volume` - Adjust the volume
- `/loop` - Toggle loop mode
- `/nowplaying` - Show the current song
- `/join` - Join your voice channel
- `/leave` - Leave the voice channel

### Ticket System
- Support ticket creation with reaction buttons
- Private channels for user support
- Customizable ticket categories and settings
- Support role management
- Ticket logging
- Simple ticket closure
- `/ticketpanel` - Create a panel for users to open tickets
- `/ticketsetup` - Configure ticket system settings
- `/addsupportrole` - Add a role to the support team
- `/removesupportrole` - Remove a role from the support team

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
- yt-dlp (for music features)
- FFmpeg (for music features, must be installed separately and added to PATH)

### FFmpeg Installation
For music features to work, you need to install FFmpeg:

#### Windows
1. Download the latest FFmpeg build from [FFmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Extract the ZIP file to a location on your computer
3. Add the `bin` folder to your system PATH

#### macOS
```
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```
sudo apt update
sudo apt install ffmpeg
```

## Contributing

Feel free to contribute to this project by submitting pull requests or opening issues.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
