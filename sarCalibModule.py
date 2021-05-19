import numpy as np
import configparser
import time
import subprocess
import parseDataMod
import math

class SARCALIBMODULE(object):
    def __init__(self,GUI):
        self.GUI = GUI #just pass GUI object into SAR calib module to access configuration and data-taking methods....
        self.outputPath = "test.dat"
        self.outputPathStamped = "test-1.dat"
        self.dataMap = {}
        self.mapFeb2ChToColutaCh = {}
        self.mapColutaChToFeb2Ch = {}
        self.defineMaps()
        self.testSingleWeight = False #debugging mode

    def test(self):
        #generic module test function
        pass

    def defineMaps(self):
        #define feb2ch to COLUTA ch
        numFeb2ChPerAsic = 4
        for feb2Ch in range(0,128,1):
          colutaNum = math.floor(int(feb2Ch) / numFeb2ChPerAsic)
          colutaLabel = "coluta" + str(colutaNum+1)
          self.mapFeb2ChToColutaCh[feb2Ch] = {}
          #asic hi/lo pair
          hiLoPair = feb2Ch % numFeb2ChPerAsic
          if hiLoPair == 0 :
            self.mapFeb2ChToColutaCh[feb2Ch]["lo"] = (colutaNum,0,colutaLabel,"channel1")
            self.mapFeb2ChToColutaCh[feb2Ch]["hi"] = (colutaNum,1,colutaLabel,"channel2")
          if hiLoPair == 1 :
            self.mapFeb2ChToColutaCh[feb2Ch]["lo"] = (colutaNum,3,colutaLabel,"channel4")
            self.mapFeb2ChToColutaCh[feb2Ch]["hi"] = (colutaNum,2,colutaLabel,"channel3")
          if hiLoPair == 2 :
            self.mapFeb2ChToColutaCh[feb2Ch]["lo"] = (colutaNum,4,colutaLabel,"channel5")
            self.mapFeb2ChToColutaCh[feb2Ch]["hi"] = (colutaNum,5,colutaLabel,"channel6")
          if hiLoPair == 3 :
            self.mapFeb2ChToColutaCh[feb2Ch]["lo"] = (colutaNum,7,colutaLabel,"channel8")
            self.mapFeb2ChToColutaCh[feb2Ch]["hi"] = (colutaNum,6,colutaLabel,"channel7")

        #define COLUTA ch labels to feb2ch
        numColutaPerFeb2 = 32
        numChPerColuta = 8
        for colutaNum in range(0,numColutaPerFeb2,1):
          for chNum in range(0,numChPerColuta,1) :
            febChNum = math.floor((numChPerColuta*colutaNum+chNum)/2)
            hilo = "lo"
            if chNum == 1 or chNum == 2 or chNum == 5 or chNum == 6 :
              hilo = "hi"
            colutaLabel = "coluta" + str(colutaNum+1)
            channelLabel = "channel" + str(chNum+1)
            if colutaLabel not in self.mapColutaChToFeb2Ch :
              self.mapColutaChToFeb2Ch[colutaLabel] = {}
            self.mapColutaChToFeb2Ch[colutaLabel][channelLabel] = (febChNum,hilo)

        #test maps here
        #for feb2Ch in range(0,128,1):
        #  print(feb2Ch)
        #  print("LO",self.mapFeb2ChToColutaCh[feb2Ch]["lo"])
        #  print("HI",self.mapFeb2ChToColutaCh[feb2Ch]["hi"])

        #for colutaNum in range(0,numColutaPerFeb2,1):
        #  for chNum in range(0,numChPerColuta,1) :
        #    colutaLabel = "coluta" + str(colutaNum+1)
        #    channelLabel = "channel" + str(chNum+1)
        #    print(colutaNum,chNum,colutaLabel,channelLabel,self.mapColutaChToFeb2Ch[colutaLabel][channelLabel])    
        return

    def doSarCalib(self,coluta,channel):
        chLabelDict = { 'channel1': ('ch1','ch2','channel2'), 'channel2': ('ch2','ch1','channel1'), 'channel3': ('ch3','ch4','channel4'), 'channel4': ('ch4','ch3','channel3')
                       , 'channel5': ('ch5','ch6','channel6'), 'channel6': ('ch6','ch5','channel5'), 'channel7': ('ch7','ch8','channel8'), 'channel8': ('ch8','ch7','channel7') }
        if coluta not in self.GUI.chips :
          print("INVALID ASIC")
          return None
        if channel not in chLabelDict :
          print("INVALID CH")
          return None
        MSBchannel = channel
        LSBchannel = chLabelDict[channel][2]
        MSBSectionName = chLabelDict[channel][0]
        LSBSectionName = chLabelDict[channel][1]

        # Common Setting for Weighting Evaluation
        self.GUI.chips[coluta].setConfiguration(MSBSectionName,'SHORTINPUT', '1')
        self.GUI.chips[coluta].setConfiguration(MSBSectionName,'DREMDACToSAR', '0')
        self.GUI.chips[coluta].setConfiguration(MSBSectionName,'OutputMode', '1')
        self.GUI.chips[coluta].setConfiguration(MSBSectionName,'EXTToSAR', '0')
        self.GUI.chips[coluta].setConfiguration(LSBSectionName,'DATAMUXSelect', '1')
        self.GUI.sendUpdatedConfigurations()

        nRepeats = 1
        self.GUI.nSamples = 100000
        self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples))

        #list of weights to measure
        weightsList = ["W_2ND_16","W_2ND_24","W_2ND_32","W_2ND_64","W_2ND_128","W_2ND_224",
                       "W_1ST_Unit","W_1ST_128","W_1ST_256","W_1ST_384","W_1ST_640","W_1ST_1024","W_1ST_2048","W_1ST_3584"] #Note: order matters!!!! must be done from lowest to highest weights
        if self.testSingleWeight == True :
          weightsList = ["W_2ND_16"] #test only
        weightResultDict = {}
        for weightName in weightsList :
          bitArrayDict = self.getWeightBits(weightName,coluta,MSBchannel,LSBchannel)
          weightResultDict[weightName] = bitArrayDict

        self.calcWeights(weightsList,weightResultDict)
        #print out weights
        for weightName in weightsList :
          if weightName not in weightResultDict :
            print("MISSING WEIGHT ", weightName)
            return None
          if "W_P" not in weightResultDict[weightName] or "W_N" not in weightResultDict[weightName] :
            print("MISSING WEIGHT ", weightName)
            return None
          if weightName == "W_1ST_Unit" : continue
          print(weightName,"P",weightResultDict[weightName]["W_P"])
          print(weightName,"N",weightResultDict[weightName]["W_N"])

        print("DONE TEST")
        return None

    def takeTriggerData(self):
        """Runs takeTriggerData script"""
        subprocess.call("python takeTriggerData.py -o "+self.outputPath+" -t trigger -a 20", shell=True)
        time.sleep(5)

    def removeTriggerData(self):
        """Runs takeTriggerData script"""
        subprocess.call("rm "+self.outputPathStamped, shell=True)
        time.sleep(5)

    def takeData(self):
        self.takeTriggerData()
        maxReads = 100000 #need to optimize
        attributes = {} #this is a really bad way to pass required attributes field to parseDataMod
        attributes['adc'] = self.GUI.singleADCMode_ADC
        chanData = parseDataMod.parseData("test-1.dat",'trigger', maxReads,attributes)
        self.removeTriggerData()
        self.dataMap = {}
        for chanNum,data in enumerate(chanData) :
          loData = data[0]
          hiData = data[1]
          if len(loData) == 0 or len(hiData) == 0 : continue
          #check for fake data in parsed data, corresponds to channel without data recorded
          if isinstance(loData[0], list) : continue

          loDataBin = [ parseDataMod.convert_to_bin(x) for x in loData ]
          hiDataBin = [ parseDataMod.convert_to_bin(x) for x in hiData ]
          
          colutaLabel = self.mapFeb2ChToColutaCh[chanNum]["lo"][2]
          lo_colutaCh = self.mapFeb2ChToColutaCh[chanNum]["lo"][3]
          hi_colutaCh = self.mapFeb2ChToColutaCh[chanNum]["hi"][3]
 
          if colutaLabel not in self.dataMap :
            self.dataMap[colutaLabel] = {}
          self.dataMap[colutaLabel][lo_colutaCh] = loDataBin
          self.dataMap[colutaLabel][hi_colutaCh] = hiDataBin
          continue
          print( chanNum )
          print( "\t",colutaLabel)
          print( "\t", lo_colutaCh )
          print( "\t", hi_colutaCh )
          print( "\t", loData)
          print( "\t", hiData)
        return

    def calcWeights(self, weightsList, weightResultDict):
        list_Weighting_Second_Stage_P = [0,0,0,0,0,0,0,0,0,0,0,0,0,10,6,4,2,1,0.5,0.25]
        list_Weighting_Second_Stage_N = [0,0,0,0,0,0,0,0,0,0,0,0,0,10,6,4,2,1,0.5,0.25]
        weightPositionDict = {"W_2ND_16":12,"W_2ND_24":11,"W_2ND_32":10,"W_2ND_64":9,"W_2ND_128":8,"W_2ND_224":7} #Note: this is a bad solution. also note only 2nd stage weights here
        for weightName in weightsList :
          self.calcWeight(weightName, weightResultDict, list_Weighting_Second_Stage_P,list_Weighting_Second_Stage_N )
          if "W_P" not in weightResultDict[weightName] or "W_N" not in weightResultDict[weightName] :
            return None
          W_P = weightResultDict[weightName]["W_P"]
          W_N = weightResultDict[weightName]["W_N"]
          #update weighting list
          if weightName not in weightPositionDict :
            #return None
            continue
          listPos = weightPositionDict[weightName]
          list_Weighting_Second_Stage_P[listPos] = round(W_P,2)
          list_Weighting_Second_Stage_N[listPos] = round(W_N,2)
        
        #need to update 1st stage weights, copied from original implementation in CV3 code
        if self.testSingleWeight == True :
          return None

        weightResultDict["W_1ST_128"]["W_P"] = weightResultDict["W_1ST_128"]["W_P"] + weightResultDict["W_1ST_Unit"]["W_P"]
        weightResultDict["W_1ST_128"]["W_N"] = weightResultDict["W_1ST_128"]["W_N"] + weightResultDict["W_1ST_Unit"]["W_N"]

        weightResultDict["W_1ST_256"]["W_P"] = weightResultDict["W_1ST_256"]["W_P"] + weightResultDict["W_1ST_128"]["W_P"] + weightResultDict["W_1ST_Unit"]["W_P"]
        weightResultDict["W_1ST_256"]["W_N"] = weightResultDict["W_1ST_256"]["W_N"] + weightResultDict["W_1ST_128"]["W_N"] + weightResultDict["W_1ST_Unit"]["W_N"]

        weightResultDict["W_1ST_384"]["W_P"] = weightResultDict["W_1ST_384"]["W_P"] + weightResultDict["W_1ST_256"]["W_P"] + weightResultDict["W_1ST_128"]["W_P"]
        weightResultDict["W_1ST_384"]["W_N"] = weightResultDict["W_1ST_384"]["W_N"] + weightResultDict["W_1ST_256"]["W_N"] + weightResultDict["W_1ST_128"]["W_N"]

        weightResultDict["W_1ST_640"]["W_P"] = weightResultDict["W_1ST_640"]["W_P"] + weightResultDict["W_1ST_384"]["W_P"] + weightResultDict["W_1ST_256"]["W_P"]
        weightResultDict["W_1ST_640"]["W_N"] = weightResultDict["W_1ST_640"]["W_N"] + weightResultDict["W_1ST_384"]["W_N"] + weightResultDict["W_1ST_256"]["W_N"]

        weightResultDict["W_1ST_1024"]["W_P"] = weightResultDict["W_1ST_384"]["W_P"] + weightResultDict["W_1ST_640"]["W_P"] + weightResultDict["W_1ST_1024"]["W_P"]
        weightResultDict["W_1ST_1024"]["W_N"] = weightResultDict["W_1ST_384"]["W_N"] + weightResultDict["W_1ST_640"]["W_N"] + weightResultDict["W_1ST_1024"]["W_N"]

        weightResultDict["W_1ST_2048"]["W_P"] = weightResultDict["W_1ST_384"]["W_P"] + weightResultDict["W_1ST_640"]["W_P"] + weightResultDict["W_1ST_1024"]["W_P"] + weightResultDict["W_1ST_2048"]["W_P"]
        weightResultDict["W_1ST_2048"]["W_N"] = weightResultDict["W_1ST_384"]["W_N"] + weightResultDict["W_1ST_640"]["W_N"] + weightResultDict["W_1ST_1024"]["W_N"] + weightResultDict["W_1ST_2048"]["W_N"]

        weightResultDict["W_1ST_3584"]["W_P"] = weightResultDict["W_1ST_128"]["W_P"] + weightResultDict["W_1ST_256"]["W_P"]  + weightResultDict["W_1ST_384"]["W_P"] \
                                              + weightResultDict["W_1ST_640"]["W_P"] + weightResultDict["W_1ST_2048"]["W_P"] + weightResultDict["W_1ST_3584"]["W_P"]
        weightResultDict["W_1ST_3584"]["W_N"] = weightResultDict["W_1ST_128"]["W_N"] + weightResultDict["W_1ST_256"]["W_N"]  + weightResultDict["W_1ST_384"]["W_N"] \
                                              + weightResultDict["W_1ST_640"]["W_N"] + weightResultDict["W_1ST_2048"]["W_N"] + weightResultDict["W_1ST_3584"]["W_N"]
        return None

    def calcWeight(self,weightName,weightResultDict,list_Weighting_Second_Stage_P,list_Weighting_Second_Stage_N):
        if weightName not in weightResultDict :
          return None
        print("WEIGHT",weightName)
        Weighting_Second_Stage_P=np.array(list_Weighting_Second_Stage_P)
        Weighting_Second_Stage_P=np.diag(Weighting_Second_Stage_P)
        Weighting_Second_Stage_N=np.array(list_Weighting_Second_Stage_P)
        Weighting_Second_Stage_N=np.diag(Weighting_Second_Stage_N)

        #for calibType in weightResultDict[weightName].keys() :
        calibTypeList = ["SWP","SWPB","SWN","SWNB"]
        for calibType in calibTypeList :
          if calibType not in weightResultDict[weightName] :
            print("MISSING calibType in weightResultDict")
            return None
          PArray = weightResultDict[weightName][calibType]["P"]
          NArray = weightResultDict[weightName][calibType]["N"]
          calibVal = PArray.dot(Weighting_Second_Stage_P)+NArray.dot(Weighting_Second_Stage_N)
          calibVal = np.sum(calibVal, axis=1)
          calibVal = np.mean(calibVal)
          weightResultDict[weightName][calibType]["val"] = calibVal

        for calibType in calibTypeList :
          if calibType not in weightResultDict[weightName] :
            print("MISSING calibType in weightResultDict")
            return None
          if "val" not in weightResultDict[weightName][calibType] :
            print("MISSING val in weightResultDict")
            return None
        SWP  = weightResultDict[weightName]["SWP"]["val"]
        SWPB = weightResultDict[weightName]["SWPB"]["val"]
        SWN  = weightResultDict[weightName]["SWN"]["val"]
        SWNB = weightResultDict[weightName]["SWNB"]["val"]
        weightResultDict[weightName]["W_P"] = SWP - SWPB
        weightResultDict[weightName]["W_N"] =SWNB -SWN
        return None      

    #def getWeightBits(self,weightName,coluta,MSBchannel,LSBchannel,nRepeats):
    def getWeightBits(self,weightName,coluta,MSBchannel,LSBchannel):
        #cal control
        CAL_Config = configparser.ConfigParser()
        CAL_Config.read("./config/COLUTAV3_PipelineSARCalibrationControls.cfg")

        chLabelDict = { 'channel1':'ch1','channel2':'ch2','channel3':'ch3','channel4':'ch4','channel5':'ch5','channel6':'ch6','channel7':'ch7','channel8':'ch8'}
        if MSBchannel not in chLabelDict :
          print("INVALID CH")
          return None
        MSBSectionName = chLabelDict[MSBchannel]

        calibTypeList = ["SWP","SWPB","SWN","SWNB"]
        bitArrayDict = {}
        for calibType in calibTypeList :
          #do configuration
          SARCALEN  = CAL_Config.get("SARCalibrationControls", str(weightName) + "_SARCALEN_" + str(calibType) )
          CALDIR    = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALDIR_" + str(calibType) )
          CALPNDAC  = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALPNDAC_" + str(calibType) )
          CALREGA   = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGA_" + str(calibType) )
          CALREGB   = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGB_" + str(calibType) )

          self.GUI.chips[coluta].setConfiguration(MSBSectionName,'SARCALEN', SARCALEN)
          self.GUI.chips[coluta].setConfiguration(MSBSectionName,'CALDIR', CALDIR)
          self.GUI.chips[coluta].setConfiguration(MSBSectionName,'CALPNDAC', CALPNDAC)
          self.GUI.chips[coluta].setConfiguration(MSBSectionName,'CALREGA', CALREGA)
          self.GUI.chips[coluta].setConfiguration(MSBSectionName,'CALREGB', CALREGB)
          self.GUI.sendUpdatedConfigurations()
          time.sleep(0.1)

          #record data
          #BitsArrayP , BitsArrayN  = self.SARCalibDataTaking(
          #            weightName + '_' + calibType ,coluta,MSBchannel ,LSBchannel ,nRepeats ,SARCALEN  ,CALDIR  ,CALPNDAC  ,CALREGA  ,CALREGB  )
          result = self.SARCalibDataTaking(weightName + '_' + calibType ,coluta,MSBchannel ,LSBchannel)
          if result == None : 
            return None
          BitsArrayP , BitsArrayN  = result
          bitArrayDict[calibType] = {"P":BitsArrayP , "N":BitsArrayN}
        
        return bitArrayDict


    #def SARCalibDataTaking(self,Evaluating_Indicator,coluta, MSBchannel,LSBchannel,nRepeats,SARCALEN,CALDIR,CALPNDAC,CALREGA,CALREGB):
    def SARCalibDataTaking(self,Evaluating_Indicator,coluta, MSBchannel,LSBchannel):
        self.takeData()
        if coluta not in self.dataMap :
          return None
        if MSBchannel not in self.dataMap[coluta] :
          return None
        if LSBchannel not in self.dataMap[coluta] :
          return None

        MSB_list_string = self.dataMap[coluta][MSBchannel]
        LSB_list_string = self.dataMap[coluta][LSBchannel]
        BitsArrayP, BitsArrayN = self.sarCalibListDataToTwentyBits(MSB_list_string,LSB_list_string)
        return BitsArrayP, BitsArrayN


    def sarCalibListDataToTwentyBits(self,MSBList,LSBList):
        ListLength=len(MSBList)
        BitsArrayP  = 999*np.ones((ListLength,20),dtype=np.float)
        BitsArrayN  = 999*np.ones((ListLength,20),dtype=np.float)
        for i in range(ListLength):
            for bitPos in range(15,0-1,-1):
              LSBbit = str(LSBList[i][bitPos])
              if LSBbit == '1':
                BitsArrayP[i,bitPos+4]=+1
                BitsArrayN[i,bitPos+4]=+0
              elif LSBbit == '0':
                BitsArrayP[i,bitPos+4]=+0
                BitsArrayN[i,bitPos+4]=-1
              elif LSBbit != '1' and LSBbit != '0':
                BitsArrayP[i,bitPos+4]=500000000000000000
                BitsArrayN[i,bitPos+4]=500000000000000000

              if bitPos < 12 : continue
              MSBbit = str(MSBList[i][bitPos])
              if MSBbit == '1':
                BitsArrayP[i,bitPos-12]=+1
                BitsArrayN[i,bitPos-12]=+0
              elif MSBbit == '0':
                BitsArrayP[i,bitPos-12]=+0
                BitsArrayN[i,bitPos-12]=-1
              elif MSBbit != '1' and MSBbit != '0':
                BitsArrayP[i,bitPos-12]=500000000000000000
                BitsArrayN[i,bitPos-12]=500000000000000000

        return BitsArrayP, BitsArrayN
        #debug only below
        for i in range(ListLength):
            print(i)
            print("\t",BitsArrayP[i])
            print("\t",BitsArrayN[i])
         
        return BitsArrayP, BitsArrayN
