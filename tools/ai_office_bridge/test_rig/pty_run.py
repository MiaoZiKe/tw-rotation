"""在假終端機裡開互動式 Claude Code，自動通過首次啟動畫面，送一句話，之後只觀察。用法：pty_run.py <輸出檔> <總秒數>"""
import pty, os, sys, time, select, re
out=open(sys.argv[1],"wb"); total=float(sys.argv[2])
pid, fd = pty.fork()
if pid == 0:
    os.environ.update(TERM="xterm-256color", COLUMNS="120", LINES="40")
    os.execvp("claude", ["claude","--setting-sources","project,local","--model","haiku","--permission-mode","dontAsk"])
buf=""; done=set(); t0=time.time(); sent_at=None; ready_at=None
def strip(s): return re.sub(r"\s+","",re.sub(r"\x1b\[[0-9;?<>=]*[a-zA-Z]|\x1b\][^\x07]*\x07","",s))
while time.time()-t0 < total:
    r,_,_=select.select([fd],[],[],0.3)
    if r:
        try: d=os.read(fd,65536)
        except OSError: break
        out.write(d); out.flush(); buf=(buf+d.decode("utf-8","replace"))[-6000:]
    s=strip(buf)
    for key,pat,resp in (("theme","Choosethetextstyle","\r"),("sec","PressEntertocontinue","\r"),("trust","Itrustthisfolder","\x1b[B\r")):
        if key not in done and pat in s:
            time.sleep(1); os.write(fd,resp.encode()); done.add(key); buf=""; print("auto:",key, round(time.time()-t0,1)); ready_at=time.time()
    if "trust" in done and sent_at is None and time.time()-ready_at>7:
        os.write(fd,"只回答兩個字：收到".encode()); time.sleep(1); os.write(fd,b"\r"); sent_at=time.time(); print("prompt sent", round(sent_at-t0,1), int(sent_at))
try: os.kill(pid, 15)
except Exception: pass
