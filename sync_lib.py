
"""

updates specific library in libs
example: python sync_lib.py libs/twisted ~/Downloads/Twisted-12.3.0/twisted

walks through directory in first argument, looks for files ending with 'py' and overwrites it with corresponding file from directory from second argument

"""




import os
import os.path
import sys
import shutil


if len(sys.argv) != 3:
    print "Need two arguments"
    exit()

for i in [1, 2]:
    if not os.path.exists(sys.argv[i]):
        print sys.argv[i], 'does not exist'
        exit()
    if not os.path.isdir(sys.argv[i]):
        print sys.argv[i], 'is not directory'
        exit()

for root, dirs, files in os.walk(sys.argv[1]):
    for name in files:
        if name.endswith('py'):
            dest = os.path.join(root, name)
            src = sys.argv[2] + dest.replace(sys.argv[1], "")
            print src, '-->', dest
            shutil.copy(src, dest)