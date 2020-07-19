from configparser import ConfigParser

c = ConfigParser()
c.read('./config.ini')

BOTTOKEN = c.get('config', 'bottoken')
DATABASE = c.get('config', 'database')
ADMINCHAT = int(c.get('config', 'adminchat'))
REVERTTIME = c.getint('config', 'reverttime', fallback=30)
