import json

mapping = {"lpgbt9": {"coluta13": {"0x0cc": "ch1", "0x0ce": "ch2", "0x0d0": "ch3", "0x0d2": "ch4", "0x0d4": "ch5", "0x0d6": "ch6", "0x0d8": "ch7", "0x0da": "ch8"}, 
                      "coluta14": {"0x0e0": "ch1", "0x0e2": "ch2", "0x0e4": "ch3", "0x0e6": "ch4"}},
          "lpgbt10": {"coluta14": {"0x0cc": "ch5", "0x0ce": "ch6", "0x0d0": "ch7", "0x0d2": "ch8"},
                      "coluta15": {"0x0d8": "ch1", "0x0da": "ch2", "0x0dc": "ch3", "0x0de": "ch4", "0x0e0": "ch5", "0x0e2": "ch6", "0x0e4": "ch7", "0x0e6": "ch8"}},
          "lpgbt11": {"coluta16": {"0x0ce": "ch1", "0x0d0": "ch2", "0x0d2": "ch3", "0x0d4": "ch4", "0x0d6": "ch5", "0x0d8": "ch6", "0x0da": "ch7", "0x0dc": "ch8"}},
          "lpgbt14": {"coluta17": {"0x0ce": "ch1", "0x0d0": "ch2", "0x0d2": "ch3", "0x0d4": "ch4", "0x0d6": "ch5", "0x0d8": "ch6", "0x0da": "ch7", "0x0dc": "ch8"}},
          "lpgbt15": {"coluta18": {"0x0cc": "ch1", "0x0ce": "ch2", "0x0d0": "ch3", "0x0d2": "ch4", "0x0d4": "ch5", "0x0d6": "ch6", "0x0d8": "ch7", "0x0da": "ch8"},
                      "coluta19": {"0x0e0": "ch1", "0x0e2": "ch2", "0x0e4": "ch3", "0x0e6": "ch4"}},
          "lpgbt16": {"coluta19": {"0x0cc": "ch5", "0x0ce": "ch6", "0x0d0": "ch7", "0x0d2": "ch8"},
                      "coluta20": {"0x0d8": "ch1", "0x0da": "ch2", "0x0dc": "ch3", "0x0de": "ch4", "0x0e0": "ch5", "0x0e2": "ch6", "0x0e4": "ch7", "0x0e6": "ch8"}}}

with open("config/lpGBTColutaMapping.json", "w") as f:
    json.dump(mapping, f)
