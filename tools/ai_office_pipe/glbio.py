import json, struct, numpy as np
def read_glb(path):
    b=open(path,'rb').read()
    assert b[:4]==b'glTF'
    off=12; js=None; binc=None
    while off<len(b):
        ln,ty=struct.unpack_from('<II',b,off); off+=8
        if ty==0x4E4F534A: js=json.loads(b[off:off+ln])
        elif ty==0x004E4942: binc=b[off:off+ln]
        off+=ln
    def acc(i):
        a=js['accessors'][i]; bv=js['bufferViews'][a['bufferView']]
        dt={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}[a['componentType']]
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        o=bv.get('byteOffset',0)+a.get('byteOffset',0)
        st=bv.get('byteStride',0)
        assert not st or st==np.dtype(dt).itemsize*n
        return np.frombuffer(binc,dt,a['count']*n,o).reshape(a['count'],n).copy()
    p=js['meshes'][0]['primitives'][0]
    return js,acc(p['attributes']['POSITION']).astype(np.float64),acc(p['indices']).reshape(-1,3).astype(np.int64)
