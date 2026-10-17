"""依版本綁定從共用庫重建專案素材；不改既有不同內容的檔案。"""
import argparse,hashlib,json,shutil
from pathlib import Path
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def materialize(project,root):
 project=Path(project).resolve();root=Path(root).resolve()
 bindings=json.loads((project/'asset_bindings.json').read_text(encoding='utf-8'))
 copied=0
 for target,source in bindings.items():
  src=(root/source).resolve();dst=(project/target).resolve()
  if not src.is_relative_to(root) or not dst.is_relative_to(project):raise ValueError('路徑越界')
  if not src.is_file():raise FileNotFoundError(src)
  if dst.exists():
   if digest(src)!=digest(dst):raise FileExistsError('不同內容不可覆寫：'+str(dst))
  else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);copied+=1
 return copied
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--root',default=str(Path(__file__).resolve().parents[2]));a=p.parse_args();print('materialized',materialize(a.project,a.root))
