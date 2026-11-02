import sys, importlib
from kit import *
from PIL import Image
n=sys.argv[1]
m=importlib.import_module('m'+n)
items=make('G'+n,m)
shot_svgs(items,'/tmp/claude-0/w')
ic=Image.open(f'/tmp/claude-0/w/G{n}_icon512.png').convert('RGBA'); i110=Image.open(f'/tmp/claude-0/w/G{n}_ig110.png').convert('RGBA'); i40=Image.open(f'/tmp/claude-0/w/G{n}_ig40.png').convert('RGBA'); hz=Image.open(f'/tmp/claude-0/w/G{n}_horizontal.png').convert('RGBA')
sheet=Image.new('RGB',(1200,512+420),'white')
sheet.paste(ic,(0,0),ic); sheet.paste(i110,(540,20),i110); sheet.paste(i40,(680,20),i40)
sheet.paste(Image.open(f'/tmp/claude-0/w/G{n}_ig400.png').convert('RGBA'),(540,150),Image.open(f'/tmp/claude-0/w/G{n}_ig400.png').convert('RGBA'))
sheet.paste(hz,(0,520),hz)
sheet.save(f'/tmp/claude-0/w/sheet{n}.png')
