#!/usr/bin/env python3

import os
import time
import json

import requests
import sys

CONFIG_DIRECTORY = os.path.expanduser("~/.config/ttrlauncher/")

URL = "https://www.toontownrewritten.com/api/login?format=json"

def die(reason):
    print(reason)
    exit(1)

def finish_partial_auth(r):
    while True:
        print(r['banner'])
        code = input("Code: ")
        r = requests.post(URL, data={'appToken': code, 'responseToken': r['responseToken']}).json()

        if r['success']:
            return r


def finish_queue(r):
    queueToken = r['queueToken']
    while True:
        print(r)
        print("Currently waiting in queue... Position: {}, ETA: {} seconds".format(r['position'], r['eta']))
        time.sleep(1)
        r = requests.post(URL, data={'queueToken': queueToken}).json()
        if r['success'] == "true":
            return r
        time.sleep(29)


def login(account):
    r = requests.post(URL, data={'username': account[0], 'password': account[1]}).json()

    if r['success'] == "false":
        die("Unable to login: {}".format(r['banner']))
    elif r['success'] == "partial":
        r = finish_partial_auth(r)

    if r['success'] == "delayed":
        r = finish_queue(r)
        print(r)

    if r['success'] == "true":
        os.environ['TTI_GAMESERVER'] = r['gameserver']
        os.environ['TTI_PLAYCOOKIE'] = r['cookie']
        os.system("TTREngine")
        #os.system('python -m toontown.toonbase.ClientStart')
    else:
        die('Somehow we got here, not sure how ...')


login(['email@domain.com', 'password'])
