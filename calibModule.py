import json
import sqlite3
import datetime
from pathlib import Path

class CALIBMODULE(object):
    def __init__(self):
        self.databaseName = "calibConstants.db"
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
        print("WORKED!")
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

    ############################
    # SQLITE3 DataBase Version #
    ############################

    #Input Database As String With .db
    #Get back metadata for tables/column names
    def retrieveMetaData(self, database):
        #tab to spaces

        #Connect to Database
        conn = sqlite3.connect(database)
        c = conn.cursor()	

        #Get Board Numbers And Time Stamps
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        boardNumberList = c.fetchall()
        boards = []
        #boardTimes is a dictionary that uses board numbers for keys and timestamps for content
        boardTimes = {}

        for board in boardNumberList:
            boards.append(board[0])
            c.execute(f"SELECT * FROM {board[0]}")
            timetable = c.fetchall() 
            times = []
            for row in timetable:
                if row[0] not in times:
                    times.append(row[0])
            boardTimes[board[0]] = times

        #Get Coluta and Channel Names 
        firstBoard = boardNumberList[0][0]
        c.execute(f"SELECT * FROM {firstBoard}")
        table = c.fetchall()
        colutas = []
        channels = []
        for row in table:
            if row[1] not in colutas:
                colutas.append(row[1])
            if row[2] not in channels:
                channels.append(row[2])

        #Get weight names in database
        weightNames = []

        for info in c.description:
            weightNames.append(info[0])
        weightMapping = {}
        index = 0
        for key in weightNames:
            weightMapping[key] = index
            index += 1

        weightNames.remove(weightNames[0])
        weightNames.remove(weightNames[0])
        weightNames.remove(weightNames[0])

        # Close connection
        conn.commit()
        conn.close()

        #Return board/time dictionary, colutas, channels, and weight names
        return [boardTimes, colutas, channels, weightNames, weightMapping]


    #def getMdacCalibDB(self,boardId,coluta,channel):
    def getMdacCalibDB(self, board, coluta, channel, timestamp = 'most recent'):    
        database = self.databaseName 
        conn = sqlite3.connect(database)
        c = conn.cursor()

        weightIndices = self.retrieveMetaData(database)[4]
        weightNames = self.retrieveMetaData(database)[3]

        finaltimestamp = timestamp

        if finaltimestamp == 'most recent':
            #Get most recent time
            dateTimeList = []
            for t in self.retrieveMetaData(database)[0][board]:
                dateTimeList.append(self.convertToDateTime(t))
            mostRecent = max(dateTimeList)
            finaltimestamp = f"{mostRecent.month}-{mostRecent.day}-{mostRecent.year} {mostRecent.hour}:{mostRecent.minute}:{mostRecent.second}"
        
        try:
            c.execute(f"SELECT * FROM {board} WHERE timestamp = '{finaltimestamp}' AND coluta = {coluta} AND channel = {channel}")
            data = c.fetchall()
            mdacConstants = data[0][3:11]
            mdacNames = weightNames[0:8]
            result = {}
            for i in range(len(mdacNames)):
                mdacName = mdacNames[i]
                mdacConstant = mdacConstants[i]
                result[mdacName] = mdacConstant
            return result

        except:
          return None


    def getSarCalibDB(self, board, coluta, channel, timestamp = 'most recent'):    
        database = self.databaseName 
        conn = sqlite3.connect(database)
        c = conn.cursor()

        weightIndices = self.retrieveMetaData(database)[4]
        weightNames = self.retrieveMetaData(database)[3]
        finaltimestamp = timestamp

        if finaltimestamp == 'most recent':
            #Get most recent time
            dateTimeList = []
            for t in self.retrieveMetaData(database)[0][board]:
                dateTimeList.append(self.convertToDateTime(t))
            mostRecent = max(dateTimeList)
            finaltimestamp = f"{mostRecent.month}-{mostRecent.day}-{mostRecent.year} {mostRecent.hour}:{mostRecent.minute}:{mostRecent.second}"

        try:
            c.execute(f"SELECT * FROM {board} WHERE timestamp = '{finaltimestamp}' AND coluta = {coluta} AND channel = {channel}")
            data = c.fetchall()
            sarConstants = data[0][11:31]
            sarNames = weightNames[8:29]
            result = {}
            for i in range(len(sarNames)):
                sarName = sarNames[i]
                sarConstant = sarConstants[i]
                result[sarName] = sarConstant
            return result

        except:
            return None


    #This function is for time-related stuff
    def convertToDateTime(self, time):
      a, b = time.split(' ')
      month, day, year = a.split('-')
      hour, minute,  second = b.split(':')
      x = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
      return x


#end class CALIBMODULE
