import json

d = {ch: {} for ch in range(48,80)}

prefix = {48: 0xa5, 52: 0xa6, 56: 0xa7, 60: 0xa8, 64: 0xa1, 68: 0xa2, 72: 0xa3, 76: 0xa4}

for ch in d.keys():
  i = ch-ch%4
  n = prefix[i] << 8
  if ch%4 == 0:
    d[ch][0] = n+0x09
    d[ch][1] = n+0x29
  elif ch%4 == 1:
    d[ch][0] = n+0x69
    d[ch][1] = n+0x49
  elif ch%4 == 2:
    d[ch][0] = n+0x89
    d[ch][1] = n+0xa9
  elif ch%4 == 3:
    d[ch][0] = n+0xe9
    d[ch][1] = n+0xc9

with open("FEB2-CH_serializer.json","w") as f:
    json.dump(d,f)
