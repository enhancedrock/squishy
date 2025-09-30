<h1 align="center">
<img width="75" src="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png" alt="Squishy, a blue slime girl character by @enhancedrock, art by @chewyffon">

squishy
</h1>
<p align="center">
The cutest<sup>*</sup> free, open source, fully expandable, and self-hostable Discord bot. Designed to provide all the features you could ever need such as an economy, minigames, levelling, and more.
</p>
<sup>*In my subjective opinion</sup>

## Why FOSS?

I believe it presents new opportunities for me, Squishy, and the servers I/others use her in. I hate freemium Discord bots that charge you for features that you would just expect to come normally, so I decided to write my own bot and self-host her.

## Why not host her, and allow people to add her to their server?

I can't afford to host a bot for however many servers to use. And this way, people can customise her code to add their own features or things they would like for their server (although under the AGPL-3.0 license, the modified source code must be made public to users of your version of the bot).

## Hey, you said this could do everything I need, but there's no moderation!

Use Wick. It's the perfect moderation bot. If you really want it to be a part of Squishy, feel free to write an addon! I may at some point.

## Setup

1. Make an 'New Application' in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Optionally, give it a Profile Picture and Description, before heading to 'Installation'.
> [!NOTE]
> Squishy's normal profile picture is available in the `assets` folder as `squishypfp.png`, downloaded in step 8. Credit for this goes to Chewy/chewyffon/@chewyffon.
3. Scroll to 'Guild Install', and add the 'bot' scope, then add the 'Administrator' permission.
4. Now, copy the 'Discord Provided Link', open it and add it to your server.
5. Return to the Developer Portal at the Installation tab, and change 'Discord Provided Link' to 'None'.
6. Now go to the 'Bot' section, and disable 'Public Bot'.
> [!NOTE]
> Steps 5-6 will prevent people who aren't you from using your instance of Squishy, as she's only designed to work in 1 server at a time.
7. Enable the 3 intents (Presence, Server Members, Message Content) and press 'Reset Token'. Copy your bot token you're given.
> [!CAUTION]
> This token is how programs access your bot. **Keep it safe, and do not share it with ANYONE**, or else they can log in as the bot and **do whatever they want to your server.**
8. Download the latest source code zip from the [releases](https://github.com/enhancedrock/squishy/releases), and extract it somewhere, renaming the folder to `squishy`
9. Duplicate `config-template.yml`, changing the duplicates name to `config.yml`
10. In your new `config.yml`, set `bot-token` to the toke we got in step 7, and `server-id` to the server you plan on using Squishy in.`
> [!NOTE]
> Squishy needs Python 3.10.

## Running Squishy

That's it! You can CD into her parent directory and run `python3 squishy` or CD into her directory and run `python3 .`
Your next step would be to get some addons from the web UI (go to localhost:6942, the default password is `squishable`), go to Market, and get some addons! (As of the time of writing, the default addons are dummy addons and don't do anything) You can also do this with commands, see s.help for more. Or - look into making some. Look at the template addon in the `assets` folder.

## License

This project is licensed under the AGPL-3.0.
Additional attribution requirements apply — see the `NOTICE` file for details.