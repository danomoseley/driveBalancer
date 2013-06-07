#!/usr/bin/python

import os
import doctest
import ctypes
import platform
import sys
import shutil
import sqlite3 as lite

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
            
def updateSickbeard(src, dest):
    con = None
    
    try:
        con = lite.connect('C:\Program Files (x86)\SickBeard\sickbeard.db') 
        cur = con.cursor()
        cur.execute('UPDATE tv_episodes SET location = replace(location, ?, ?) WHERE location like ?',
                    (src, dest, src + '%'))
        print "Number of tv_episodes rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE tv_shows SET location = replace(location, ?, ?) WHERE location like ?',
                    (src, dest, src + '%'))    
        print "Number of tv_shows rows updated: %d" % cur.rowcount
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
        con = lite.connect('C:\Users\Dan.Moseley\AppData\Roaming\XBMC\userdata\Database\MyVideos75.db') 
        cur = con.cursor()
        cur.execute('UPDATE path SET strPath = replace(strPath, ?, ?) WHERE strPath like ?',
                    (src, dest, src + '%'))
        print "Number of path rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE tvshow SET c16 = replace(c16, ?, ?) WHERE c16 like ?',
                    (src, dest, src + '%'))
        print "Number of tvshow rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
        cur.execute('UPDATE episode SET c18 = replace(c18, ?, ?) WHERE c18 like ?',
                    (src, dest, src + '%'))
        print "Number of episode rows updated: %d" % cur.rowcount
        #con.rollback()
        con.commit()
    except lite.Error, e:
        print "Error %s:" % e.args[0]
        sys.exit(1)
    finally:
        if con:
            con.close()

def balance(paths):
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

    print 'Greatest free space: ' + path_with_greatest_free_space + ' (' + humanize_bytes(greatest_free_space, 2) + ')'

    print 'Least free space: ' + path_with_least_free_space + ' (' +  humanize_bytes(least_free_space, 2) + ')'

    best_match_folder = ''
    #max_size = 0
    max_size = float('inf')
    for dir in getImmediateSubdirectories(path_with_least_free_space):
        dir_size = dirSize(dir)
        if dir_size < max_size and dir_size < (greatest_free_space / 2):
            max_size = dir_size
            best_match_folder = dir

    if best_match_folder != '' and path_with_greatest_free_space != '':
        src = best_match_folder
        dest = path_with_greatest_free_space + '\\' + os.path.basename(best_match_folder)
        print 'Moving: ' + src + ' -> ' + dest + ' (' + humanize_bytes(max_size, 2) + ')'
        shutil.move(src, dest)
        updateSickbeard(src, dest)
        updateXBMC(src, dest)
        #raw_input("Press enter to balance again")
        balance(paths)
    else:
        print 'error'


balance(['E:\TV Shows', 'G:\TV Shows', 'H:\TV Shows'])