"""可重編的科技插畫元件；SVG 保留層次，PNG 供圖卡排版。"""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image,ImageDraw

C='#321A14'
def svg(body):
 return '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="700" viewBox="0 0 1000 700"><defs><linearGradient id="metal" x2="0" y2="1"><stop stop-color="#EDF5F6"/><stop offset="1" stop-color="#A7BDD0"/></linearGradient><linearGradient id="silicon"><stop stop-color="#B9DFF0"/><stop offset=".5" stop-color="#DCCEF0"/><stop offset="1" stop-color="#B9DBCC"/></linearGradient><clipPath id="waferclip"><ellipse cx="500" cy="340" rx="360" ry="220"/></clipPath></defs><g stroke="'+C+'" stroke-width="6" stroke-linejoin="round" stroke-linecap="round">'+body+'</g></svg>'
def wafer_svg():
 grid=''.join(f'<path d="M{x} 100V580" stroke="#6F91A5" stroke-width="3"/>' for x in range(140,880,55))+''.join(f'<path d="M120 {y}H880" stroke="#6F91A5" stroke-width="3"/>' for y in range(120,580,40))
 return svg('<ellipse cx="500" cy="370" rx="360" ry="220" fill="#525E6B"/><ellipse cx="500" cy="340" rx="360" ry="220" fill="url(#silicon)"/><g clip-path="url(#waferclip)">'+grid+'</g><path d="M230 260Q470 90 755 225" fill="none" stroke="#FFF9EF" stroke-width="18" opacity=".75"/><path d="M480 548Q500 530 520 548L521 562H479Z" fill="#FFF9EF"/>')
def tool_svg():
 b='<path d="M165 200L320 105H820L890 175V545L745 625H165Z" fill="#A7BDD0"/><path d="M165 200H745V625H165Z" fill="url(#metal)"/><path d="M745 200L890 175V545L745 625Z" fill="#7DADDE"/><path d="M165 200L320 105H820L745 200Z" fill="#E9F1F2"/>'
 for x in [195,345,495]:
  b+=f'<rect x="{x}" y="240" width="128" height="278" rx="15" fill="#E5ECEC"/><path d="M{x+17} 478H{x+110}" fill="none" stroke-width="3"/><rect x="{x+76}" y="355" width="17" height="67" rx="5" fill="#525E6B"/>'
  for y in [260,490]: b+=f'<circle cx="{x+17}" cy="{y}" r="4" fill="#795B49" stroke="none"/>'
 b+='<rect x="652" y="254" width="64" height="110" rx="8" fill="#525E6B"/><rect x="663" y="267" width="41" height="40" rx="3" fill="#8EDBD4"/>'
 for y in [327,345]: b+=f'<circle cx="674" cy="{y}" r="5" fill="#FFE5A5" stroke-width="2"/>'
 for x in [200,680,818]: b+=f'<path d="M{x} 570V633H{x+32}V570" fill="#525E6B"/>'
 b+='<path d="M780 250L853 220V444L780 479Z" fill="#627C92"/>'
 for y in range(280,420,24): b+=f'<path d="M792 {y}L840 {y-18}" stroke="#B9DFF0" stroke-width="4"/>'
 b+='<ellipse cx="422" cy="584" rx="130" ry="42" fill="#525E6B"/><ellipse cx="422" cy="568" rx="115" ry="33" fill="#B9DFF0"/><path d="M330 566H510M350 552H490M350 580H490" stroke="#7DADDE" stroke-width="3"/>'
 return svg(b)
def optical_svg():
 # 功能流程示意：雷射擊中錫滴形成電漿，EUV由反射鏡收集／導引至光罩與晶圓。
 b='<rect x="65" y="155" width="155" height="110" rx="20" fill="#525E6B"/><rect x="90" y="180" width="90" height="35" rx="8" fill="#B9DFF0"/><path d="M220 212H345" stroke="#F58C83" stroke-width="12"/><path d="M330 196L350 212L330 228" fill="#F58C83" stroke="#F58C83"/>'
 b+='<path d="M360 134C340 161 335 177 360 187C385 177 380 161 360 134Z" fill="#B9DFF0"/><circle cx="360" cy="213" r="32" fill="#FFE5A5" stroke="#EC886A"/>'
 for dx,dy in [(-50,0),(50,0),(0,-50),(0,50),(-35,-35),(35,35)]: b+=f'<path d="M{360+dx*.8} {213+dy*.8}L{360+dx*1.2} {213+dy*1.2}" stroke="#EC886A" stroke-width="5"/>'
 b+='<path d="M400 213L535 305L675 195L780 320L690 470" fill="none" stroke="#B899D6" stroke-width="10"/>'
 for x,y,angle in [(535,305,-35),(675,195,35),(780,320,35)]: b+=f'<g transform="translate({x},{y}) rotate({angle})"><rect x="-49" y="-9" width="98" height="18" rx="6" fill="#7DADDE"/><path d="M-39 -3H39" stroke="#FFF9EF" stroke-width="3"/></g>'
 b+='<path d="M610 450L740 420L783 452L653 488Z" fill="#525E6B"/><path d="M646 444L704 430M663 454L725 440" stroke="#FFE5A5" stroke-width="4"/><path d="M690 488L550 555" stroke="#B899D6" stroke-width="9"/><ellipse cx="500" cy="580" rx="120" ry="42" fill="#525E6B"/><ellipse cx="500" cy="566" rx="115" ry="37" fill="url(#silicon)"/>'
 for x in range(440,580,30): b+=f'<path d="M{x} 542V590" stroke="#6F91A5" stroke-width="2"/>'
 return svg(b)
def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True); records=[]
 for name,fn in [('wafer',wafer_svg),('euv_tool',tool_svg),('optical_path',optical_svg)]:
  data=fn();p=out/(name+'.svg');p.write_text(data,encoding='utf-8')
  try:
   import cairosvg
   cairosvg.svg2png(bytestring=data.encode(),write_to=str(out/(name+'.png')))
  except (ImportError,OSError):
   # svglib/reportlab 在無 Cairo 的Windows環境用既有繪圖套件渲染SVG。
   from svglib.svglib import svg2rlg
   from reportlab.graphics import renderPM
   renderPM.drawToFile(svg2rlg(str(p)),str(out/(name+'.png')),fmt='PNG',bg=0xffffff)
  records.append({'asset_id':'tech_'+name,'svg':p.name,'png':name+'.png','category':'codex_original','original_author':'Codex','tool':'Python生成分層SVG','版本':'v001','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'品管狀態':'review','限制':'教學功能示意，非真實機型剖面；光路非光學設計比例'})
 (out/'manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();build(args.out)
