#!/usr/bin/python

import os
import doctest
import ctypes
import platform
import sys
import shutil

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

def getSize(source):
        total_size = os.path.getsize(source)
        for item in os.listdir(source):
            itempath = os.path.join(source, item)
            if os.path.isfile(itempath):
                total_size += os.path.getsize(itempath)
            elif os.path.isdir(itempath):
                total_size += getSize(itempath)
        return total_size

def getImmediateSubdirectories(dir):
    return [dir + name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]

greatest_free_space = 0
path_with_most_free_space = ''

paths = ['/Users/Dan-o/Downloads/']

for path in paths:
    free_space = get_free_space(path)
    if free_space > greatest_free_space:
        greatest_free_space = free_space
        path_with_most_free_space = path

print humanize_bytes(greatest_free_space, 2)
print path_with_most_free_space

best_match_folder = ''
max_size = 0
for disk in paths:
    if disk not in path_with_most_free_space:
        for dir in getImmediateSubdirectories(disk):
            dir_size = getSize(dir)
            if dir_size > max_size and dir_size < (greatest_free_space / 2):
                max_size = dir_size
                best_match_folder = dir

if best_match_folder != '' and path_with_most_free_space != '':
    print best_match_folder
    print humanize_bytes(max_size, 2)
    print
    shutil.move(best_match_folder, path_with_most_free_space + os.path.basename(best_match_folder))
else:
    print 'error'

    # print path to all filenames.
    # for filename in filenames:
    #    print os.path.join(dirname, filename)

    # Advanced usage:
    # editing the 'dirnames' list will stop os.walk() from recursing into there.
    # if '.git' in dirnames:
    #     # don't go into any .git directories.
    #     dirnames.remove('.git')