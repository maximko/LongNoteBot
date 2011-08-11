#! /usr/bin/python
# -*- coding:utf-8 -*-

# create database longnote CHARACTER SET utf8 COLLATE utf8_general_ci
#
# create table data (id INT NOT NULL AUTO_INCREMENT,
#                    alias VARCHAR(255),  jabberid VARCHAR(200) NOT NULL,
#                    text MEDIUMTEXT, PRIMARY KEY (jabberid, id));

from xmpp import *
import ConfigParser
import MySQLdb
import re

class DataBase:
    connection = None
    def __init__(self, host, user, passwd, database):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.database = database
    
    def connect(self):
        self.connection = MySQLdb.connect(host=self.host, user=self.user,
                                          passwd=self.passwd, db=self.database,
                                          use_unicode = 1, charset='utf8')

    def cursor(self):
        try:
            self.connection.ping()
            return self.connection.cursor()
        except (AttributeError, MySQLdb.OperationalError), e:
            print "Connect to Database... [%s]" % e
            self.connect()
            return self.connection.cursor()


def mainf():
    global db
    global bot
    config = ConfigParser.ConfigParser()
    config.read('longnote.conf')
    jabberID = JID(config.get('Account', 'jid'))
    bot = Client(jabberID.getDomain(), debug=[])
    bot.connect()
    bot.auth(jabberID.getNode(), config.get('Account', 'pass'), config.get('Account', 'res'))
    bot.sendInitPresence()
    bot.send(Presence(show="chat", status=config.get('Strings', 'status')))
    bot.RegisterHandler('presence',presenseh)
    bot.RegisterHandler('message', messageh)
    db = DataBase(config.get('MySQL', 'host'), config.get('MySQL', 'user'),
                  config.get('MySQL', 'pass'), config.get('MySQL', 'database'))
    while 1:
        bot.Process(1)

def presenseh(connection, presense):
    if presense.getType()=='subscribe':
        connection.send(Presence(presense.getFrom(), "subscribed"))
    elif presense.getType()=='unsubscribe':
        connection.send(Presence(presense.getFrom(), "unsubscribed"))

def messageh(connection, message):
    if (message.getBody() == "all"):
        sendall(message)
    elif (message.getBody()[:3] == "del"):
        delete(message)
    elif (message.getBody()[0] == "#"):
        show(message)
    elif (message.getBody() == "HELP"):
        sendhelp(message)
    else:
        add(message)

def sendall(message):
    c = db.cursor()
    c.execute("""select id, text from data where jabberid = %s""",
                                           re.sub(r"\/.*", "", str(message.getFrom())))
    data = c.fetchall()
    msg = "Все записи:"
    for row in data:
        msg += "\n#" + str(row[0]) + " --> " + row[1].encode('utf-8')
    bot.send(Message(message.getFrom(), msg))
    c.close()

def add(message):
    c = db.cursor()
    if (c.execute("""insert into data values(NULL, %s, %s, %s)""",
                ("", re.sub(r"\/.*", "", str(message.getFrom())), message.getBody())) == 1):
        c.execute("""select id from data where jabberid = %s order by id desc limit 1;""",
                                                re.sub(r"\/.*", "", str(message.getFrom())))
        num = c.fetchone()
        bot.send(Message(message.getFrom(), "Заметка #" + str(num[0]) + " добавлена."))
    else:
        bot.send(Message(message.getFrom(), "Внезапно возникла ошибка."))
    c.close()

def delete(message):
    c = db.cursor()
    if (len(message.getBody()) > 5):
        if (c.execute("""delete from data where jabberid = %s and id = %s""",
             (re.sub(r"\/.*", "", str(message.getFrom())), str(message.getBody()[5:]))) == 1):
            bot.send(Message(message.getFrom(), "Удалено."))
        else:
            bot.send(Message(message.getFrom(), "При удалении возникла ошибка."))
    else:
        bot.send(Message(message.getFrom(), "Использование: del #<id>"))
    c.close()

def show(message):
    c = db.cursor()
    if (len(message.getBody()) != 1):
        if (c.execute("""select text from data where jabberid = %s and id = %s""",
              (re.sub(r"\/.*", "", str(message.getFrom())), message.getBody()[1:])) == 1):
            msg = "Заметка " + message.getBody().encode('utf-8') + " --> "
            data = c.fetchall()
            for row in data:
                msg += row[0].encode('utf-8')
            bot.send(Message(message.getFrom(), msg))
        else:
            bot.send(Message(message.getFrom(), "Неверный номер заметки."))
    else:
        bot.send(Message(message.getFrom(), "Использование: #<id>"))
    c.close()
        
def sendhelp(message):
    helpmsg = """Для добавления заметки просто отошлите ее боту.
#<номер заметки> - получение заметки по номеру (#123)
all - вывод всех заметок с номерами
del #<номер заметки> - удаление заметки (del #123)"""
    bot.send(Message(message.getFrom(), helpmsg))

if __name__ == '__main__':
    mainf()
