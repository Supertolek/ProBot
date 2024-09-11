import os
import discord
import pronotepy
import pytz
import asyncio
from pronoteAPI_connection import connection_to_pronotepy
from pronoteAPI_utils import get_homeworks, get_grades
from discord import ForumChannel, app_commands
from discord.ext import commands
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from id_wrapper import allready_registered, save_user, get_user, get_all_users

scheduler = AsyncIOScheduler()

def reload_scheduler():
    first_update = datetime.datetime.now().strftime("%Y-%m-%d 15:00:00")
    second_update = datetime.datetime.now().strftime("%Y-%m-%d 17:00:00")
    third_update = datetime.datetime.now().strftime("%Y-%m-%d 18:00:00")
    final_update = datetime.datetime.now().strftime("%Y-%m-%d 22:00:00")
    scheduler.add_job(update_all_homeworks, "date", run_date=first_update, timezone=pytz.timezone("Europe/Paris"))
    scheduler.add_job(update_all_homeworks, "date", run_date=second_update, timezone=pytz.timezone("Europe/Paris"))
    scheduler.add_job(update_all_homeworks, "date", run_date=third_update, timezone=pytz.timezone("Europe/Paris"))
    scheduler.add_job(update_all_homeworks, "cron", hour="18-21", minute="0,19", timezone=pytz.timezone("Europe/Paris"))
    scheduler.add_job(reload_scheduler, "date", run_date=final_update, timezone=pytz.timezone("Europe/Paris"))
    scheduler.start()
    

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

users: dict[str, pronotepy.Client] = {}
failed_connection = []

