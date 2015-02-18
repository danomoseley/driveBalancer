#!/usr/bin/python

import os
import json
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
            
def f7(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if not (x in seen or seen_add(x))]
  
potential_shows = []
show_sizes = {}
con = None
try:
    con = lite.connect(config.get('XBMC','sqlite_path'))
    cur = con.cursor()
    rows = cur.execute('select strPath, watchedcount, c00 from tvshowview where watchedcount < 5;')
    for row in rows:
        path = row[0]
        name = row[2]
        if os.path.isdir(path):
            bytes = dirSize(path)
            potential_shows.append({'name':name,'path':path,'size':bytes,'size_humanized': humanize_bytes(bytes, 2)})
            show_sizes[name] = humanize_bytes(bytes, 2)
    sorted_shows = sorted(potential_shows, key=lambda k: k['size'])
    big_show_names = [x['name'] for x in sorted_shows]
    big_show_names = f7(big_show_names)
    for show in big_show_names:
        print "%s - %s" % (show_sizes[show].ljust(10), show)
except lite.Error, e:
    print "Error %s:" % e.args[0]
finally:
    if con:
        con.close()
        

