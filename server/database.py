import aiosqlite, asyncio
import time

class Db:
    def __init__(self, db_file):
        self.db_file = db_file
        self.lock = asyncio.Lock()
    
    async def __aenter__(self):
        self.db = await aiosqlite.connect(self.db_file)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.db.close()
    
    async def check_user_exists(self, username):
        async with self.lock, self.db.execute("SELECT * FROM USERS WHERE Username = ?;", (username,)) as cursor:
            res = await cursor.fetchone()
            return bool(res)
    
    async def check_user_exists_by_id(self, id):
        async with self.lock, self.db.execute("SELECT * FROM USERS WHERE ID = ?;", (id,)) as cursor:
            res = await cursor.fetchone()
            return bool(res)
    
    async def create_user(self, username, password):
        async with self.lock, self.db.execute("INSERT INTO USERS(Username, Password) VALUES (?, ?);", (username, password,)) as cursor:
            res = cursor.lastrowid
            await self.db.commit()
    
    async def valid_password(self, username, password):
        async with self.lock, self.db.execute("SELECT Password FROM USERS WHERE Username = ?;", (username,)) as cursor:
            res = await cursor.fetchone()
            return res[0] == password
    
    async def get_user_by_name(self, uname):
        async with self.lock, self.db.execute("SELECT ID, Username FROM USERS WHERE Username = ?;", (uname,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def get_user_by_id(self, id):
        async with self.lock, self.db.execute("SELECT ID, Username FROM USERS WHERE ID = ?;", (id,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def create_ad(self, title, price, phone, description, seller, status):
        async with self.lock, self.db.execute("INSERT INTO ADS(Title, Price, Phone, Description, Seller, Status) VALUES (?,?,?,?,?,?);",
                                              (title, price, phone, description, seller, status,)) as cursor:
            res = cursor.lastrowid
            await self.db.commit()
            return res
    
    async def create_images(self, ad_id, images):
        async with self.lock, self.db.execute("INSERT INTO IMAGES(Images, Ad) VALUES (?,?);", (images, ad_id,)) as cursor:
            res = cursor.lastrowid
            await self.db.commit()
            return res
            
    async def get_ad_by_id(self, id):
        async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID WHERE ADS.ID = ?;", (id,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def change_ad_status(self, id, status):
        async with self.lock, self.db.execute("UPDATE ADS SET STATUS = ? WHERE ID = ?;", (status, id,)) as cursor:
            await self.db.commit()

    async def get_ads(self, id, count, offset, onlyActive):
        #SELECT ADS.*, IMAGES.Image FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID;
        if onlyActive:
            if id == -1:
                async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID WHERE ADS.STATUS = 'active' LIMIT ?, ?;", (offset, count,)) as cursor:
                    res = await cursor.fetchall()
                    return res
            else:
                async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID WHERE (ADS.SELLER = ? AND ADS.STATUS = 'active') LIMIT ?, ?;", (id, offset, count,)) as cursor:
                    res = await cursor.fetchall()
                    return res
        else:
            if id == -1:
                async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID LIMIT ?, ?;", (offset, count,)) as cursor:
                    res = await cursor.fetchall()
                    return res
            else:
                async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID WHERE ADS.SELLER = ? LIMIT ?, ?;", (id, offset, count,)) as cursor:
                    res = await cursor.fetchall()
                    return res
    
    async def search_ads(self, word, count, offset):
        async with self.lock, self.db.execute("SELECT ADS.*, IMAGES.Images FROM ADS JOIN IMAGES ON IMAGES.Ad = ADS.ID WHERE ADS.STATUS = 'active' AND ADS.Title LIKE '%' || ? || '%' LIMIT ?, ?;", (word, offset, count,)) as cursor:
            res = await cursor.fetchall()
            return res
    
    async def get_dialog(self, id):
        async with self.lock, self.db.execute("SELECT * FROM DIALOGS WHERE ID = ?;", (id,)) as cursor:
            res = await cursor.fetchone()
            return res

    async def create_dialog(self, member1, member2):
        async with self.lock, self.db.execute("INSERT INTO DIALOGS(Member1, Member2) VALUES (?,?);", (member1, member2,)) as cursor:
            res = cursor.lastrowid
            await self.db.commit()
            return res
    
    async def add_message(self, dialog, message, sender):
        async with self.lock, self.db.execute("INSERT INTO MESSAGES(Dialog, Message, Sender, Time) VALUES (?,?,?,?);", (dialog, message, sender,int(time.time()))) as cursor:
            res = cursor.lastrowid
            await self.db.commit()
            return res
    
    async def get_message(self, messageid):
        async with self.lock, self.db.execute("SELECT * FROM MESSAGES WHERE ID = ?;", (messageid,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def get_messages_from_dialog(self, dialog):
        async with self.lock, self.db.execute("SELECT * FROM MESSAGES WHERE DIALOG = ?;", (dialog,)) as cursor:
            res = await cursor.fetchall()
            return res
    
    async def get_dialog_by_members(self, member1, member2):
        async with self.lock, self.db.execute("SELECT ID FROM DIALOGS WHERE ((Member1 = ? and Member2 = ?) or (Member1 = ? and Member2 = ?));", (member1, member2, member2, member1,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def get_dialogs_of_uid(self, uid):
        async with self.lock, self.db.execute("SELECT * FROM DIALOGS WHERE (Member1 = ? or Member2 = ?);", (uid, uid,)) as cursor:
            res = await cursor.fetchall()
            return res
    
    async def get_last_message(self, dialog_id):
        async with self.lock, self.db.execute("SELECT Message, Time FROM MESSAGES WHERE DIALOG = ? ORDER BY ID DESC LIMIT 1;", (dialog_id,)) as cursor:
            res = await cursor.fetchone()
            return res
    
    async def change_username(self, old_name, new_name):
        async with self.lock, self.db.execute("UPDATE users SET Username = ? WHERE Username = ?;", (new_name, old_name,)) as cursor:
            await self.db.commit()
            return
    
    async def change_password(self, uname, new_password):
        async with self.lock, self.db.execute("UPDATE users SET Password = ? WHERE Username = ?;", (new_password, uname,)) as cursor:
            await self.db.commit()
            return
        

    # async with self.lock, self.db.execute() as cursor: