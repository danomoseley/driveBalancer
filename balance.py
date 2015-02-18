#!/usr/bin/python

import os
import doctest
import ctypes
import platform
import sys
import shutil
import sqlite3 as lite
import urllib2
import os
import time
import re
import subprocess
import ConfigParser

config = ConfigParser.RawConfigParser()
config.read('config.cfg')

class DirSizeError(Exception): pass

def get_free_space(folder):
    """ Return folder/drive free space (in bytes)
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize

def humanize_bytes(bytes, precision=1):
    """
    Return a humanized string representation of a number of bytes.
    """
    abbrevs = (
        (1<<50L, 'PB'),
        (1<<40L, 'TB'),
        (1<<30L, 'GB'),
        (1<<20L, 'MB'),
        (1<<10L, 'kB'),
        (1, 'bytes')
    )
    if bytes == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if bytes >= factor:
            break
    return '%.*f %s' % (precision, bytes / factor, suffix)

def dirSize(start, follow_links=0, start_depth=0, max_depth=0, skip_errs=0):

    # Get a list of all names of files and subdirectories in directory start
    try: dir_list = os.listdir(start)
    except:
        # If start is a directory, we probably have permission problems
        if os.path.isdir(start):
            raise DirSizeError('Cannot list directory %s'%start)
        else:  # otherwise, just re-raise the error so that it propagates
            raise

    total = 0L
    for item in dir_list:
        # Get statistics on each item--file and subdirectory--of start
        path = start + '\\' + item
        try: stats = os.stat(path)
        except: 
            if not skip_errs:
                raise DirSizeError('Cannot stat %s'%path)
        # The size in bytes is in the seventh item of the stats tuple, so:
        total += stats[6]
        # recursive descent if warranted
        if os.path.isdir(path) and (follow_links or not os.path.islink(path)):
            bytes = dirSize(path, follow_links, start_depth+1, max_depth)
            total += bytes
            if max_depth and (start_depth < max_depth):
                print_path(path, bytes)
    return total

def getImmediateSubdirectories(dir):
    return [dir + '\\' + name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]

def openURL(url, username, password):
    req = urllib2.Request(url)

    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, username, password)

    auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)
    opener = urllib2.build_opener(auth_manager)

    urllib2.install_opener(opener)

    return urllib2.urlopen(req)
            
def stopSickbeard():
    try:
        handler = openURL('http://'+config.get('SickBeard','host')+':'+config.get('SickBeard','port'),config.get('SickBeard','username'),config.get('SickBeard','password'))
        print handler.getcode()
        if handler.getcode() == 200:
            page = handler.read()
            
            pid_search = re.search('<a href="/home/shutdown/\?pid=(\d+)" ', page, re.IGNORECASE)
            
            if pid_search:
                pid = pid_search.group(1)
                
                print "http://%s:%s/home/shutdown?pid=%s" % (config.get('SickBeard','host'), config.get('SickBeard','port'), pid)
                handler = openURL('http://'+config.get('SickBeard','host')+':'+config.get('SickBeard','port')+'/home/shutdown?pid='+pid,config.get('SickBeard','username'),config.get('SickBeard','password'))

                while openURL('http://'+config.get('SickBeard','host')+':'+config.get('SickBeard','port'),config.get('SickBeard','username'),config.get('SickBeard','password')).getcode() == 200:        
                    print "Sleeping for 10 seconds"
                    time.sleep(10)
    except Exception as e:
        print 'Sickbeard is not running'

def startSickbeard():
    print "Starting sickbeard"
    p = subprocess.Popen([sys.executable, config.get('SickBeard','py')], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT);

def updateSickbeard(src, dest):
    con = None
    
    try:
        con = lite.connect(config.get('SickBeard','sqlite_path')) 
        cur = con.cursor()
        cur.execute('UPDATE tv_episodes SET location = replace(location, ?, ?) WHERE location like ?',
                    (src, dest, src + '%'))
        print "Number of SickBeard tv_episodes rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE tv_shows SET location = replace(location, ?, ?) WHERE location like ?',
                    (src, dest, src + '%'))    
        print "Number of SickBeard tv_shows rows updated: %d" % cur.rowcount
        
        #con.rollback()
        con.commit()
    except lite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()
            
def updatePlex(src, dest):
    con = None
    
    try:
        con = lite.connect(config.get('Plex','sqlite_path'))
        cur = con.cursor()
        cur.execute('UPDATE media_parts SET file = replace(file, ?, ?) WHERE file like ?',
                    (src, dest, src + '%'))
        print "Number of Plex media_parts rows updated: %d" % cur.rowcount
        con.commit()
        cur.execute('UPDATE media_streams SET url = replace(url, ?, ?) WHERE url like ?',
                    (src, dest, src + '%'))
        print "Number of Plex media_streams rows updated: %d" % cur.rowcount
        con.commit()
    except lite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()

def updateNzbDrone(src, dest):
    con = None
    
    try:
        con = lite.connect(config.get('NzbDrone','sqlite_path'))
        cur = con.cursor()
        cur.execute('UPDATE Series SET Path = ? WHERE Path = ?', (dest, src))
        print "Number of NzbDrone Series rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
    except lite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()

def updateXBMC(src, dest):
    con = None
    
    try:
        con = lite.connect(config.get('XBMC','sqlite_path'))
        cur = con.cursor()
        cur.execute('UPDATE path SET strPath = replace(strPath, ?, ?) WHERE strPath like ?',
                    (src, dest, src + '%'))
        print "Number of XBMC path rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE tvshow SET c16 = replace(c16, ?, ?) WHERE c16 like ?',
                    (src, dest, src + '%'))
        print "Number of XBMC tvshow rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE episode SET c18 = replace(c18, ?, ?) WHERE c18 like ?',
                    (src, dest, src + '%'))
        print "Number of XBMC episode rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
    except lite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()
            
def balance(paths, count, already_processed=[]):
    greatest_free_space = 0
    path_with_greatest_free_space = ''
    least_free_space = float('inf')
    path_with_least_free_space = ''

    for path in paths:
        free_space = get_free_space(path)
        if free_space > greatest_free_space:
            greatest_free_space = free_space
            path_with_greatest_free_space = path

        if free_space < least_free_space:
            least_free_space = free_space
            path_with_least_free_space = path

    free_space_difference_ratio = (least_free_space/1.0) / (greatest_free_space/1.0)
    if free_space_difference_ratio > 0.8 or count <= 0:
        return

    print "Greatest free space: %s (%s)" % (path_with_greatest_free_space, humanize_bytes(greatest_free_space, 2))

    print "Least free space: %s (%s)" % (path_with_least_free_space, humanize_bytes(least_free_space, 2))

    best_match_folder = ''
    max_size = float('inf')
    for dir in getImmediateSubdirectories(path_with_least_free_space):
        dir_size = dirSize(dir)
        if dir not in already_processed:
            if dir_size < max_size and dir_size < (greatest_free_space / 2):
                if dir_size > 1073741824:
                    max_size = dir_size
                    best_match_folder = dir

    if best_match_folder != '' and path_with_greatest_free_space != '':
        src = best_match_folder
        dest = path_with_greatest_free_space + '\\' + os.path.basename(best_match_folder)
        print "Moving: %s -> %s (%s)" % (src, dest, humanize_bytes(max_size, 2))
        shutil.move(src, dest)
        updateNzbDrone(src, dest)
        #updateSickbeard(src, dest)
        updateXBMC(src, dest)
        updatePlex(src, dest)
        count -= 1
        already_processed.append(dest)
        if len(sys.argv) == 0:
            choice = raw_input("Press enter to balance again or type no to stop: ").lower()
        if len(sys.argv) > 0 or choice not in ['n','no']:
            balance(paths, count, already_processed)
    else:
        return

#stopSickbeard()
balance(['E:\TV Shows', 'G:\TV Shows', 'H:\TV Shows', 'C:\TV Shows', 'F:\TV Shows', 'I:\TV Shows'], config.getint('General','balance_limit'))
#startSickbeard()
