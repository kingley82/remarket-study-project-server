from json import JSONEncoder, loads

class Encoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
    
    def tojson(self):
        return self.default(self)

class User(Encoder):
    def __init__(self, id, name):
        self.id = id
        self.username = name

class Ad(Encoder):
    def __init__(self, raw, user):
        if raw == None:
            self.status = None
        else:
            self.id = raw[0]
            self.title = raw[1]
            self.price = raw[2]
            self.phone = raw[3]
            self.description = raw[4]
            self.seller = user
            self.status = raw[6] #active/closed
            self.images = raw[7]
    def standartize(self):
        self.images = loads(self.images)
        return self

class Message(Encoder):
    def __init__(self, id, dialog, message, sender, time):
        self.id = id
        self.dialog = dialog
        self.message = message
        self.sender = sender
        self.time = time

class Dialog(Encoder):
    def __init__(self, id, member1, member2, last_message):
        self.id = id
        self.member1 = member1
        self.member2 = member2
        self.last_message = last_message