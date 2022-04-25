import requests
import config


def send_discord_alert(message):

    discord_message_to_push = {"content": message}

    response = requests.post(config.DISCORD_WEBHOOK, json=discord_message_to_push)

    return
