#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import json
import pandas as pd
import numpy as np
import datetime
import argparse
from random import randint
from langdetect import *

parser = argparse.ArgumentParser()
parser.add_argument("-ownName", dest='ownName', type=str, help="name of the owner of the chat logs, written as in the logs", required=True)
parser.add_argument('-f','-filePath', dest='filePath', help='Facebook chat log file (HTML file)', default='raw/Hangouts.json')
parser.add_argument("-max", "-maxExportedMessages", dest='maxExportedMessages', type=int, default=1000000, help="maximum number of messages to export")
args = parser.parse_args()

maxExportedMessages = args.maxExportedMessages
ownName = args.ownName
filePath = args.filePath

print('Parsing JSON file...')
archive = json.load(open(filePath))

names = {}
def idToName(id):
    if id in names:
        return names[id]
    else:
        return None

def saveNameForId(name, id):
    if not id in names:
        names[id] = name
    elif names[id] != name:
        print('Assuming', name, 'is', names[id])

data = []
conversationId = ""
conversationWithId = ""
conversationWithName = ""

print('Extracting messages...')
for state in archive["conversation_state"]:

    if state['conversation_state']['conversation']['type'] == 'GROUP':
        print('Can\'t handle groups yet, skipping')
        continue

    if "conversation_id" in state:
        conversationId = state["conversation_id"]["id"]

    if "conversation" in state["conversation_state"]:
        for participant in state["conversation_state"]["conversation"]["participant_data"]:
            if "fallback_name" in participant:
                saveNameForId(participant["fallback_name"], participant["id"]["gaia_id"])

    for event in state["conversation_state"]["event"]:
        timestamp = int(event["timestamp"])

        if "conversation_id" in event:
            conversationId = event["conversation_id"]["id"]

        if "chat_message" in event and "segment" in event["chat_message"]["message_content"]:
            content = event["chat_message"]["message_content"]
            text = content["segment"][0]["text"]
            conversationId = event["conversation_id"]["id"]
            senderId = event["sender_id"]["chat_id"]

            participants = state["conversation_state"]["conversation"]["current_participant"]

            if len(participants) == 2:
                for participant in participants:
                    if idToName(participant["gaia_id"]) != ownName:
                        conversationWithId = participant["gaia_id"]

                if idToName(senderId)!=None or idToName(conversationWithId)!=None:
                    if idToName(senderId) != ownName and senderId != conversationWithId:
                        print(idToName(senderId), 'in conversation with', idToName(conversationWithId), '!')
                        print('Parsing error, is your ownId correct?')
                        print('******************************')
                        print('DATA DUMP:')
                        print('******************************')
                        print(names)
                        print('******************************')
                        print(data)
                        print('******************************')
                        print('Sender id that crashed it:', senderId)

                        exit(0)

                    # saves the message
                    timestamp = timestamp/1000000
                    data += [[timestamp, conversationId, idToName(conversationWithId), idToName(senderId), text]]

                else:
                    # unknown sender
                    print("No senderName for either senderId", senderId, conversationWithId)

                if len(data) >= maxExportedMessages:
                    break

print(len(data), 'messages parsed.')

print('Converting to DataFrame...')
df = pd.DataFrame(index=np.arange(0, len(data)))
df = pd.DataFrame(data)
df.columns = ['timestamp', 'conversationId', 'conversationWithName', 'senderName', 'text']
df['platform'] = 'hangouts'

print('Detecting languages...')
df['language'] = 'unknown'
for name, group in df.groupby(df.conversationWithName):
    sample = ''
    df2 = df[df.conversationWithName == name].dropna()

    if len(df2)>10:
        for x in range(0, min(len(df2), 100)):
            sample = sample + df2.iloc[randint(0, len(df2)-1)]['text']

        print('\t', name, detect(sample))
        df.loc[df.conversationWithName == name, 'language'] = detect(sample)

print('Computing dates...')
df['datetime'] = df['timestamp'].apply(lambda x: datetime.datetime.fromtimestamp(float(x)).toordinal())
print(df.head())

print('Saving to pickle file...')
df.to_pickle('data/hangouts.pkl')