#!/usr/bin/python3

import xml.etree.ElementTree as ET
import urllib.request
import pyrfc3339
import os.path
import json

conf_dir = os.path.expanduser("~/.esperantose")
timestamp_file = os.path.join(conf_dir, "timestamp")
apikey_file = os.path.join(conf_dir, "apikey")

with open(apikey_file, 'r', encoding='utf-8') as f:
    apikey = f.read().rstrip()

urlbase = "https://api.telegram.org/bot" + apikey + "/"
send_message_url = urlbase + "sendMessage"
channel_name = "@esperanto_se_demandoj"

try:
    with open(timestamp_file, 'r', encoding='utf-8') as f:
        last_timestamp = pyrfc3339.parse(f.read().rstrip())
except FileNotFoundError:
    last_timestamp = None

u = urllib.request.urlopen("http://esperanto.stackexchange.com/feeds")
d = ET.parse(u)

latest_timestamp = None

for entry in d.getroot().findall('./{http://www.w3.org/2005/Atom}entry'):
    published = entry.find("./{http://www.w3.org/2005/Atom}published")

    if published is None:
        continue

    timestamp = pyrfc3339.parse("".join(published.itertext()))

    if last_timestamp is not None and timestamp <= last_timestamp:
        continue

    link = entry.find("./{http://www.w3.org/2005/Atom}link")
    title = entry.find("./{http://www.w3.org/2005/Atom}title")

    if link is None or title is None or 'href' not in link.attrib:
        continue

    link_url = link.attrib['href']
    title_text = "".join(title.itertext())

    args = {
        'chat_id': channel_name,
        'text': title_text + "\n" + link_url
    }

    req = urllib.request.Request(send_message_url,
                                 json.dumps(args).encode('utf-8'))
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    rep = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    if rep['ok'] is not True:
        raise Exception("sendMessage request failed")

    if latest_timestamp is None or timestamp > latest_timestamp:
        latest_timestamp = timestamp

if latest_timestamp is not None:
    with open(timestamp_file, 'w', encoding='utf-8') as f:
        print(pyrfc3339.generate(latest_timestamp), file=f)
