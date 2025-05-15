#!/usr/bin/python3
import argparse
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime
import imaplib
import email
import json
import locale
import re
import sys

strReactionHelp = """
 - 😎 zur Kenntnis genommen
 - ✔️ wurde beantwortet `@<name>`
 - 🔜 wird beantwortet `@<name>`
 - 📤 wurde weitergeleitet *<target>*
 - ‼️ Redebedarf in der Sitzung
 - 🗑️ /dev/null
"""

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def load_config(path):
    """Load configuration from a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='IMAP Email Scanner')
    parser.add_argument(
        '--since',
        type=str,
        help='Only fetch emails since this date (format: YYYY-MM-DD)',
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to the configuration JSON file',
    )
    return parser.parse_args()

def decode_mime_words(s):
    """Decode MIME encoded-words (like =?UTF-8?B?...?=) in headers."""
    if s is None:
        return ""
    decoded_parts = decode_header(s)
    return ''.join(
        part.decode(encoding or 'utf-8', errors='replace') if isinstance(part, bytes) else part
        for part, encoding in decoded_parts
    )

def prepare_mails(imap_server, start_date):
    # find all emails in inbox
    typ, data = imap_server.search(None, 'ALL')
    if typ != 'OK':
        eprint("Failed to search mailbox.")
        return
    
    # fetch all headers
    uids = data[0].split()
    uid_range = b','.join(uids)
    typ, data = imap_server.fetch(uid_range, '(BODY.PEEK[])')
    if typ != 'OK':
        eprint("Failed to fetch messages.")
        return

    # filter mails
    emails = []
    rxStripHtml = re.compile(r"<style.+?</style>|<.+?>", re.DOTALL)
    rxStripEmptyLines = re.compile(r"\n\s*\n+", re.MULTILINE)
    rxStripQuote = re.compile(r"^\s*>.+?$", re.MULTILINE)
    rxStripFwd = re.compile(r"\-{16,}.+$", re.DOTALL)
    rxMaskMarkdown = re.compile(r"^\s*(#|\-|~)", re.MULTILINE)
    for uid_info, header_bytes in data[::2]:
        # fetch infos
        uid = uid_info.decode().split()[0]
        message = email.message_from_bytes(header_bytes)
        
        # FILTER by date
        date = parsedate_to_datetime(message.get("Date"))
        date = date.replace(tzinfo=None)
        if date < start_date: continue

        # FILTER by recipient
        to_header = decode_mime_words(message.get("To"))
        recipients = [addr.lower() for name, addr in getaddresses([to_header or ""])]
        if not "fsi@fsi.uni-tuebingen.de".lower() in recipients: continue
        
        # handle multipart mails
        body = ""
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = part.get('Content-Disposition')
                try:
                    # Only include text parts
                    if (content_type == "text/plain" or content_type == "text/html") and not content_disposition:
                        body += part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='replace')
                except Exception as e:
                    print(f"Error decoding body part: {e}")
        else:
            body = message.get_payload(decode=True).decode(message.get_content_charset() or 'utf-8', errors='replace')
        
        # reformat body nicely
        body = re.sub(rxMaskMarkdown, lambda m: f"\\{m.group(1)}", body) # mask markdown 
        body = re.sub(rxStripHtml, "", body) # strip html tags
        body = re.sub(rxStripQuote, "", body) # strip quotes
        #body = re.sub(rxStripFwd, "", body) # strip fwd parts
        body = re.sub(rxStripEmptyLines, "\n\n", body) # strip multiple empty lines
        body = body.strip()
        if len(body) > 2000:
            body = body[:2000] + "...\n**Der restliche Text dieser Nachricht wurde gekürzt.**"
        

        # at this point, only relevant mails are left
        # so we want to save them
        emails.append({
            "uid": uid, 
            "date": date, 
            "from": re.sub(rxStripHtml, "", decode_mime_words(message.get("From"))),
            "subject": decode_mime_words(message.get("Subject")),
            "body": body})
    return emails

def format_mails(mails):
    str = []
    for num, m in enumerate(mails):
        str.append(f"<details><summary><code>#{num:03d}</code> [{m['date']:%Y-%m-%d}] <b>{m['from']}</b><br/>{m['subject']}</summary>")
        str.append(f"<blockquote>{m['body']}</blockquote>")
        str.append("</details>")
        str.append("")
        str.append(f"<!-- #{num:03d} -->")
        str.append("**Reaktion:** 🚨 TODO ")
        str.append("")
        str.append("---")
    return "\n".join(str)


def main():
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
    args = parse_args()

    # Process the --since argument
    now_date = datetime.now()
    if args.since:
        try:
            start_date = datetime.strptime(args.since, '%Y-%m-%d')
        except ValueError:
            eprint("Invalid date format. Please use YYYY-MM-DD.")
            return
    else:
        start_date = now_date - timedelta(days=7)  # Default: last 7 days
    
    # load json config
    config = load_config(args.config) #TODO: error handling?

    # connect to server
    imap_server = imaplib.IMAP4_SSL(host=config["mail"]["imapserv"])
    imap_server.login(config["mail"]["username"], config["mail"]["password"])
    imap_server.select(config["mail"]["mailbox"]) #TODO: provide default value

    # prepare and format mails
    mails = prepare_mails(imap_server, start_date)
    formatted_mails = format_mails(mails)
    eprint("total_mail_len = " + str(len(formatted_mails)))

    # generate full output
    next_meeting = now_date + timedelta(days=7)
    output = []
    output.append(f"# Mails für die [Sitzung {now_date:%Y-%m-%d}](https://pad.fsi.uni-tuebingen.de/fsi-sitzung-{now_date:%Y-%m-%d})")
    output.append(f"Dieses Pad enthält Mails seit {start_date:%Y-%m-%d}.")
    output.append("")
    output.append(f"Letztes Mail-Pad: https://pad.fsi.uni-tuebingen.de/fsi-sitzung-{start_date:%Y-%m-%d}-mails")
    output.append(f"Nächstes Mail-Pad: https://pad.fsi.uni-tuebingen.de/fsi-sitzung-{next_meeting:%Y-%m-%d}-mails")
    output.append("")
    output.append("Generiert von `fsi-mailfetch.py` ([Source Code](https://github.com/fsi-tue/mailfetch))")
    output.append(":::info")
    output.append("**Mögliche Reaktionen** für Copy/Paste")
    output.append(strReactionHelp)
    output.append(":::")
    output.append("---")
    output.append(formatted_mails)

    print("\n".join(output))
    return 

if __name__ == '__main__':
    main()