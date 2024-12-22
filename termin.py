from nbtrd import *
import json
import sys
if len(sys.argv)<2:
    print('err: no input nbt.')
    sys.exit(-1)
raw=json.load(open(sys.argv[1],'r'))

temp=structure(100,100,100)
temp.add_to_palette(blocks.BLOCK_STONE,temp.create_blockstate('minecraft:stone'))
temp.add_to_palette(blocks.BLOCK_REDSTONE,temp.create_blockstate('minecraft:redstone_wire'))
temp.add_to_palette(blocks.BLOCK_REPETITOR,temp.create_blockstate('minecraft:repetitor'))
temp.add_to_palette(blocks.BLOCK_REDSTONE_TORCH,temp.create_blockstate('minecraft:redstone_torch'))
temp.add_to_palette(blocks.BLOCK_LEVER,temp.create_blockstate('minecraft:lever'))
temp.fill(0,0,0,3,3,48,blocks.BLOCK_REPETITOR)
# print(temp.get_nbt())
nbt.write_to_nbt_file('output.nbt',temp.get_nbt())