@bot.event
async def on_ready():
    all_users = get_all_users()
    for user in all_users:
        try:
            client = pronotepy.Client.token_login(user[1],user[2],user[3],user[4])
            users[user[0]] = client
            save_user(user[0], client.pronote_url, client.username,
                  client.password, client.uuid)
            print(f"{user[0]} connected")
        except:
            print(f"{user[0]} have an issue")
            failed_connection.append(user[0])
            
    if failed_connection != []:
        print(failed_connection)
    
    print("Bot is up!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)
    reload_scheduler()


@bot.tree.command(name="link", description="Relie ton compte pronote.")
async def link_command(interaction: discord.Interaction):
    await link_command_callback(interaction)


async def link_command_callback(interaction: discord.Interaction):
    class Popup(discord.ui.Modal, title="Connectez-vous à Pronote."):
        username = discord.ui.TextInput(label="Nom d'utilisateur",
                                        style=discord.TextStyle.short,
                                        placeholder="jean.dupont",
                                        required=True,
                                        min_length=1,
                                        max_length=20)

        password = discord.ui.TextInput(label="Mot de passe",
                                        style=discord.TextStyle.short,
                                        placeholder="passw0rd",
                                        required=True)
        
        async def on_submit(self, interaction: discord.Interaction):
            if allready_registered(interaction.user.id):
                if int(interaction.user.id) in failed_connection:
                    await interaction.response.send_message(
                        "Vous êtes déjà enregistré dans le bot.", ephemeral=True)
                    return
                else:
                    pass
            await interaction.response.send_message(
                "Connection à pronote en cours...")
            message = await interaction.original_response()
            username = self.username.value
            password = self.password.value
            client = connection_to_pronotepy(username, password)
            if client is None:
                button = discord.ui.Button(label="Réessayer",
                                           style=discord.ButtonStyle.primary)
                button.callback = link_command_callback
                view = discord.ui.View()
                view.add_item(button)
                await message.edit(
                    content="Identifiant ou Mot de passe incorrect.",
                    view=view)
                await link_command_callback(interaction)
                return
            else:
                users[str(interaction.user.id)] = client
                save_user(interaction.user.id, client.pronote_url, client.username,
                          client.password, client.uuid)
                await message.edit(
                    content=
                    f"Connection réussie!\nVous êtes maintenant connecté à Pronote en tant que {username}."
                )

    await interaction.response.send_modal(Popup())


@bot.tree.command(
    name="info",
    description="Obtiens les informations sur ton compte pronote.")
async def info_command(interaction: discord.Interaction):
    user_info = get_user(interaction.user.id)
    if user_info is None:
        await interaction.response.send_message(
            "You are not linked to Pronote.")
    else:
        await interaction.response.send_message(
            f"Nom d'utilisateur : {user_info["username"]}\nToken : {user_info["token"]}\nUrl pronote : {user_info["url"]}\nUUId : {user_info["uuid"]}",
            ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if after.channel and after.channel.id == 1282706897316876298:
        await member.move_to(before.channel)
        await update_homeworks(member.id)


async def update_all_homeworks(users_id: list[int]|None=None):
    users_id_list = []
    if not users_id:
        users_id_list = [int(user_id) for user_id in users.keys()]
    for user_id in users_id_list:
        await update_homeworks(user_id, False)

async def update_homeworks(member_id: int, ping_if_not_done: bool=True):
    forum_ids = {
        "FRANCAIS": 1280869011306975262,
        "MATHEMATIQUES": 1280869146598445169,
        "PHYSIQUE-CHIMIE": 1280869206526787584,
        "NUMERIQUE SC.INFORM.": 1280869270548643974,
        "HISTOIRE-GEOGRAPHIE": 1280869301997273118,
        "ANGLAIS LV1": 1280869341872525353,
        "ESPAGNOL LV2": 1280869528678699052,
        "ALLEMAND LV2": 1280869567094198332,
        "ENS. SCIENT. SVT": 1280869612753522762,
        "ENS. SCIENT. PC": 1280869612753522762,
        "ED MORALE ET CIVIQUE": 1280869634169634867,
        "CINEMA-AUDIOVISUEL": 1280869661143076978
    }
    forum_channels = {
        subject_name: bot.get_channel(int(channel_id))
        for subject_name, channel_id
        in forum_ids.items()}
    forum_channels_good = {
        subject_name: channel
        for subject_name, channel
        in forum_channels.items()
        if isinstance(channel, ForumChannel)
    }
    forum_channels_threads = {} # "subject": {"thread_title": ["thread", "history"]}
    for subject_name, forum_channel in forum_channels_good.items():
        forum_channel_threads = {} # "thread_title": ["thread", "history"]
        for forum_channel_thread in forum_channel.threads:
            if forum_channel_thread.owner_id == 1281282866080120914:
                thread_history = forum_channel_thread.history(limit=2, oldest_first=True)
                thread_first_message = await thread_history.__anext__()
                forum_channel_threads[thread_first_message.content] = [forum_channel_thread, thread_history]
        forum_channels_threads[subject_name] = forum_channel_threads

    client = users["961697282149990430"] # Bastien
    client = users[str(member_id)]
    homeworks = client.homework(datetime.date.today())
    for homework in homeworks:
        subject = homework.subject.name
        description = homework.description
        thread_name = f"{homework.date}: Devoir de {subject.capitalize()}"
        thread_description = f"**Devoir de {subject.capitalize()}**\n{description}\n*{homework.date}*"
        if homework.files:
            thread_description += f"\n*Fichiers:*\n{"\n".join([f"[{file.name}]({file.url})" for file in homework.files])}"
        if thread_description not in forum_channels_threads[subject]:
            generated_thread = await forum_channels_good[subject].create_thread(
                name=thread_name,
                content=thread_description)
            forum_channels_threads[subject][thread_name] = [generated_thread.thread, generated_thread.thread.history(limit=2, oldest_first=True)]
            if not homework.done:
                await generated_thread.thread.send(f"Élèves concernés:\n<@{member_id}>", silent=True)
            else:
                mention_message = await generated_thread.thread.send("Élèves concernés:", silent=True)
                await mention_message.edit(content=mention_message.content + f"\n<@{member_id}>")
        else:
            (subject_thread, subject_thread_history) = forum_channels_threads[subject][thread_description]
            first_message = await subject_thread_history.__anext__()
            if f"<@{member_id}>" not in first_message.content:
                await first_message.edit(content = f"{first_message.content}\n<@{member_id}>")
            if not homework.done:
                await subject_thread.send(f"<@{member_id}>")

@bot.tree.command(name="link²", description="Relie ton compte pronote.")
async def _link_command(interaction: discord.Interaction, username: str,
                        password: str):
    await interaction.response.send_message("Connection à pronote en cours...")
    message = await interaction.original_response()

    client = connection_to_pronotepy(username, password)
    if client is None:
        await message.edit(content="Identifiant ou Mot de passe incorrect.")
        return
    else:
        await message.edit(content="Connection réussie !")
        save_user(username, client.pronote_url, client.username,
                  client.password, client.uuid)
        date = datetime.date.today()
        homeworks = client.homework(date)

        if not homeworks:
            await message.edit(
                content=f"{interaction.user.mention}, aucun devoir trouvé.")
            return

        embeds = []
        for homework in homeworks:
            embed = discord.Embed(
                title=f"Devoir de {homework.subject.name}",
                description=
                f"A rendre pour le {homework.date.strftime('%d/%m/%Y')}",
                color=discord.Color.from_str(homework.background_color))
            embed.add_field(name="Description",
                            value=homework.description,
                            inline=False)
            embeds.append(embed)
        await message.edit(embeds=embeds)


bot.run(os.environ["DISCORD_TOKEN"])
