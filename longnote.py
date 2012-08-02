#!/usr/bin/python
# -*- coding:utf-8 -*-
#
# v2.0
#
# create database longnote CHARACTER SET utf8 COLLATE utf8_general_ci
#
# create table data (id INT NOT NULL AUTO_INCREMENT,
#                    alias VARCHAR(255),  jabberid VARCHAR(200) NOT NULL,
#                    text MEDIUMTEXT, category varchar(255) DEFAULT NULL,
#                    PRIMARY KEY (jabberid, id));
#
# Колонка 'alias' в этой версии не используется.

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
            print "Connecting to Database... [%s]" % e
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
    if (message.getBody() != None):
        m = message.getBody()
        if (m[0] == ":"):
            if (m[:2] == ":a"):
                sendall(message)
            elif (m[:4] == ":rml"):
                deletelast(message)
            elif (m[:3] == ":rm"):
                delete(message)
            elif (m[:3] == ":mv"):
                move(message)
            elif (re.match("^:\d+$", m) != None):
                show(message)
            else:
                bot.send(Message(message.getFrom(), "Нет такой команды. HELP - список команд."))

        elif (message.getBody() == "HELP"):
                sendhelp(message)
        else:
            add(message)

def sendall(message):
    c = db.cursor()
    match = re.match(r":a @(.+)?", message.getBody())
    if (match != None):
        if (match.groups()[0] != None):
            notes = True
            c.execute("""select id, text, category from data where jabberid = %s and category = %s""",
                     (re.sub(r"\/.*", "", str(message.getFrom())), match.groups()[0]))
        else:
            notes = False
	    c.execute("""select category from data where jabberid = %s group by category""",
                      re.sub(r"\/.*", "", str(message.getFrom())))
    else:
	notes = True
        c.execute("""select id, text, category from data where jabberid = %s""",
                                           re.sub(r"\/.*", "", str(message.getFrom())))

    data = c.fetchall()
    if notes:    
        msg = "Все записи:"
        for row in data:
            msg += "\n#" + str(row[0]) + " @" + enc(row[2]) + " --> " + enc(row[1])
    else:
        msg = "Все категории:"
        for row in data:
            msg += "\n@" + enc(row[0])    

    bot.send(Message(message.getFrom(), msg))
    c.close()

def add(message):
    c = db.cursor()
    match = re.match(r"^@(\S+)? (.+)", message.getBody())
    if (match != None and match.groups()[0] != None):
        msg = match.groups()[1]
        cat = match.groups()[0]
    else:
        msg = message.getBody()
        cat = "default"       
    if (c.execute("""insert into data values(NULL, %s, %s, %s, %s)""",
                ("", re.sub(r"\/.*", "", str(message.getFrom())), msg, cat))):
        c.execute("""select id from data where jabberid = %s order by id desc limit 1;""",
                                                re.sub(r"\/.*", "", str(message.getFrom())))
        num = c.fetchone()
        bot.send(Message(message.getFrom(), "Заметка #" + str(num[0]) + " добавлена."))
    else:
        bot.send(Message(message.getFrom(), "Внезапно возникла ошибка."))
    c.close()

def delete(message):
    c = db.cursor()
    if (len(message.getBody()) > 4):
        if (c.execute("""delete from data where jabberid = %s and id = %s""",
             (re.sub(r"\/.*", "", str(message.getFrom())), str(message.getBody()[3:])))):
            bot.send(Message(message.getFrom(), "Удалено."))
        else:
            bot.send(Message(message.getFrom(), "При удалении возникла ошибка."))
    else:
        bot.send(Message(message.getFrom(), "Использование: :rm <id>"))
    c.close()

def deletelast(message):
    c = db.cursor()
    if (c.execute("""delete from data where jabberid = %s order by id desc limit 1""", 
                  re.sub(r"\/.*", "", str(message.getFrom())))):
        bot.send(Message(message.getFrom(), "Удалено."))
    else:
        bot.send(Message(message.getFrom(), "При удалении возникла ошибка."))
    c.close()

def show(message):
    c = db.cursor()
    if (len(message.getBody()) != 1):
        if (c.execute("""select text, category from data where jabberid = %s and id = %s""",
              (re.sub(r"\/.*", "", str(message.getFrom())), message.getBody()[1:]))):
            data = c.fetchone()
            msg = "Заметка #%s @%s --> %s" % (enc(message.getBody()[1:]), enc(data[1]), enc(data[0]))
            bot.send(Message(message.getFrom(), msg))
        else:
            bot.send(Message(message.getFrom(), "Неверный номер заметки."))
    else:
        bot.send(Message(message.getFrom(), "Использование: :<id>"))
    c.close()

def move(message):
    c = db.cursor()
    if (len(message.getBody()) > 4):
        match = re.match(r"^:mv #(\d+)? @(\S+)?$", message.getBody())
        match2 = re.match(r"^:mv @(\S+)? @(\S+)?$", message.getBody())
        if (match != None):
            ID = match.groups()[0]
            cat = match.groups()[1]
            if (ID != None and cat != None):
                if (c.execute("""update data set category = %s where jabberid = %s and id = %s""", (cat, re.sub(r"\/.*", "", str(message.getFrom())), ID))):
                    bot.send(Message(message.getFrom(), "Перемещено."))
                else:
                    bot.send(Message(message.getFrom(), "Ошибка."))
        elif (match2 != None):
            old = match2.groups()[0]   
            new = match2.groups()[1]
            if (old != None and new != None):
                if (c.execute("""update data set category = %s where jabberid = %s and category = %s""", (new, re.sub(r"\/.*", "", str(message.getFrom())), old))):
                    bot.send(Message(message.getFrom(), "Переименовано."))
                else:
                    bot.send(Message(message.getFrom(), "Ошибка."))
        else:
            bot.send(Message(message.getFrom(), "Использование: :mv @<old> @<new> или :mv #<id> @<category>"))    
    else:
        bot.send(Message(message.getFrom(), "Использование: :mv @<old> @<new> или :mv #<id> @<category>"))
        
def sendhelp(message):
    helpmsg = """Для добавления заметки просто отошлите ее боту.
:<номер заметки> - получение заметки по номеру (:123)
:a - вывод всех заметок с номерами
:a @ - вывод всех категорий
:a @<category> - вывод всех заметок категории
:rm <номер заметки> - удаление заметки (:rm 123)
:rml - удаление последней заметки
:mv @<old> @<new> - переименовать категорию
:mv #<id> @<category> - переместить заметку в категорию"""
    bot.send(Message(message.getFrom(), helpmsg))

def enc(string):
    return string.encode('utf-8')

if __name__ == '__main__':
    mainf()
