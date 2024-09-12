import os
import json
import discord
from discord import ForumChannel
from discord.ext import commands
import pronotepy
from pronoteAPI_connection import connection_to_pronotepy, connection_with_qr_code
import datetime
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from id_wrapper import allready_registered, save_user, get_user, get_all_users
import hashlib
from homeworks_wrapper import compare_stored_homeworks, get_stored_homeworks_hash, store_homeworks_hash

scheduler = AsyncIOScheduler()

config = json.load(open("config.json"))

bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

users: dict[str, pronotepy.Client] = {}
failed_connection = []

def reload_scheduler():
    # Configure toutes les horaires d'actualisation fixes
    for update in config["homework_check"]["static_update_hours"]:
        run_date = datetime.datetime.now().strftime(f"%Y-%m-%d {update}")
        scheduler.add_job(
            update_homeworks,
            "date",
            run_date=run_date,
            timezone=pytz.timezone("Europe/Paris"))
    # Configure les actualisations périodiques (ex: toutes les 30 minutes)
    scheduler.add_job(
        update_homeworks,
        "cron",
        hour=f"{config["homework_check"]["repetitive_update_start"]}-{config["homework_check"]["repetitive_update_end"]}",
        minute=",".join(config["homework_check"]["repetitive_update_steps"]),
        timezone=pytz.timezone("Europe/Paris"))
    run_date = datetime.datetime.now().strftime(f"%Y-%m-%d {config["homework_check"]["repetitive_update_end"]}:00:01")
    scheduler.add_job(
        reload_scheduler,
        "date",
        run_date=run_date,
        timezone=pytz.timezone("Europe/Paris"))
    scheduler.start()

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
async def link_command(interaction: discord.Interaction, image: discord.Attachment, verification_code: str):
    await interaction.response.send_message(f"<@{interaction.user.id}>: Connection en cours à Pronote...")
    original_response = await interaction.original_response()
    connection_status = connection_with_qr_code(image.url, verif_code=verification_code)
    # Vérifie si la connexion a réussi
    if connection_status:
        users[str(interaction.user.id)] = connection_status
        await original_response.edit(content=f"<@{interaction.user.id}>: Connection réussie!")
    else:
        await original_response.edit(content=f"<@{interaction.user.id}>: Une erreur est survenue lors de la connexion.")


async def _link_command_callback(interaction: discord.Interaction):
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
                button.callback = _link_command_callback
                view = discord.ui.View()
                view.add_item(button)
                await message.edit(
                    content="Identifiant ou Mot de passe incorrect.",
                    view=view)
                await _link_command_callback(interaction)
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



@bot.tree.command(name="homeworks", description="Met à jour les devoirs.")
async def update_homeworks_command(interaction: discord.Interaction):
    await interaction.response.send_message("Actualisation des devoirs en cours...")
    await update_homeworks(interaction.user.id)
    await interaction.edit_original_response(content="Actualisation des devoirs réussie.")


async def update_homeworks(users_id: list[int]|int|None=None):
    """Syncronise les devoirs affichés sur discord avec les devoirs de pronote."""
    # Génère la liste des utilisateurs connectés
    generated_users_id = []
    if isinstance(users_id, int):
        generated_users_id = [users_id]
    elif isinstance(users_id, list):
        generated_users_id = users_id
    else:
        generated_users_id = [int(user_id) for user_id in users.keys()]

    # Initie la liste des salons chargés
    loaded_subject_forum_channels = {}
    loaded_homeworks_threads = {}
    
    # Récupère les devoirs de pronote
    for user_id in generated_users_id:
        # Exécuté pour chaque utilisateur connecté
        client = users[str(user_id)]
        homeworks = client.homework(datetime.date.today())
        # Détecte si de nouveaux devoirs sont apparus
        if compare_stored_homeworks(int(user_id), [homework.description for homework in homeworks]):
            print(f"No update for {user_id}")
        else:
            print(f"Update for {user_id}")
            stored_homeworks_hash = get_stored_homeworks_hash(user_id)
            new_homeworks = [
                homework
                for homework in homeworks
                if hashlib.sha256(str(homework.description).encode()).hexdigest() not in stored_homeworks_hash
            ]
            # Crée les salons des devoirs si ils n'existent pas
            for homework in new_homeworks:
                # Exécuté pour chaque devoir
                thread_description = "\n".join([
                    f"**Devoir de {homework.subject.name.capitalize()}**",
                    f"{homework.description}",
                    f"*{homework.date}*"])
                thread_name = f"{homework.date}: Devoir de {homework.subject.name.capitalize()}"
                # Vérifie que la matière est déjà chargée
                if homework.subject.name not in loaded_homeworks_threads:
                    loaded_homeworks_threads[homework.subject.name] = {}
                # Vérifie si le salon existe déjà
                if thread_description in loaded_homeworks_threads[homework.subject.name]:
                    # Exécuté si le salon existe déjà
                    thread = loaded_homeworks_threads[homework.subject.name][thread_description]
                    if not isinstance(thread, discord.channel.ThreadWithMessage):
                        print(f"Thread {thread_description} is not a thread")
                        continue
                    thread_history = thread.thread.history(limit=2, oldest_first=True)
                    thread_messages = [message async for message in thread_history]
                    await thread_messages[1].edit(content=thread_messages[1].content + f"\n<@{user_id}>")
                    await thread.thread.send(f"<@{user_id}>")
                else:
                    forum_channel = None
                    if homework.subject.name in loaded_subject_forum_channels:
                        # Si le salon de la matière sélectionnée est déjà chargé
                        forum_channel = loaded_subject_forum_channels[homework.subject.name]
                    else:
                        # Si le salon de la matière sélectionnée n'est pas chargé
                        forum_channel = bot.get_channel(int(config["subjects"][homework.subject.name]))
                    # Vérifie que forum_channel est bien de type ForumChannel
                    if not isinstance(forum_channel, ForumChannel):
                        print(f"The channel {int(config["subjects"][homework.subject.name])} is not a forum channel. Please check the config file.")
                        continue
                    # Crée le salon du devoir et l'ajoute à la liste des salons chargés
                    generated_thread = await forum_channel.create_thread(
                        name=thread_name,
                        content=thread_description)
                    loaded_homeworks_threads[homework.subject.name][thread_description] = generated_thread
                    # Mentionne l'utilisateur si le devoir n'est pas marqué comme fait
                    if not homework.done:
                        await generated_thread.thread.send(f"Élèves concernés:\n<@{user_id}>")
                    else:
                        mention_message = await generated_thread.thread.send("Élèves concernés:")
                        await mention_message.edit(content=f"Élèves concernés:\n<@{user_id}>")
            store_homeworks_hash(user_id, [homework.description for homework in homeworks])        

bot.run(os.environ["DISCORD_TOKEN"])
