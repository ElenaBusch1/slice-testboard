import json
from pathlib import Path

class CALIBMODULE(object):
    def __init__(self):
        self.calibFileName = "calibFile.json"
        self.reqSarWeightName = "W_1ST_3584"
        self.reqMdacWeightName = 'MDACCorrectionCode0'
        self.data = None

    def test(self):
        #test process
        #result = self.checkCalibFile()
        #print(result)
        #self.ensureCalibFile()
        #testSarVals = {'W_2ND_16': 16.25, 'W_2ND_24': 24.43, 'W_2ND_32': 32.9, 'W_2ND_64': 64.66, 'W_2ND_128': 129.53, 'W_2ND_224': 225.95, 'W_1ST_128': 131.67, 'W_1ST_256': 264.32, 'W_1ST_384': 395.75, 'W_1ST_640': 659.64, 'W_1ST_1024': 1054.46, 'W_1ST_2048': 2106.05, 'W_1ST_3584': 3685.93, 'W_2ND_10': 10, 'W_2ND_6': 6, 'W_2ND_4': 4, 'W_2ND_2': 2, 'W_2ND_1': 1, 'W_2ND_0p5': 0.5, 'W_2ND_0p25': 0.25}
        #self.addSarCalib(boardId="34",coluta="coluta20",channel="channel8",sarVals=testSarVals)
        #testMdacVals = {'MDACCorrectionCode0': 77.24, 'MDACCorrectionCode1': 4169.35, 'MDACCorrectionCode2': 4169.15, 'MDACCorrectionCode3': 4171.31, 'MDACCorrectionCode4': 4169.52, 'MDACCorrectionCode5': 4169.78, 'MDACCorrectionCode6': 4170.65, 'MDACCorrectionCode7': 4171.54}
        #self.addMdacCalib(boardId="34",coluta="coluta20",channel="channel8",mdacVals=testMdacVals)
        #result = self.getSarCalib(boardId="34",coluta="coluta20",channel="channel8")
        #print(result)
        #result = self.getMdacCalib(boardId="34",coluta="coluta20",channel="channel8")
        #print(result)
        return None
        
    def checkCalibFile(self):
        calibFilePath = Path(self.calibFileName)
        if calibFilePath.is_file():
          return True
        return False
    
    def ensureCalibFile(self):
        if self.checkCalibFile() :
          return None
        temp = {"sliceBoardCalibs":{} }
        with open(self.calibFileName, 'w') as fp:
          json.dump(temp, fp, sort_keys=True, indent=4)
        return None
    
    def getSarCalib(self,boardId,coluta,channel):
        self.ensureCalibFile()
        data = {}
        with open(self.calibFileName, 'r') as fp:
          temp = json.load(fp)  
          data = temp
        if "sliceBoardCalibs" not in data :
          return None
        if boardId not in data["sliceBoardCalibs"] :
          return None
        if coluta not in data["sliceBoardCalibs"][boardId] :
          return None
        if channel not in data["sliceBoardCalibs"][boardId][coluta] :
          return None
        if "sarVals" not in data["sliceBoardCalibs"][boardId][coluta][channel] :
          return None
        if self.reqSarWeightName not in data["sliceBoardCalibs"][boardId][coluta][channel]["sarVals"] :
          return None
        return data["sliceBoardCalibs"][boardId][coluta][channel]["sarVals"]
          
    def addSarCalib(self,boardId,coluta,channel,sarVals):
        #check if SAR Vals has required info
        if isinstance(sarVals, dict) == False :
          return None
        if self.reqSarWeightName not in sarVals:
          return None
        self.ensureCalibFile()
        data = {}
        with open(self.calibFileName, 'r') as fp:
          temp = json.load(fp)  
          data = temp
        if "sliceBoardCalibs" not in data :
          return None
        if boardId not in data["sliceBoardCalibs"]:
          data["sliceBoardCalibs"][boardId] = {}
        if coluta not in data["sliceBoardCalibs"][boardId] :
          data["sliceBoardCalibs"][boardId][coluta] = {}
        if channel not in data["sliceBoardCalibs"][boardId][coluta] :
          data["sliceBoardCalibs"][boardId][coluta][channel] = {}
        data["sliceBoardCalibs"][boardId][coluta][channel]["sarVals"] = sarVals
        with open(self.calibFileName, 'w') as fp:
          json.dump(data, fp, sort_keys=True, indent=4)

    def getMdacCalib(self,boardId,coluta,channel):
        self.ensureCalibFile()
        data = {}
        with open(self.calibFileName, 'r') as fp:
          temp = json.load(fp)  
          data = temp
        if "sliceBoardCalibs" not in data :
          return None
        if boardId not in data["sliceBoardCalibs"] :
          return None
        if coluta not in data["sliceBoardCalibs"][boardId] :
          return None
        if channel not in data["sliceBoardCalibs"][boardId][coluta] :
          return None
        if "mdacVals" not in data["sliceBoardCalibs"][boardId][coluta][channel] :
          return None
        if self.reqMdacWeightName not in data["sliceBoardCalibs"][boardId][coluta][channel]["mdacVals"] :
          return None
        return data["sliceBoardCalibs"][boardId][coluta][channel]["mdacVals"]
          
    def addMdacCalib(self,boardId,coluta,channel,mdacVals):
        #check if MDAC Vals has required info
        if isinstance(mdacVals, dict) == False :
          return None
        if self.reqMdacWeightName not in mdacVals:
          return None
        self.ensureCalibFile()
        data = {}
        with open(self.calibFileName, 'r') as fp:
          temp = json.load(fp)
          data = temp
        if "sliceBoardCalibs" not in data :
          return None
        if boardId not in data["sliceBoardCalibs"]:
          data["sliceBoardCalibs"][boardId] = {}
        if coluta not in data["sliceBoardCalibs"][boardId] :
          data["sliceBoardCalibs"][boardId][coluta] = {}
        if channel not in data["sliceBoardCalibs"][boardId][coluta] :
          data["sliceBoardCalibs"][boardId][coluta][channel] = {}
        data["sliceBoardCalibs"][boardId][coluta][channel]["mdacVals"] = mdacVals
        with open(self.calibFileName, 'w') as fp:
          json.dump(data, fp, sort_keys=True, indent=4)
#end class CALIBMODULE
