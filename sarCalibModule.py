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
        pass

    def testWriteMdacCal(self):
        coluta = "coluta20"
        channel = "channel7"
        channelLabel = "ch7"
        mdacCorr = {'MDACCorrectionCode0': 70.93294117647065, 'MDACCorrectionCode1': 4163.7532085702705,\
                    'MDACCorrectionCode2': 4162.98000336078, 'MDACCorrectionCode3': 4164.754957983194,\
                    'MDACCorrectionCode4': 4162.9218487394955, 'MDACCorrectionCode5': 4163.0388126280595,\
                    'MDACCorrectionCode6': 4164.028739495798, 'MDACCorrectionCode7': 4167.986220803226}
        mdacCorrDdpu = {}
        mdacCorrDdpu['MDACCorrectionCode0'] = mdacCorr['MDACCorrectionCode0']
        mdacCorrDdpu['MDACCorrectionCode1'] = mdacCorrDdpu['MDACCorrectionCode0']+mdacCorr['MDACCorrectionCode1']
        mdacCorrDdpu['MDACCorrectionCode2'] = mdacCorrDdpu['MDACCorrectionCode1']+mdacCorr['MDACCorrectionCode2']
        mdacCorrDdpu['MDACCorrectionCode3'] = mdacCorrDdpu['MDACCorrectionCode2']+mdacCorr['MDACCorrectionCode3']
        mdacCorrDdpu['MDACCorrectionCode4'] = mdacCorrDdpu['MDACCorrectionCode3']+mdacCorr['MDACCorrectionCode4']
        mdacCorrDdpu['MDACCorrectionCode5'] = mdacCorrDdpu['MDACCorrectionCode4']+mdacCorr['MDACCorrectionCode5']
        mdacCorrDdpu['MDACCorrectionCode6'] = mdacCorrDdpu['MDACCorrectionCode5']+mdacCorr['MDACCorrectionCode6']
        mdacCorrDdpu['MDACCorrectionCode7'] = mdacCorrDdpu['MDACCorrectionCode6']+mdacCorr['MDACCorrectionCode7']

        for corr in mdacCorrDdpu :
          if corr not in self.GUI.chips[coluta][channelLabel] :
            continue
          val = mdacCorrDdpu[corr]
          val4x = round(4*val)
          valLength = 17
          binString = format(val4x,'0'+str(valLength)+'b')
          self.GUI.chips[coluta].setConfiguration(channelLabel,corr,binString)
          boxName = coluta + channelLabel + corr + "Box"
          self.GUI.updateBox(boxName, binString)
        self.GUI.sendUpdatedConfigurations()    


    def testMdacCal(self):
        #generic module test function
        coluta = "coluta20"
        channel = "channel7"
        channelLabel = "ch7"

        #'MDACCALEN', 'CALFLASH', 'CALMDAC' , FLAGEN, MDACCorrectionCode0
        self.GUI.chips[coluta].setConfiguration(channelLabel,"FLAGEN", str(0) )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCALEN",str(1) )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode0",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode1",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode2",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode3",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode4",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode5",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode6",'00000000000000000' )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCorrectionCode7",'00000000000000000' )
        self.GUI.sendUpdatedConfigurations()

        mdacCalList = [128,128,64 ,64 ,32 ,32 ,16 ,16 ,8  ,8  ,4  ,4  ,2  ,2  ,1  ,1  ]
        flashList =   [0  ,1  ,1  ,3  ,3  ,7  ,7  ,15 ,15 ,31 ,31 ,63 ,63 ,127,127,255]
        stepMeas = {}
        for stepNum in range(0,16,1):
          mdacCalVal = str( format(mdacCalList[stepNum],'08b')  )
          flashVal = str(   format(flashList[stepNum],'08b') )
          self.GUI.chips[coluta].setConfiguration(channelLabel,"CALMDAC",str(mdacCalVal) )
          self.GUI.chips[coluta].setConfiguration(channelLabel,"CALFLASH",str(flashVal)  )
          self.GUI.sendUpdatedConfigurations()
          time.sleep(0.1)
          self.takeData()
          #print( self.dataMap[coluta][channel][0:4] )
          decArray = self.convert_to_dec(self.dataMap[coluta][channel] )
          print( stepNum, np.mean(decArray),np.std(decArray))
          stepMeas[stepNum] = np.mean(decArray)
 
        self.GUI.chips[coluta].setConfiguration(channelLabel,"CALMDAC", str(format(0,'08b')) )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"CALFLASH",str(format(0,'08b'))  )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"FLAGEN", str(1) )
        self.GUI.chips[coluta].setConfiguration(channelLabel,"MDACCALEN",str(0) )
        self.GUI.sendUpdatedConfigurations()      

        mdacCorr = {}
        mdacCorr["MDACCorrectionCode0"] = stepMeas[0] - stepMeas[1]
        mdacCorr["MDACCorrectionCode1"] = stepMeas[2] - stepMeas[3]
        mdacCorr["MDACCorrectionCode2"] = stepMeas[4] - stepMeas[5]
        mdacCorr["MDACCorrectionCode3"] = stepMeas[6] - stepMeas[7]
        mdacCorr["MDACCorrectionCode4"] = stepMeas[8] - stepMeas[9]
        mdacCorr["MDACCorrectionCode5"] = stepMeas[10] - stepMeas[11]
        mdacCorr["MDACCorrectionCode6"] = stepMeas[12] - stepMeas[13]
        mdacCorr["MDACCorrectionCode7"] = stepMeas[14] - stepMeas[15]
        print(mdacCorr)

        return

    def convert_to_dec(self,binArray):
        decArray = []
        for num in binArray :
          dec  = int(''.join([str(x) for x in num]),2)
          decArray.append(dec)
        return decArray

    def testSarConstantWrite(self):
        coluta = "coluta20"
        channel = "channel7"
        channelLabel = "ch7"
        
        chWeightResultDict = {"W_1ST_3584" : 3572.20               ,"W_1ST_2048" : 2040.87              ,"W_1ST_1024" : 1021.80,\
                              "W_1ST_640" : 639.17                 ,"W_1ST_384" : 383.71                ,"W_1ST_256" : 256.15  ,\
                              "W_1ST_128" : 127.48                 ,"W_2ND_224" : 219.34                ,"W_2ND_128" : 125.96  ,\
                              "W_2ND_64" : 62.74                   ,"W_2ND_32" : 31.55                  ,"W_2ND_24" : 23.63    ,\
                              "W_2ND_16" : 15.86                   ,"W_2ND_10" : 10.                    ,"W_2ND_6"  : 6. }

        sarCalibDdpuConfigs = {"W_1ST_3584" : 'SARCorrectionCode20',"W_1ST_2048" : 'SARCorrectionCode19',"W_1ST_1024" : 'SARCorrectionCode18' ,\
                               "W_1ST_640" : 'SARCorrectionCode17' ,"W_1ST_384" : 'SARCorrectionCode16' ,"W_1ST_256" : 'SARCorrectionCode15'  ,\
                               "W_1ST_128" : 'SARCorrectionCode14' ,"W_2ND_224" : 'SARCorrectionCode13' ,"W_2ND_128" : 'SARCorrectionCode12'  ,\
                               "W_2ND_64" : 'SARCorrectionCode11'  ,"W_2ND_32" : 'SARCorrectionCode10'  ,"W_2ND_24" : 'SARCorrectionCode9'    ,\
                               "W_2ND_16" : 'SARCorrectionCode8'   ,"W_2ND_10" : 'SARCorrectionCode7'   ,"W_2ND_6"  : 'SARCorrectionCode6'}

        mapSarCorrToWeights = {'SARCorrectionCode20' : "W_1ST_3584",'SARCorrectionCode19' : "W_1ST_2048",'SARCorrectionCode18' : "W_1ST_1024" ,\
                               'SARCorrectionCode17' : "W_1ST_640" ,'SARCorrectionCode16' : "W_1ST_384" ,'SARCorrectionCode15' : "W_1ST_256"  ,\
                               'SARCorrectionCode14' : "W_1ST_128" ,'SARCorrectionCode13' : "W_2ND_224" ,'SARCorrectionCode12' : "W_2ND_128"  ,\
                               'SARCorrectionCode11' : "W_2ND_64"  ,'SARCorrectionCode10' : "W_2ND_32"  ,'SARCorrectionCode9'  : "W_2ND_24"   ,\
                               'SARCorrectionCode8' : "W_2ND_16"   ,'SARCorrectionCode7'  : "W_2ND_10"  ,'SARCorrectionCode6'  : "W_2ND_6"}
                               
        sarCorrLengths      = {'SARCorrectionCode20' : 14,'SARCorrectionCode19' : 14,'SARCorrectionCode18' : 13 ,\
                               'SARCorrectionCode17' : 12 ,'SARCorrectionCode16' : 11 ,'SARCorrectionCode15' : 11  ,\
                               'SARCorrectionCode14' : 10 ,'SARCorrectionCode13' : 10 ,'SARCorrectionCode12' : 10  ,\
                               'SARCorrectionCode11' : 9  ,'SARCorrectionCode10' : 8  ,'SARCorrectionCode9'  : 7   ,\
                               'SARCorrectionCode8' : 7   ,'SARCorrectionCode7'  : 6  ,'SARCorrectionCode6'  : 5}
        
        for corr in mapSarCorrToWeights :
          if corr not in self.GUI.chips[coluta][channelLabel] :
            continue
          weightLabel = mapSarCorrToWeights[corr]
          if weightLabel not in chWeightResultDict :
            continue
          val = chWeightResultDict[weightLabel]
          valNormed = val/chWeightResultDict["W_1ST_3584"]*3584*0.97
          val4x = round(4*valNormed)
          if val4x > 16383 :
            print("OVERFLOW")
          valLength = sarCorrLengths[corr]
          #binString = format(6,'014b')
          binString = format(val4x,'0'+str(valLength)+'b')
          #print( corr, self.GUI.chips[coluta][channelLabel][corr] , len(self.GUI.chips[coluta][channelLabel][corr]) ,"\t",val4x, binString )
          #print( corr, len(self.GUI.chips[coluta][channelLabel][corr]) ,"\t",len(binString) )
          self.GUI.chips[coluta].setConfiguration(channelLabel,corr,binString)
          #print( corr, self.GUI.chips[coluta][channelLabel][corr] ,"\t",val4x, binString )
          boxName = coluta + channelLabel + corr + "Box"
          self.GUI.updateBox(boxName, binString)
        self.GUI.sendUpdatedConfigurations()
        #look at current channel DDPU config
        #print(self.GUI.chips[coluta][channelLabel])
        #print(chWeightResultDict)
        pass

    def printData(self):
        for asicLabel in self.dataMap :
          for chanLabel in self.dataMap[asicLabel] :
            if len( self.dataMap[asicLabel][chanLabel] ) > 0 :
              print(asicLabel,"\t",chanLabel,"\t",self.dataMap[asicLabel][chanLabel][0] )
        return None

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

        #calculate the weights given the recorded data
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
          totalWeight = ( weightResultDict[weightName]["W_P"] + weightResultDict[weightName]["W_N"] ) / 2.0
          weightResultDict[weightName]["TOTAL"] = totalWeight
          print(weightName,"P",weightResultDict[weightName]["W_P"])
          print(weightName,"N",weightResultDict[weightName]["W_N"])
          print(weightName,"TOTAL",weightResultDict[weightName]["TOTAL"])
          
        print("DONE TEST")
        return None

    def takeTriggerData(self):
        """Runs takeTriggerData script"""
        subprocess.call("python takeTriggerData.py -o "+self.outputPath+" -t trigger -a 20 -s 1", shell=True)
        time.sleep(1)

    def removeTriggerData(self):
        """Runs takeTriggerData script"""
        subprocess.call("rm "+self.outputPathStamped, shell=True)
        time.sleep(0.1)

    def takeData(self):
        self.takeTriggerData()
        maxReads = 1000000 #need to optimize, currently gets about 5950 samples with 1000000
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
          #use position dict above to correctly update the list_Weighting_Second_Stage_P/N lists
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
          result = self.SARCalibDataTaking(weightName + '_' + calibType ,coluta,MSBchannel ,LSBchannel)
          if result == None : 
            return None
          BitsArrayP , BitsArrayN  = result
          bitArrayDict[calibType] = {"P":BitsArrayP , "N":BitsArrayN}
        
        return bitArrayDict


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
