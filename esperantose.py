#!/usr/bin/python3

import urllib.request
import datetime
import time
import os.path
import json
import io
import gzip
import html

def has_parts(entry):
    for part in ["link", "title", "creation_date"]:
        if part not in entry:
            return False

    return True

def get_se_query(url):
    u = urllib.request.urlopen(url)
    g = gzip.GzipFile(mode='rb', fileobj=u)
    t = io.TextIOWrapper(g, 'utf-8')
    return json.load(t)

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
        last_timestamp = int(f.read().rstrip())
except FileNotFoundError:
    d = datetime.datetime.now()
    last_timestamp = int(time.mktime(d.timetuple())) - 48 * 60 * 60

query_url = ("https://api.stackexchange.com/2.2/questions?"
             "order=asc&"
             "sort=creation&"
             "site=esperanto&"
             "pagesize=10&"
             "fromdate={}").format(last_timestamp)

d = get_se_query(query_url)

latest_timestamp = None

for entry in d['items']:
    if not has_parts(entry):
        continue

    timestamp = int(entry["creation_date"])

    if last_timestamp is not None and timestamp <= last_timestamp:
        continue

    link = entry["link"]
    title = html.unescape(entry["title"])

    args = {
        'chat_id': channel_name,
        'text': title + "\n" + link
    }

    req = urllib.request.Request(send_message_url,
                                 json.dumps(args).encode('utf-8'))
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    rep = json.load(io.TextIOWrapper(urllib.request.urlopen(req), 'utf-8'))
    if rep['ok'] is not True:
        raise Exception("sendMessage request failed")

    if latest_timestamp is None or timestamp > latest_timestamp:
        latest_timestamp = timestamp

if latest_timestamp is not None:
    with open(timestamp_file, 'w', encoding='utf-8') as f:
        print(latest_timestamp, file=f)
