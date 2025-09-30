import time
import asyncio
import discord
from discord.ext import commands
import yaml
import logging
from logger import Logger
logger = Logger("bot", log_level="DEBUG")

__version__ = "3.0.0"

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)

for handler in logger.logger.handlers:
    discord_logger.addHandler(handler)

with open ('config.yml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

squishy = commands.Bot(command_prefix=config['bot']['prefix'], intents=discord.Intents.all(), help_command=None)

squishy.default_embed_color = config['bot']['embed-colours']['default']
squishy.error_embed_color = config['bot']['embed-colours']['error']
squishy.success_embed_color = config['bot']['embed-colours']['success']
squishy.warning_embed_color = config['bot']['embed-colours']['warning']
squishy.info_embed_color = config['bot']['embed-colours']['info']

status_map = {
    0: discord.Status.online,
    1: discord.Status.idle,
    2: discord.Status.dnd,
    3: discord.Status.invisible
}
status_type = config['bot'].get('online-type', 1)
online_type = status_map.get(status_type, discord.Status.online)

@squishy.event
async def on_ready():
    """Handle bot ready event - fires on initial connection and reconnections"""
    # Only set start_time on first connection
    if not hasattr(squishy, 'start_time'):
        squishy.start_time = time.time()
        squishy.reconnect_count = 0
        
        # Load enabled modules
        await load_modules()
        
        # Start the status rotation task
        squishy.loop.create_task(status_rotation())
    else:
        squishy.reconnect_count += 1

async def load_modules():
    """Load enabled modules from the modules directory"""
    import os
    import importlib.util
    
    modules_dir = os.path.join(os.path.dirname(__file__), "modules")
    enabled_modules = config.get('modules', {}).get('enabled', [])
    
    # Create modules directory if it doesn't exist
    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
        logger.info("Created modules directory")
        return
    
    if not enabled_modules:
        logger.info("No modules enabled in config")
        return
    
    # Get all Python files in modules directory
    module_files = [f for f in os.listdir(modules_dir) 
                   if f.endswith('.py') and not f.startswith('__')]
    
    if not module_files:
        logger.info("No module files found in modules directory")
        return
    
    loaded_count = 0
    for module_file in module_files:
        module_name = module_file[:-3]  # Remove .py extension
        module_path = os.path.join(modules_dir, module_file)
        
        try:
            # Load the module first to get its NAME attribute
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                logger.error(f"Could not load module spec for '{module_name}'")
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get the module's NAME attribute, fallback to filename
            module_display_name = getattr(module, 'NAME', module_name)
            
            # Check if this module is enabled in config (using NAME attribute)
            if module_display_name not in enabled_modules:
                logger.debug(f"Module '{module_display_name}' not enabled, skipping")
                continue
            
            # Look for a setup function to add the cog
            if hasattr(module, 'setup'):
                await module.setup(squishy)
                logger.info(f"Loaded module: {module_display_name}")
                loaded_count += 1
            else:
                logger.warning(f"Module '{module_display_name}' has no setup function")
                
        except Exception as e:
            logger.error(f"Failed to load module '{module_name}': {e}")
    
    logger.info(f"Successfully loaded {loaded_count} modules")

async def status_rotation():
    """Rotate through enabled status types"""
    await squishy.wait_until_ready()
    
    while not squishy.is_closed():
        try:
            status_config = config['bot']['status']
            enabled_statuses = []
            
            # Get server
            guild = None
            if 'server-id' in config['bot']:
                guild = squishy.get_guild(config['bot']['server-id'])
            if not guild and squishy.guilds:
                guild = squishy.guilds[0]  # Fallback to first guild
            
            # Build list of enabled status types
            if status_config.get('channel-count', False) and guild:
                channel_count = len([c for c in guild.channels if isinstance(c, (discord.TextChannel, discord.VoiceChannel))])
                enabled_statuses.append(f"{channel_count} channels")
            
            if status_config.get('member-count', False) and guild:
                enabled_statuses.append(f"{guild.member_count} members")
            
            if status_config.get('role-count', False) and guild:
                enabled_statuses.append(f"{len(guild.roles)} roles")
            
            if status_config.get('repo', False):
                enabled_statuses.append("github.com/enhancedrock/squishy")
            
            if status_config.get('custom', {}).get('enabled', False):
                custom_text = status_config['custom'].get('custom', 'Custom Status')
                enabled_statuses.append(custom_text)
            
            # If no statuses enabled, add a default
            if not enabled_statuses:
                enabled_statuses = ["with Discord.py"]
            
            # Cycle through each enabled status
            for status_text in enabled_statuses:
                if squishy.is_closed():
                    break
                
                # Determine activity type for custom status
                activity_type = discord.ActivityType.watching  # default
                if status_config.get('custom', {}).get('enabled', False) and status_text == status_config['custom'].get('custom', ''):
                    custom_type = status_config['custom'].get('custom-type', 1)
                    activity_map = {
                        0: discord.ActivityType.playing,
                        1: discord.ActivityType.watching,
                        2: discord.ActivityType.listening,
                        3: None  # No activity type (just status)
                    }
                    activity_type = activity_map.get(custom_type, discord.ActivityType.watching)
                
                # Create activity
                if activity_type:
                    activity = discord.Activity(type=activity_type, name=status_text)
                else:
                    activity = None
                
                # Update status
                await squishy.change_presence(status=online_type, activity=activity)
                logger.debug(f"Online type set to: {online_type}")
                logger.debug(f"Status updated: {status_text}")
                
                # Wait for the configured interval
                interval = status_config.get('interval', 30)
                await asyncio.sleep(interval)
        
        except Exception as e:
            logger.error(f"Error in status rotation: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds before retrying



class HelpView(discord.ui.View):
    def __init__(self, user: discord.User | discord.Member, commands_list: list, timeout: float = 60.0, start_page: int = 0) -> None:
        super().__init__(timeout=timeout)
        self.user = user
        self.commands_list = commands_list
        self.current_page = start_page
        self.max_pages = (len(commands_list) + 4) // 5  # 5 commands per page
        self.message: discord.Message | None = None
        
        self.update_buttons()
    
    def get_page_commands(self):
        """Get the commands for the current page"""
        start_idx = self.current_page * 5
        end_idx = min(start_idx + 5, len(self.commands_list))
        return self.commands_list[start_idx:end_idx]
    
    def create_embed(self):
        """Create the embed for the current page"""
        embed = discord.Embed(
            title="Available Commands",
            color=squishy.default_embed_color,
        )
        
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")

        page_commands = self.get_page_commands()
        for cmd in page_commands:
            description = cmd.brief if cmd.brief else ("*No brief description - Click button below for full description*" if cmd.help else "*No description*")
            embed.add_field(
                name=f"{config['bot']['prefix']}{cmd.name}",
                value=description,
                inline=False
            )
        
        return embed
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.clear_items()
        
        # First row: Navigation buttons
        prev_button = discord.ui.Button(
            emoji="⬅️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0,
            row=0
        )
        prev_button.callback = self.previous_page
        
        page_button = discord.ui.Button(
            label=f"{self.current_page + 1}/{self.max_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=0
        )
        
        next_button = discord.ui.Button(
            emoji="➡️",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page >= self.max_pages - 1,
            row=0
        )
        next_button.callback = self.next_page
        
        self.add_item(prev_button)
        self.add_item(page_button)
        self.add_item(next_button)
        
        # Second row: Command buttons
        page_commands = self.get_page_commands()
        for i, cmd in enumerate(page_commands):
            cmd_button = discord.ui.Button(
                label=cmd.name,
                style=discord.ButtonStyle.primary,
                row=1
            )
            # Create a callback that captures the current command
            cmd_button.callback = self.create_command_callback(cmd)
            self.add_item(cmd_button)
    
    def create_command_callback(self, cmd):
        """Create a callback function for a specific command"""
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message(
                    "You cannot interact with this help menu.", 
                    ephemeral=True
                )
                return
            
            # Show detailed command info
            embed = discord.Embed(
                title=f"Command: {config['bot']['prefix']}{cmd.name}",
                color=squishy.info_embed_color
            )
            
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")

            description = cmd.help or cmd.brief or "*No description available*"
            embed.add_field(name="Description", value=description, inline=False)
            
            if cmd.aliases:
                aliases = ", ".join([f"`{alias}`" for alias in cmd.aliases])
                embed.add_field(name="Aliases", value=aliases, inline=False)
            
            if cmd.signature:
                embed.add_field(
                    name="Usage", 
                    value=f"`{config['bot']['prefix']}{cmd.name} {cmd.signature}`", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="Usage", 
                    value=f"`{config['bot']['prefix']}{cmd.name}`", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "You cannot interact with this help menu.", 
                ephemeral=True
            )
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message(
                "You cannot interact with this help menu.", 
                ephemeral=True
            )
            return
        
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

@squishy.command(brief="Get a list of commands and their descriptions/arguments",
                 help="Get a paginated list of commands and their brief explanations, and their full length description and arguments should they exist by clicking the associated button. You can also specify a command name to get detailed help for that specific command.")
async def help(ctx, *, query: str = None):
    # If no query provided, show first page
    if query is None:
        page = 1
    else:
        # Try to parse as integer (page number)
        try:
            page = int(query)
        except ValueError:
            # Not an integer, treat as command name
            command = squishy.get_command(query.lower())
            if command is None:
                embed = discord.Embed(
                    title="Command Not Found",
                    description=f"No command named `{query}` found. Use `{config['bot']['prefix']}help` to see all commands.",
                    color=squishy.error_embed_color
                )
                embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
                await ctx.reply(embed=embed)
                return
            
            # Show detailed help for the specific command
            embed = discord.Embed(
                title=f"Command: {config['bot']['prefix']}{command.name}",
                color=squishy.info_embed_color
            )
            
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")

            description = command.help or command.brief or "*No description available*"
            embed.add_field(name="Description", value=description, inline=False)
            
            if command.aliases:
                aliases = ", ".join([f"`{alias}`" for alias in command.aliases])
                embed.add_field(name="Aliases", value=aliases, inline=False)
            
            if command.signature:
                embed.add_field(
                    name="Usage", 
                    value=f"`{config['bot']['prefix']}{command.name} {command.signature}`", 
                    inline=False
                )
            else:
                embed.add_field(
                    name="Usage", 
                    value=f"`{config['bot']['prefix']}{command.name}`", 
                    inline=False
                )
            
            await ctx.reply(embed=embed)
            return
    
    # Show paginated command list
    # Get all commands and sort them alphabetically, excluding hidden ones
    commands_list = sorted([cmd for cmd in squishy.commands if not cmd.hidden], key=lambda x: x.name)
    
    # Calculate max pages
    max_pages = (len(commands_list) + 4) // 5
    
    # Validate page number
    if page < 1:
        page = 1
    elif page > max_pages:
        page = max_pages
    
    # Convert to 0-based index for internal use
    start_page = page - 1
    
    view = HelpView(ctx.author, commands_list, start_page=start_page)
    embed = view.create_embed()
    
    message = await ctx.reply(embed=embed, view=view)
    view.message = message

@squishy.command(brief="Ping the bot to check its latency")
async def ping(ctx):
    latency = squishy.latency * 1000  # Convert to milliseconds
    embed = discord.Embed(
        title="Pong!",
        description=f"Latency: `{latency:.2f} ms`",
        color=squishy.success_embed_color
    )
    embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
    await ctx.reply(embed=embed)

@squishy.command(brief="Check the bots uptime")
async def uptime(ctx):
    current_time = time.time()
    uptime_seconds = int(current_time - squishy.start_time)
    
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    
    embed = discord.Embed(
        title="Uptime",
        description=f"The bot has been online for: `{uptime_str}`",
        color=squishy.info_embed_color
    )
    embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
    await ctx.reply(embed=embed)

@squishy.command(brief="Stats for nerds", help="Shows the CPU and memory usage, number of users, uptime, reconnects, and latency.")
async def stats(ctx):
    import psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    cpu_usage = psutil.cpu_percent(interval=1)

    current_time = time.time()
    uptime_seconds = int(current_time - squishy.start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(
        title="Bot Statistics",
        description=f"Squishy v{__version__} | https://github.com/enhancedrock/squishy",
        color=squishy.info_embed_color
    )
    embed.add_field(name="CPU Usage", value=f"`{cpu_usage}%`", inline=False)
    embed.add_field(name="Memory Usage", value=f"`{mem_info.rss / (1024 * 1024):.2f} MB`", inline=False)
    embed.add_field(name="Number of Users", value=f"`{len(squishy.users)}`", inline=False)
    embed.add_field(name="Uptime", value=f"`{days}d {hours}h {minutes}m {seconds}s`", inline=False)
    embed.add_field(name="Reconnects", value=f"`{squishy.reconnect_count}`", inline=False)
    embed.add_field(name="Latency", value=f"`{squishy.latency * 1000:.2f} ms`", inline=False)
    embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
    
    await ctx.reply(embed=embed)

@squishy.command(brief="Did you know Squishy was made by a transfem? Now you do!", hidden=True)
async def estrogen(ctx):
    embed = discord.Embed(
        title=":3:tm:",
        description="bwaaa",
        color=0xADD8E6
    )
    embed.set_image(url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/bwaaa.gif")
    
    await ctx.reply(embed=embed)

@squishy.event
async def on_message(message):
    # Don't respond to bot messages
    if message.author.bot:
        return
    
    # Check if bot is mentioned
    if squishy.user.mention in message.content and not message.content.startswith(f"{config['bot']['prefix']}"):
        embed = discord.Embed(
            title="Hello!",
            description=f"My prefix is `{config['bot']['prefix']}`",
            color=squishy.default_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await message.reply(embed=embed)
    
    # Process commands after handling mentions
    await squishy.process_commands(message)

@squishy.command(brief="List available modules from repositories")
async def modules(ctx, repo_id: int = 0):
    """List all available modules from a specific repository"""
    # Check if user has permission to view modules
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to view available modules.",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        return
    
    try:
        import market
        modules_list = market.list_available_modules(repo_id)
        
        if not modules_list:
            embed = discord.Embed(
                title="No Modules Found",
                description=f"No modules found in repository {repo_id}",
                color=squishy.warning_embed_color
            )
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
            await ctx.reply(embed=embed)
            return
        
        # Create pages of modules (5 per page)
        pages = []
        for i in range(0, len(modules_list), 5):
            page_modules = modules_list[i:i+5]
            embed = discord.Embed(
                title=f"Available Modules (Page {len(pages)+1})",
                description=f"Repository {repo_id}",
                color=squishy.default_embed_color
            )
            
            for module in page_modules:
                name = module.get('name', 'Unknown')
                version = module.get('version', 'Unknown')
                author = module.get('author', 'Unknown')
                description = module.get('description', 'No description available')
                
                # Check if installed
                installed = market.is_module_installed(module.get('source', ''))
                status = "✅ Installed" if installed else "⬇️ Available"
                
                embed.add_field(
                    name=f"{name} v{version} {status}",
                    value=f"**Author:** {author}\n**Description:** {description[:100]}{'...' if len(description) > 100 else ''}",
                    inline=False
                )
            
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
            pages.append(embed)
        
        if len(pages) == 1:
            await ctx.reply(embed=pages[0])
        else:
            # TODO: Add pagination view for multiple pages
            await ctx.reply(embed=pages[0])
            
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"Failed to fetch modules: {str(e)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)

@squishy.command(brief="Install a module by name")
async def install(ctx, *, module_name: str):
    """Install a module by its name from the default repository"""
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to view installed modules.",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        return
    try:
        import market
        
        # Send initial message
        embed = discord.Embed(
            title="Installing Module",
            description=f"Installing `{module_name}`...",
            color=squishy.info_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        message = await ctx.reply(embed=embed)
        
        # Try to install
        success = market.install_module_by_name(module_name)
        
        if success:
            embed = discord.Embed(
                title="Module Installed",
                description=f"Successfully installed `{module_name}`!\n\n⚠️ **Restart the bot** to load the new module.",
                color=squishy.success_embed_color
            )
        else:
            embed = discord.Embed(
                title="Installation Failed",
                description=f"Failed to install `{module_name}`. Check if the module name is correct and if it's already installed.",
                color=squishy.error_embed_color
            )
        
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await message.edit(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)

@squishy.command(brief="Update all installed modules")
async def updatemodules(ctx):
    """Update all installed modules that have available updates"""
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to view installed modules.",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        return
    try:
        import market
        
        # Send initial message
        embed = discord.Embed(
            title="Updating Modules",
            description="Checking for updates...",
            color=squishy.info_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        message = await ctx.reply(embed=embed)
        
        # Update all modules
        results = market.update_all_modules()
        
        if not results:
            embed = discord.Embed(
                title="No Updates Available",
                description="All installed modules are up to date!",
                color=squishy.success_embed_color
            )
        else:
            updated = [name for name, success in results.items() if success]
            failed = [name for name, success in results.items() if not success]
            
            description = ""
            if updated:
                description += f"**Successfully Updated ({len(updated)}):**\n"
                description += "\n".join([f"✅ {name}" for name in updated])
            
            if failed:
                if description:
                    description += "\n\n"
                description += f"**Failed to Update ({len(failed)}):**\n"
                description += "\n".join([f"❌ {name}" for name in failed])
            
            if updated:
                description += "\n\n⚠️ **Restart the bot** to load the updated modules."
            
            color = squishy.success_embed_color if not failed else squishy.warning_embed_color
            embed = discord.Embed(
                title="Module Updates Complete",
                description=description,
                color=color
            )
        
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await message.edit(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)

@squishy.command(brief="Show installed modules")
async def installed(ctx):
    """Show all currently installed modules"""
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to view installed modules.",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        return
    try:
        import market
        
        installed_modules = market.get_installed_modules()
        
        if not installed_modules:
            embed = discord.Embed(
                title="No Modules Installed",
                description="No modules are currently installed.",
                color=squishy.info_embed_color
            )
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
            await ctx.reply(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"Installed Modules ({len(installed_modules)})",
            color=squishy.default_embed_color
        )
        
        for module_name, module_info in installed_modules.items():
            name = module_info.get('name', module_name)
            version = module_info.get('version', 'Unknown')
            author = module_info.get('author', 'Unknown')
            description = module_info.get('description', 'No description available')
            
            # Check if update available
            if module_info.get('source'):
                repo_module = market.find_module_in_repos(module_info['source'])
                if repo_module:
                    can_update, current_ver, new_ver = market.can_module_be_updated(repo_module)
                    status = f"🔄 Update to {new_ver}" if can_update else "✅ Up to date"
                else:
                    status = "❓ Not in repos"
            else:
                status = "🔒 Local only"
            
            embed.add_field(
                name=f"{name} v{version} {status}",
                value=f"**Author:** {author}\n**Description:** {description[:100]}{'...' if len(description) > 100 else ''}",
                inline=False
            )
        
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)

@squishy.command(brief="Uninstall a module")
async def uninstall(ctx, *, module_name: str):
    """Uninstall a module by its name"""
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="Permission Denied",
            description="You need administrator permissions to view installed modules.",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)
        return
    try:
        import market
        
        # Find the module by name
        installed_modules = market.get_installed_modules()
        target_module = None
        
        for module_info in installed_modules.values():
            if module_info.get('name', '').lower() == module_name.lower():
                target_module = module_info
                break
        
        if not target_module:
            embed = discord.Embed(
                title="Module Not Found",
                description=f"No installed module named `{module_name}` found.",
                color=squishy.error_embed_color
            )
            embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
            await ctx.reply(embed=embed)
            return
        
        # Send initial message
        embed = discord.Embed(
            title="Uninstalling Module",
            description=f"Uninstalling `{module_name}`...",
            color=squishy.info_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        message = await ctx.reply(embed=embed)
        
        # Uninstall the module
        source_url = target_module.get('source', '')
        success = market.uninstall_module(source_url) if source_url else False
        
        if not source_url:
            # Manual removal for modules without source
            try:
                import os
                module_path = os.path.join('modules', target_module['filename'])
                os.remove(module_path)
                success = True
            except Exception:
                success = False
        
        if success:
            embed = discord.Embed(
                title="Module Uninstalled",
                description=f"Successfully uninstalled `{module_name}`!\n\n⚠️ **Restart the bot** to complete removal.",
                color=squishy.success_embed_color
            )
        else:
            embed = discord.Embed(
                title="Uninstallation Failed",
                description=f"Failed to uninstall `{module_name}`.",
                color=squishy.error_embed_color
            )
        
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await message.edit(embed=embed)
        
    except Exception as e:
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        await ctx.reply(embed=embed)

@squishy.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    else:
        logger.error(f"Command error in {ctx.command}: {error}")
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred while executing the command: {str(error)}",
            color=squishy.error_embed_color
        )
        embed.set_footer(text="Squishy bot by @enhancedrock", icon_url="https://raw.githubusercontent.com/enhancedrock/enhancedrock/refs/heads/main/squishypfp.png")
        try:
            await ctx.reply(embed=embed)
        except:
            pass

squishy.run(config['bot']['bot-token'], log_handler=None)