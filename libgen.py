'''
从nbt生成gate json
'''
import sys
import python_nbt.nbt as nbt
import json
if len(sys.argv)<3:
    print('lacks args')
    sys.exit(-1)

struct=nbt.read_from_nbt_file(sys.argv[1])
js={'size':}