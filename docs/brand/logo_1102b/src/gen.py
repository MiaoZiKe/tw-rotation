import sys, json, base64, requests, concurrent.futures as cf
BASE="https://api.openai.com/v1/images/generations"
COMMON=("Flat vector brand symbol on pure white background, centered, generous margin. NO text, NO letters, NO numbers, NO words, no mascot, no animal, no seal or stamp, "
        "no recycling arrows, no gradients, no shadows, no 3D, no texture. Bold clean geometric shapes with precise curves and equal stroke weights, minimal fintech logo like Robinhood, Revolut, Wise, Stripe. ")
D={
 "A":("Concept 'capital flow': a single abstract mark made of two or three smooth ribbon shapes that sweep diagonally upward-right, like money flowing from one sector into another, built from quarter-circle arcs, rounded ends. Two colors only: deep navy blue and one vivid red-orange accent.",),
 "B":("Concept 'L monogram': a bold geometric capital letter L-like glyph shape (a thick vertical bar with a foot) where the foot sweeps up into a rising diagonal tip, as if the letter L is becoming an upward arrow. Rounded corners, heavy uniform weight. Two colors only: deep navy and one red accent.",),
 "C":("Concept 'candlestick rising': three or four rounded vertical bars of ascending height inside an implied square, abstract K-line candlesticks with a tiny wick, one bar in red accent, others navy. Extremely simple and balanced, grid-based construction.",),
 "D":("Concept 'two interlocking L shapes with rotational symmetry': two identical thick L-shaped blocks rotated 180 degrees against each other forming a compact pinwheel-like square mark, representing rotation of capital between sectors. One navy, one red-orange. Pure geometry, sharp precise edges with small rounded corners.",),
}
def go(k,i):
    r=requests.post(BASE,headers={"Authorization":"Bearer sk-dummy"},json={"model":"gpt-image-1.5","prompt":D[k][0]+" "+COMMON,"size":"1024x1024","n":1,"quality":"high"},timeout=300)
    j=r.json()
    if "data" not in j: return k,i,str(j)[:200]
    open(f"ai_sketches/{k}{i}.png","wb").write(base64.b64decode(j["data"][0]["b64_json"]))
    return k,i,"ok"
ks=sys.argv[1] if len(sys.argv)>1 else "ABCD"
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(lambda a:go(*a),[(k,i) for k in ks for i in range(1,5)]): print(r)
