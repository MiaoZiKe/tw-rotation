import os
TAIL = ", bright sunny daytime, bright airy colors, no text, no letters, no logo, no signage, no real landmark buildings, no close-up human faces, photorealistic, clean composition, subject in the upper area"
P = {
 "fab": "wide interior of a bright modern semiconductor wafer fabrication cleanroom, silver automated wafer transport rails, glowing white light, engineers far away in white suits" + TAIL,
 "memory": "macro photograph of a stack of silicon memory chips and a large wafer on a bright white lab bench, soft blue reflections, shallow depth of field" + TAIL,
 "fed": "generic fictional neoclassical government building with white stone columns under blue sky, symmetrical, wide angle, no flags" + TAIL,
 "datacenter": "bright modern data center aisle with rows of white server racks and soft blue indicator lights, perspective view" + TAIL,
 "trading": "bright daytime trading floor desk beside big windows, several monitors showing only abstract line charts, plants, natural sunlight" + TAIL,
 "city": "generic fictional modern financial district with glass office towers seen from a distance, blue sky and soft clouds, aerial view" + TAIL,
 "packaging": "bright electronics assembly line, robotic arm placing a small chip on a green circuit board, clean white factory, shallow depth of field" + TAIL,
}
want = [k for k in os.environ.get("KEYS", "").replace(" ", "").split(",") if k]
if want: P = {k: v for k, v in P.items() if k in want}
