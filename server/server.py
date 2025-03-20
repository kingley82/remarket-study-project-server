import asyncio
import aiosqlite as sql
import websockets
import json
import os
import websockets.exceptions
import database
from etypes import *
from models import *

connections = {} #deviceid: websocket
# tokens = {}
users = {}       #deviceid: username
devices = {}     #username: [deviceid]

path = os.path.dirname(__file__)
db_path = os.path.join(path, "db.db")
db = database.Db(db_path)

async def echo(websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)
            payload = data[PAYLOAD]
            deviceid = data[DEVICE_ID]
            client_us = data[USERNAME]
            if data[EVENT] == AD_POST:
                print(f"New ad with title {payload[TITLE]}\n")
            else:
                print(f"Received: {message}")
            if data[EVENT] == ACCOUNT_SIGNUP:
                uname = payload[USERNAME]
                passw = payload[PASSWORD]
                async with db:
                    if await db.check_user_exists(uname):
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_USERNAME_TAKEN}}))
                    else:
                        uid = await db.create_user(uname, passw)
                        await websocket.send(json.dumps({EVENT: ACCOUNT_SIGNUP, PAYLOAD: {}}))
            if data[EVENT] == ACCOUNT_SIGNIN:
                uname = payload[USERNAME]
                passw = payload[PASSWORD]
                us_data = None
                user = None
                async with db:
                    if not await db.check_user_exists(uname):
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_USER_NOT_EXISTS}}))
                    elif not await db.valid_password(uname, passw):
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_PASSWORD}}))
                    else:
                        us_data = await db.get_user_by_name(uname)
                        user = User(us_data[0], us_data[1])
                        connections[deviceid] = websocket
                        users[deviceid] = uname
                        if uname not in devices:
                            devices[uname] = [deviceid]
                        else:
                            devices[uname].append(deviceid)
                        await websocket.send(json.dumps({EVENT: ACCOUNT_SIGNIN, PAYLOAD: {USER: user.tojson()}}))
            if data[EVENT] == AD_POST:
                title = payload[TITLE].strip()
                price = payload[PRICE]
                phone = payload[PHONE].strip()
                description = payload[DESCRIPTION].strip()
                images = list(payload[IMAGES])
                seller = payload[SELLER]
                status = payload[STATUS].strip()
                async with db:
                    if title == "" or phone == "" or description == "" or status not in ['active', 'closed'] or price < 0 or images == [] or not await db.check_user_exists_by_id(seller):
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                    else:
                        ad_id = await db.create_ad(title, price, phone, description, json.dumps(images), seller, status)
                        await websocket.send(json.dumps({EVENT: AD_POST, PAYLOAD: {ID: ad_id}}))
            if data[EVENT] == GET_AD:
                id = payload[ID]
                async with db:
                    res = await db.get_ad_by_id(id)
                    seller_res = await db.get_user_by_id(res[6])

                    ad = Ad(res, User(seller_res[0], seller_res[1]).tojson()).standartize().tojson()
                    await websocket.send(json.dumps({EVENT: GET_AD, PAYLOAD: {AD: ad}}))
            if data[EVENT] == GET_ADS:
                user_id = payload[USER]
                count = payload[COUNT]
                offset = payload[OFFSET]
                active = payload[ACTIVE]
                async with db:
                    res = await db.get_ads(user_id, count, offset, active)
                    async def standartize(res):
                        user = await db.get_user_by_id(res[6])
                        return Ad(res, User(user[0], user[1]).tojson()).standartize().tojson()
                    
                    response = [await standartize(x) for x in res]
                    await websocket.send(json.dumps({EVENT: GET_ADS, PAYLOAD: {ADS: response}}))
            if data[EVENT] == SEARCH:
                word = payload[SEARCH]
                count = payload[COUNT]
                offset = payload[OFFSET]
                async with db:
                    res = await db.search_ads(word, count, offset)
                    async def standartize(res):
                        user = await db.get_user_by_id(res[6])
                        return Ad(res, User(user[0], user[1]).tojson()).standartize().tojson()
                    response = [await standartize(x) for x in res]
                    await websocket.send(json.dumps({EVENT: GET_ADS, PAYLOAD: {ADS: response}}))
            if data[EVENT] == AD_STATUS_CHANGE:
                id = payload[ID]
                async with db:
                    res = await db.get_ad_by_id(id)
                    user = await db.get_user_by_id(res[6])
                    ad = Ad(res, User(user[0], user[1]).tojson()).standartize()
                    if ad.status == None:
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                    else:
                        if deviceid in users:
                            if users[deviceid] == client_us:
                                if ad.status == "active":
                                    await db.change_ad_status(id, "closed")
                                    await websocket.send(json.dumps({EVENT: AD_STATUS_CHANGE, PAYLOAD: {STATUS: "closed"}}))
                                else:
                                    await db.change_ad_status(id, "active")
                                    await websocket.send(json.dumps({EVENT: AD_STATUS_CHANGE, PAYLOAD: {STATUS: "active"}}))
                            else:
                                await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                        else:
                            await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == GET_DIALOG:
                member1 = payload[MEMBERS][0]
                member2 = payload[MEMBERS][1]
                async with db:
                    if deviceid in users:
                        if users[deviceid] == client_us:
                            res = await db.get_dialog_by_members(member1, member2)
                            if res == None:
                                res = await db.create_dialog(member1, member2)
                            if type(res) in [list, tuple]:
                                res = res[0]
                            res = await db.get_dialog(res)
                            user1 = await db.get_user_by_id(res[1])
                            user1 = User(user1[0], user1[1]).tojson()
                            user2 = await db.get_user_by_id(res[2])
                            user2 = User(user2[0], user2[1]).tojson()
                            d = Dialog(res[0], user1, user2, "").tojson()
                            await websocket.send(json.dumps({EVENT: GET_DIALOG, PAYLOAD: {DIALOG: d}}))
                        else:
                            await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                    else:
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == GET_MESSAGES:
                dialog = payload[DIALOG]
                if deviceid in users:
                    async with db:
                        res = await db.get_dialog(dialog)
                        uid = await db.get_user_by_name(client_us)
                        if uid[0] in [res[1], res[2]]:
                            res = await db.get_messages_from_dialog(dialog)
                            messages = []
                            for i in res:
                                sender = await db.get_user_by_id(i[3])
                                messages.append(Message(i[0], i[1], i[2], User(sender[0], sender[1]).tojson(), i[4]).tojson())
                            await websocket.send(json.dumps({EVENT: GET_MESSAGES, PAYLOAD: {MESSAGES: messages}}))
                        else:
                            await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                else:
                    await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == GET_DIALOGS:
                if deviceid in users:
                    async with db:
                        res = await db.get_user_by_name(users[deviceid])
                        uid = res[0]
                        raw_dialogs = await db.get_dialogs_of_uid(uid)
                        dialogs = {}
                        for d in raw_dialogs:
                            member1 = await db.get_user_by_id(d[1])
                            member1 = User(member1[0], member1[1]).tojson()
                            member2 = await db.get_user_by_id(d[2])
                            member2 = User(member2[0], member2[1]).tojson()
                            last_message = await db.get_last_message(d[0])
                            if last_message == None:
                                dialogs[last_message[1]] = Dialog(d[0], member1, member2, "Чат открыт").tojson()
                            else:
                                dialogs[last_message[1]] = Dialog(d[0], member1, member2, last_message[0]).tojson()
                        dialogs = list(dict(sorted(dialogs.items())).values())[::-1]
                        await websocket.send(json.dumps({EVENT: GET_DIALOGS, PAYLOAD: {DIALOGS: dialogs}}))
                else: await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == ACCOUNT_LOGOUT:
                if deviceid in users:
                    uname = users[deviceid]
                    if uname in devices:
                        devices[uname] = list(filter(lambda a: a != deviceid, devices[uname]))
                    del users[deviceid]
                    del connections[deviceid]
                    await websocket.send(json.dumps({EVENT: ACCOUNT_LOGOUT, PAYLOAD: {STATUS: OK}}))
                else: await websocket.send(json.dumps({EVENT: ACCOUNT_LOGOUT, PAYLOAD: {STATUS: ERROR}}))
            if data[EVENT] == CHANGE_NAME:
                newname = payload[USERNAME]
                if deviceid in users:
                    async with db:
                        res = await db.get_user_by_name(newname)
                        if res != None: await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_USERNAME_TAKEN}}))
                        else:
                            uname = users[deviceid]
                            await db.change_username(uname, newname)
                            res = await db.get_user_by_name(newname)
                            user = User(res[0], res[1]).tojson()
                            users[deviceid] = res[1]
                            await websocket.send(json.dumps({EVENT: CHANGE_NAME, PAYLOAD: {USER: user}}))
                else:
                    await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == CHANGE_PASSWORD:
                old_password = payload[PASSWORD][0]
                new_password = payload[PASSWORD][1]
                print(users)
                async with db:
                    if deviceid in users:
                        if users[deviceid] == client_us:
                            if await db.valid_password(client_us, old_password):
                                await db.change_password(client_us, new_password)
                                await websocket.send(json.dumps({EVENT: CHANGE_PASSWORD, PAYLOAD: {PASSWORD: new_password}}))
                            else:
                                await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_PASSWORD}}))
                        else:
                            await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                    else:
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
            if data[EVENT] == NEW_MESSAGE:
                message = payload[TEXT]
                dialog = payload[DIALOG]
                sender = payload[SENDER]
                async with db:
                    if deviceid in users:
                        if users[deviceid] == client_us:
                            res = await db.get_user_by_id(sender)
                            sender_user = User(res[0], res[1])
                            res = await db.add_message(dialog, message, sender)
                            res = await db.get_message(res)
                            msg = Message(res[0], res[1], res[2], sender_user.tojson(), res[4])
                            await websocket.send(json.dumps({EVENT: NEW_MESSAGE, PAYLOAD: {MESSAGE: msg.tojson()}}))
                            res = await db.get_dialog(msg.dialog)
                            receiver = res[1] if sender_user.id == res[2] else res[2]
                            receiver = await db.get_user_by_id(receiver)
                            receiver = receiver[1]
                            if receiver in devices:
                                for device in devices[receiver]:
                                    await connections[device].send(json.dumps({EVENT: NEW_MESSAGE, PAYLOAD: {MESSAGE: msg.tojson()}}))
                        else:
                            await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
                    else:
                        await websocket.send(json.dumps({EVENT: ERROR, PAYLOAD: {ERROR: ERROR_INVALID_REQUEST}}))
    except websockets.exceptions.ConnectionClosedError:
        pass
            #websockets.exceptions.ConnectionClosedError: no close frame received or sent
                


print("Starting server")

async def main():
    start_server = await websockets.serve(echo, "192.168.0.108", 8088, max_size=100*1024*1024)
    await start_server.wait_closed()

asyncio.run(main())