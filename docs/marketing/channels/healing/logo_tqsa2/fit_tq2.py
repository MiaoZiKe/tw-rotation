import json, numpy as np
from PIL import Image
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa2'; o = {}
for n in list(range(1, 12)) + ['sA', 'sB']:
    a = np.array(Image.open(f'{CHK}/{n}fit.png'))[:, :, 3] > 20; ys, xs = np.nonzero(a)
    o[str(n)] = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max())*1.02
json.dump(o, open('fit.json', 'w')); print(o)
