import json, numpy as np
from PIL import Image
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa3'; o = {}
for n in range(1, 11):
    a = np.array(Image.open(f'{CHK}/{n}fit.png'))[:, :, 3] > 20; ys, xs = np.nonzero(a)
    cx = (xs.min()+xs.max())/2; cy = (ys.min()+ys.max())/2
    far = float(np.sqrt((xs-cx)**2+(ys-cy)**2).max())
    o[str(n)] = [float(cx-540), float(cy-540), far]
json.dump(o, open('fit.json', 'w')); print(o)
