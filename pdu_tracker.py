import requests
import re
from datetime import datetime, timedelta
import time
import os
import config

WEBHOOK_URL = config.DISCORD_WEBHOOK
PDU_FILE = 'pmp_pdu_count.txt'
LAST_MSG_FILE = 'pmp_last_msg_id.txt'
PE_LOG_FILE = 'pe_course_log.txt'

CERTIFICATIONS = [
    {
        'name': 'PMP',
        'renewal_date': '2027-08-24',
        'total_pdus': 60,
        'tracks_pdus': True
    },
    {
        'name': 'PE',
        'renewal_date': '2027-09-30',
        'tracks_pdus': False
    },
    {
        'name': 'CEM',
        'renewal_date': '2027-12-31',
        'tracks_pdus': False
    }
]


def load_pdu_count():
    if os.path.exists(PDU_FILE):
        with open(PDU_FILE, 'r') as file:
            try:
                return int(file.read().strip())
            except ValueError:
                return 2
    return 2


def save_pdu_count(pdu_count):
    with open(PDU_FILE, 'w') as file:
        file.write(str(pdu_count))


def load_last_message_id():
    if os.path.exists(LAST_MSG_FILE):
        with open(LAST_MSG_FILE, 'r') as file:
            return file.read().strip()
    return None


def save_last_message_id(message_id):
    with open(LAST_MSG_FILE, 'w') as file:
        file.write(str(message_id))


def append_pe_log(entry):
    """Append a PE course entry to the log file."""
    line = f"{entry['date']} - {entry['course']} - {entry['hours']}h\n"
    with open(PE_LOG_FILE, 'a') as file:
        file.write(line)


def prompt_for_pdu_count(current_pdu):
    print(f'Current PMP PDUs: {current_pdu}/{CERTIFICATIONS[0]["total_pdus"]}')
    user_input = input('Enter your current number of PMP PDUs (or any text to keep the same): ').strip()
    if user_input.isdigit():
        new_pdu = int(user_input)
        print(f'Updated PMP PDUs to {new_pdu}.')
        return new_pdu
    else:
        print('Keeping the current PMP PDU count.')
        return current_pdu


def parse_pdu_message(content: str) -> int:
    """Return number of PDUs added in the given message."""
    match = re.search(r"added\s+(\d+)\s+pdu", content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def parse_pe_message(content: str):
    """Return a PE course entry dict if the message contains one."""
    pattern = (
        r"PE\s+(?P<hours>\d+(?:\.\d+)?)\s+(?P<course>.+?)\s+(?P<date>\d{4}-\d{2}-\d{2})"
    )
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return {
            "hours": float(match.group("hours")),
            "course": match.group("course").strip(),
            "date": match.group("date"),
        }
    return None


def scan_discord_for_updates(last_message_id=None):
    """Scan Discord messages for PDU and PE updates."""
    headers = {"authorization": config.DISCORD_AUTH}
    url = (
        f"https://discord.com/api/v9/channels/{config.CHANNELID}/messages?limit=100"
    )
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch discord messages: {response.status_code}")
        return 0, last_message_id, []

    messages = response.json()
    messages.sort(key=lambda m: int(m["id"]))

    pdu_delta = 0
    new_last_id = last_message_id
    pe_entries = []

    for msg in messages:
        if last_message_id and int(msg["id"]) <= int(last_message_id):
            continue
        content = msg.get("content", "")
        added = parse_pdu_message(content)
        if added:
            pdu_delta += added
            new_last_id = msg["id"]

        pe_entry = parse_pe_message(content)
        if pe_entry:
            pe_entries.append(pe_entry)
            new_last_id = msg["id"]

    return pdu_delta, new_last_id, pe_entries


def send_discord_alert(cert_name, days_left, renewal_date, current_pdu=None, total_pdus=None):
    if current_pdu is not None and total_pdus is not None:
        pdus_needed = total_pdus - current_pdu
        message = (
            f'\U0001F514 Reminder: Your **{cert_name}** certification expires in **{days_left} days** (Deadline: {renewal_date}).\n'
            f'You currently have **{current_pdu}/{total_pdus} PDUs**. You need **{pdus_needed} more PDUs** to renew.'
        )
    else:
        message = f'\U0001F514 Reminder: Your **{cert_name}** certification expires in **{days_left} days** (Deadline: {renewal_date}).'

    payload = {'content': message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 204:
        print(f'Successfully sent reminder for {cert_name}.')
    else:
        print(f'Failed to send reminder for {cert_name}. Status code: {response.status_code}')


def check_certifications():
    today = datetime.today()
    current_pdu = load_pdu_count()
    last_msg_id = load_last_message_id()

    pdu_delta, new_last_id, pe_entries = scan_discord_for_updates(last_msg_id)
    if pdu_delta:
        current_pdu += pdu_delta
        print(f'Added {pdu_delta} PDUs from Discord messages.')
        save_pdu_count(current_pdu)
    for entry in pe_entries:
        append_pe_log(entry)
        print(
            f"Logged PE course '{entry['course']}' on {entry['date']} for {entry['hours']} hours."
        )
    if (pdu_delta or pe_entries) and new_last_id:
        save_last_message_id(new_last_id)

    for cert in CERTIFICATIONS:
        renewal_date = datetime.strptime(cert['renewal_date'], '%Y-%m-%d')
        days_left = (renewal_date - today).days
        if cert['tracks_pdus']:
            send_discord_alert(cert['name'], days_left, cert['renewal_date'], current_pdu, cert['total_pdus'])
        else:
            send_discord_alert(cert['name'], days_left, cert['renewal_date'])

    new_pdu = prompt_for_pdu_count(current_pdu)
    save_pdu_count(new_pdu)


if __name__ == '__main__':
    while True:
        check_certifications()
        time.sleep(30 * 86400)
