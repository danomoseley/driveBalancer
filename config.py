#!/usr/bin/python

import ConfigParser

config = ConfigParser.RawConfigParser()

config.add_section('General')
config.set('General','paths',['E:\TV Shows', 'G:\TV Shows', 'H:\TV Shows', 'C:\TV Shows'])
config.set('General','balance_limit',15)

config.add_section('XBMC')
config.set('XBMC','sqlite_path','C:\Users\Dan.Moseley\AppData\Roaming\XBMC\userdata\Database\MyVideos75.db')

config.add_section('SickBeard')
config.set('SickBeard','sqlite_path','C:\Program Files (x86)\SickBeard\sickbeard.db')
config.set('SickBeard','py','C:\Program Files (x86)\SickBeard\SickBeard.py')
config.set('SickBeard','host','localhost')
config.set('SickBeard','port','8081')
config.set('SickBeard','username','user')
config.set('SickBeard','password','pass')

with open('config.cfg', 'wb') as configfile:
    config.write(configfile)
