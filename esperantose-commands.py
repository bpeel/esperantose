#!/usr/bin/python3

import urllib.request
import json
import io
import gzip
import html
import sys
import time
import os

conf_dir = os.path.expanduser("~/.esperantose")
update_id_file = os.path.join(conf_dir, "update_id")
apikey_file = os.path.join(conf_dir, "apikey")

with open(apikey_file, 'r', encoding='utf-8') as f:
    apikey = f.read().rstrip()

urlbase = "https://api.telegram.org/bot" + apikey + "/"
get_updates_url = urlbase + "getUpdates"
answer_inline_query_url = urlbase + "answerInlineQuery"

try:
    with open(update_id_file, 'r', encoding='utf-8') as f:
        last_update_id = int(f.read().rstrip())
except FileNotFoundError:
    last_update_id = None

class GetUpdatesException(Exception):
    pass

class ProcessQueryException(Exception):
    pass

def save_last_update_id(last_update_id):
    with open(update_id_file, 'w', encoding='utf-8') as f:
        print(last_update_id, file=f)

def is_valid_update(update, last_update_id):
    try:
        update_id = update["update_id"]
        if not isinstance(update_id, int):
            raise GetUpdatesException("Unexpected response from getUpdates "
                                      "request")
        if last_update_id is not None and update_id <= last_update_id:
            return False

        if 'inline_query' not in update:
            return False

        query = update['inline_query']
        if (not isinstance(query['id'], str) or
            not isinstance(query['query'], str)):
            raise GetUpdatesException("Unexpected response from getUpdates "
                                      "request")
    except KeyError as e:
        raise GetUpdatesException(e)

    return True

def get_updates(last_update_id):
    args = {
        'timeout': 60 * 5,
        'allowed_updates': ['inline_query']
    }

    if last_update_id is not None:
        args['offset'] = last_update_id + 1

    try:
        req = urllib.request.Request(get_updates_url,
                                     json.dumps(args).encode('utf-8'))
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        rep = json.load(io.TextIOWrapper(urllib.request.urlopen(req), 'utf-8'))
    except urllib.error.URLError as e:
        raise GetUpdatesException(e)
    except json.JSONDecodeError as e:
        raise GetUpdatesException(e)

    try:
        if rep['ok'] is not True or not isinstance(rep['result'], list):
            raise GetUpdatesException("Unexpected response from getUpdates "
                                      "request")
    except KeyError as e:
        raise GetUpdatesException(e)
        
    if rep['ok'] is not True:
        raise Exception("sendMessage request failed")

    updates = [x for x in rep['result'] if is_valid_update(x, last_update_id)]
    updates.sort(key = lambda x: x['update_id'])
    return updates

def get_se_query(url):
    u = urllib.request.urlopen(url)
    g = gzip.GzipFile(mode='rb', fileobj=u)
    t = io.TextIOWrapper(g, 'utf-8')
    return json.load(t)

def entry_to_message(entry):
    link = entry["link"]
    title = html.unescape(entry["title"])
    return {
        'type': 'article',
        'id': str(entry['question_id']),
        'title': title,
        'input_message_content': {
            'message_text': "{}\n{}".format(title, link)
        },
        'url': link,
        'hide_url': True
    }

def process_query(query_id, query_text):
    query_text = query_text.strip()

    if len(query_text) == 0:
        query_url = ("https://api.stackexchange.com/2.2/questions?"
                     "order=desc&"
                     "sort=activity&"
                     "site=esperanto&"
                     "pagesize=5")
    else:
        query_url = ("https://api.stackexchange.com/2.2/search?"
                     "order=desc&"
                     "sort=relevance&"
                     "site=esperanto&"
                     "pagesize=5&"
                     "intitle={}").format(urllib.parse.quote_plus(query_text))

    try:
        results = get_se_query(query_url)
    except urllib.error.URLError as e:
        raise ProcessQueryException(e)
    except json.JSONDecodeError as e:
        raise ProcessQueryException(e)

    try:
        results = [entry_to_message(entry) for entry in results['items']]
    except KeyError as e:
        raise ProcessQueryException(e)

    args = {
        'inline_query_id': query_id,
        'results': results
    }

    try:
        req = urllib.request.Request(answer_inline_query_url,
                                     json.dumps(args).encode('utf-8'))
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        rep = json.load(io.TextIOWrapper(urllib.request.urlopen(req), 'utf-8'))
    except urllib.error.URLError as e:
        raise ProcessQueryException(e)
    except json.JSONDecodeError as e:
        raise ProcessQueryException(e)

    try:
        if rep['ok'] is not True:
            raise ProcessQueryException("Unexpected response from getUpdates "
                                      "request")
    except KeyError as e:
        raise ProcessQueryException(e)

while True:
    try:
        updates = get_updates(last_update_id)
    except GetUpdatesException as e:
        print("{}".format(e), file=sys.stderr)
        # Delay for a bit before trying again to avoid DOSing the server
        time.sleep(60)
        continue

    for update in updates:
        last_update_id = update['update_id']
        query = update['inline_query']

        try:
            process_query(query['id'], query['query'])
        except ProcessQueryException as e:
            print("{}".format(e), file=sys.stderr)
            time.sleep(30)
            break

        save_last_update_id(last_update_id)
