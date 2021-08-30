import numpy as np
import configparser
import time
import subprocess
import parseDataMod #feb2 version only
import math
import sys
from calibModule import CALIBMODULE

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
        self.sarWeights = {}
        self.mdacWeights = {}

        self.cv3tbVersion = False
        self.feb2Version = True

        self.guiColutaId = None
        self.guiColutaChId = None

        self.chLabelDict = { 'channel1': ('ch1','ch2','channel2'), 'channel2': ('ch2','ch1','channel1'), 'channel3': ('ch3','ch4','channel4'), 'channel4': ('ch4','ch3','channel3') , 'channel5': ('ch5','ch6','channel6'), 'channel6': ('ch6','ch5','channel5'), 'channel7': ('ch7','ch8','channel8'), 'channel8': ('ch8','ch7','channel7') }

        self.calibModule = CALIBMODULE()

    ############################################
    ########           Debug            #######
    ############################################

    def test(self):
        import timeit
        	#test calib process
        	#self.doSarCalib("coluta20","channel8")
        	#self.writeSarConstant("coluta20","channel8")
        
        #this creates a list of coluta names
        colutas = [f"coluta{i}" for i in range(13,21)]
        colutas.remove("coluta17") #Might have to deactivate this line of code


        print("We are doing the multichannel Sar Calibration")
        self.doSarCalibMultichannel(colutas, [f"channel{j}" for j in range (5,9)])
        print("End Sar Calibration Debugging")

 
        #start_time = timeit.default_timer()
        #print("We are doing the multichannel Mdac Calibration")
        #self.doMdacCalMultichannel(colutas, [f"channel{j}" for j in range (5,9)])
        #print("Time for multichannel MDAC calibration:", str(timeit.default_timer()-start_time))       

        #start_time = timeit.default_timer()
        #self.doMdacCalParallel(["coluta13", "coluta14", "coluta15", "coluta16"],"channel8")
        #print("Time for *parallel* MDAC calibration:", str(timeit.default_timer()-start_time))

        #self.writeMdacCal("coluta20","channel8")

        #print("SAR WEIGHTS")
        #print(self.sarWeights)
        #self.printSarWeights()

        #print("MDAC WEIGHTS")
        #print(self.mdacWeights)

        #start_time = timeit.default_timer()
        #self.doMdacCal("coluta13", "channel8")
        #print("Time for standard MDAC calibration:", str(timeit.default_timer()-start_time))

        #print("MDAC WEIGHTS")
        #print(self.mdacWeights)
        return None

    ############################################
    ########        Do Calibration       #######
    ############################################

    def runSarCalibInFeb2Gui(self):
        print("DO SAR CALIB")
        self.getSarMdacCalibChInFeb2GUI()
        self.doSarCalib(self.guiColutaId,self.guiColutaChId)

        print("SAR WEIGHTS","\t",self.guiColutaId,"\t",self.guiColutaChId)
        print(self.sarWeights)
        self.printSarWeights()
        
        print("WRITE SAR CONSTANTS","\t",self.guiColutaId,"\t",self.guiColutaChId)
        self.writeSarConstant(self.guiColutaId,self.guiColutaChId)
        return None

    def runMdacCalibInFeb2Gui(self):
        print("DO MDAC CALIB")
        self.getSarMdacCalibChInFeb2GUI()
        self.doMdacCal(self.guiColutaId,self.guiColutaChId)

        print("MDAC WEIGHTS","\t",self.guiColutaId,"\t",self.guiColutaChId)
        print(self.mdacWeights)

        self.writeMdacCal(self.guiColutaId,self.guiColutaChId)
        return None

    def runFullCalibInFeb2Gui(self):
        chips = ["coluta13","coluta14","coluta15","coluta16","coluta17","coluta18","coluta19","coluta20"]
        #channels = ["channel1","channel2","channel3","channel4","channel5","channel6","channel7","channel8"]
        #chips = ["coluta20"]
        channels = ["channel5","channel6","channel7","channel8"]
        for chip in chips :
          for chan in channels :
            self.doSarCalib(chip,chan)
            self.writeSarConstant(chip,chan)
            self.calibModule.addSarCalib(self.GUI.boardID,chip,chan,self.sarWeights)
            self.doMdacCal(chip,chan)
            self.writeMdacCal(chip,chan)
            self.calibModule.addMdacCalib(self.GUI.boardID,chip,chan,self.mdacWeights)
        return None

    def getSarMdacCalibChInFeb2GUI(self):
        colutaBox = getattr(self.GUI, 'stdRunsCalibColutaSelectBox')
        colutaId = None
        try:
            colutaId = colutaBox.currentText()
        except:
            print("Invalid channelId")
        chBox = getattr(self.GUI, 'stdRunsCalibColutaChSelectBox')
        chId = None
        try:
            chId = chBox.currentText()
        except:
            print("Invalid channelId")

        print(colutaId,chId)
        self.guiColutaId = colutaId
        self.guiColutaChId = chId
        return None

    def getFullCalibInFeb2Gui(self):
        chips = ["coluta13","coluta14","coluta15","coluta16","coluta17","coluta18","coluta19","coluta20"]
        channels = ["channel1","channel2","channel3","channel4","channel5","channel6","channel7","channel8"]
        for chip in chips :
          for chan in channels :
            result = self.calibModule.getSarCalib(self.GUI.boardID,chip,chan)
            if result != None :
              self.sarWeights = result
              self.writeSarConstant(chip,chan)
            result = self.calibModule.getMdacCalib(self.GUI.boardID,chip,chan)
            if result != None :
              self.mdacWeights = result
              self.writeMdacCal(chip,chan)
        return None

    def testRestoreCalib(self,coluta,channel):
        if coluta not in self.GUI.chips :
          print("INVALID ASIC")
          return None
        if channel not in self.chLabelDict :
          print("INVALID CH")
          return None
        MSBchannel = channel
        LSBchannel = self.chLabelDict[channel][2]
        MSBSectionName = self.chLabelDict[channel][0]
        LSBSectionName = self.chLabelDict[channel][1]

        #get initial COLUTA config here
        initConfig = self.getConfig(coluta)

        #try programming something
        self.doConfig(coluta,MSBSectionName,'OutputMode', '1')
        self.doConfig(coluta,MSBSectionName,'EXTToSAR', '0')
        self.doConfig(coluta,LSBSectionName,'DATAMUXSelect', '1')
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess:
            print("FAILED WRITE BEFORE RESTORING INITIAL CONFIG")

        #restore initial config here
        self.restoreConfig(coluta,initConfig)
        return None
 
    ############################################
    ########          Helpers            #######
    ############################################

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

    def doConfig(self,colutaName,sectionName,configName,configString):
        #different methods for different GUIs
        if self.cv3tbVersion == True :
          self.GUI.configurations[sectionName].setConfiguration(configName,configString)
        if self.feb2Version == True :
          self.GUI.chips[colutaName].setConfiguration(sectionName,configName,configString)
        return

    def getConfig(self,colutaName):
        if self.cv3tbVersion == True :
          return self.GUI.configuration.clone()
        if self.feb2Version == True :
          return self.GUI.chips[colutaName].clone()
        return None
   
    def restoreConfig(self,colutaName,config):
        if self.cv3tbVersion == True :
          self.GUI.configurations = config
        if self.feb2Version == True :
          self.GUI.chips[colutaName] = config
          self.GUI.sendFullCOLUTAConfig(colutaName)
        return None

    def printData(self):
        for asicLabel in self.dataMap :
          for chanLabel in self.dataMap[asicLabel] :
            if len( self.dataMap[asicLabel][chanLabel] ) > 0 :
              print(asicLabel,"\t",chanLabel,"\t",self.dataMap[asicLabel][chanLabel][0] )
        return None

    def takeData(self, coluta="", trigger=False):
        """Takes single ADC data if one coluta is passed; takes trigger data if trigger is true"""
        self.GUI.nSamples = 1000000 # Need to optimize, currently gets about 5950 samples with 1000000
        self.GUI.nSamplesBox.document().setPlainText(str(self.GUI.nSamples))
        # Data taking mode
        if trigger:
            print("TAKE TRIGGER DATA")
            getattr(self.GUI,'daqModeBox').setCurrentIndex(0) #ensure trigger mode
        else:
            print("TAKE DATA",coluta)
            colutaIndexDict = { "coluta20":0,"coluta19":1,"coluta18":2,"coluta17":3,"coluta16":4,"coluta15":5,"coluta14":6,"coluta13":7}
            if coluta not in colutaIndexDict:
                print(f"Could not find {coluta}...")
                return None
            adcIndex = colutaIndexDict[coluta]
            getattr(self.GUI,'daqModeBox').setCurrentIndex(1) #ensure ADC mode
            getattr(self.GUI,'daqADCSelectBox').setCurrentIndex(adcIndex)

        chanData = self.GUI.takeTriggerData_noDataFile('sarCalib')

        # Sorts data by COLUTA/channel
        self.dataMap = {}
        for chanNum,data in enumerate(chanData) :
          loData = data[0]
          hiData = data[1]
          if len(loData) == 0 or len(hiData) == 0 : continue
          # Check for fake data in parsed data, corresponds to channel without data recorded
          if isinstance(loData[0], list) : continue

          #loDataBin = [ parseDataMod.convert_to_bin(x) for x in loData ]
          #hiDataBin = [ parseDataMod.convert_to_bin(x) for x in hiData ]
          loDataBin = [ '{0:016b}'.format(x) for x in loData ]
          hiDataBin = [ '{0:016b}'.format(x) for x in hiData ]          

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

    ############################################
    ########  Parallel MDAC Calibration  #######
    ############################################

    def convert_to_dec_np(self,binArray):
        """Helper that converts binary array to decimal"""
        decArray = np.empty(binArray.shape[0], dtype=int)
        for i in range(binArray.shape[0]):
          dec  = int(''.join([str(x) for x in binArray[i]]),2)
          decArray[i] = dec
        return decArray


    def doMdacCalMultichannel(self, colutas, channels):
        """Calibrates MDAC for given COLUTAs/channels"""
        try:
            channelLabel = {channel : self.chLabelDict[channel][0] for channel in channels}
        except KeyError:
            print("Could not find channel(s) in MDAC calibration...")
            return None

        # Gets initial configurations
        initConfig = {coluta : self.getConfig(coluta) for coluta in colutas}
       
        # Sets configuration for MDAC calibration
        for coluta in colutas:
            for channel in channels:
                self.doConfig(coluta, channelLabel[channel], "FLAGEN", str(0))
                self.doConfig(coluta, channelLabel[channel], "MDACCALEN", str(1))
                for i in range(8):
                    self.doConfig(coluta, channelLabel[channel], f"MDACCorrectionCode{i}", '00000000000000000')
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess: sys.exit(f"MDAC Calibration stopped: readback failed while setting up colutas for MDAC calibration!")
 
        # Gets MDAC measurements
        mdacCalList = [128, 128, 64, 64, 32, 32, 16, 16, 8, 8, 4, 4, 2, 2, 1, 1]
        flashList = [0, 1, 1, 3, 3, 7, 7, 15, 15, 31, 31, 63, 63, 127, 127, 255]
        stepMeas = {coluta : {ch : {} for ch in channels} for coluta in colutas}

        for stepNum in range(0, 16, 1):
            mdacCalVal = str(format(mdacCalList[stepNum],'08b'))
            flashVal = str(format(flashList[stepNum],'08b'))
 
            # Updates MDAC calibration + flash value configurations
            for coluta in colutas:
                for channel in channels:
                    self.doConfig(coluta,channelLabel[channel],"CALMDAC",str(mdacCalVal)) 
                    self.doConfig(coluta,channelLabel[channel],"CALFLASH",str(flashVal))
            time.sleep(0.1)
 
            # Checks readback
            readbackSuccess = self.GUI.sendUpdatedConfigurations()
            if not readbackSuccess:
                sys.exit("MDAC Calibration stopped: readback failed while updating MDAC + flash value configurations!")
            
            if len(colutas) == 1:
                self.takeData(coluta=colutas[0]) # If only one COLUTA, don't take data in all COLUTAs
            else:
                self.takeData(trigger=True) # Takes data on all COLUTA/channels if two or more COLUTAs

            for coluta in colutas:
                for channel in channels:
                    # Converts binary array to dec + finds mean of data
                    decArray = self.convert_to_dec_np(np.asarray(self.dataMap[coluta][channel]))
                    stepMeas[coluta][channel][stepNum] = np.mean(decArray)
                    std = np.std(decArray)
                    print(f"{coluta}, {channel}:", stepNum, stepMeas[coluta][channel][stepNum], std)
 
        # Restores initial configs
        for coluta in initConfig.keys(): self.restoreConfig(coluta, initConfig[coluta])

        # Determines weights
        self.mdacWeights = {coluta : {ch : {} for ch in channels} for coluta in colutas}
        for coluta in colutas:
            for ch in channels:
                for i in range(8):
                    self.mdacWeights[coluta][ch][f"MDACCorrectionCode{i}"] = stepMeas[coluta][ch][i*2] - stepMeas[coluta][ch][(i*2)+1]
        try:
            from tabulate import tabulate
        except:
            print("You need the tabulate package...")
            print(self.mdacWeights)
            return
        print(self.mdacWeights)
        # Writes output to a table 
        with open("MDACCalibConstants.txt", "w") as f:
            for coluta in colutas:
                f.write("++++++++++++++++++++++++++++++++")
                f.write("++  {coluta}  ++".format(coluta=coluta))
                f.write("++++++++++++++++++++++++++++++++\n\n")
                for ch in channels:
                    f.write(f"{ch}\n")
                    to_table = [[corr, self.mdacWeights[coluta][ch][corr]] for corr in self.mdacWeights[coluta][ch].keys()]
                    table = tabulate(to_table,  showindex="never", tablefmt="psql")
                    f.write(table)
                    f.write("\n \n")

    def writeMdacCalMultichanel(self, colutas, channels):
        """Writes MDAC constants to board"""
        try:
            channelLabel = {channel : self.chLabelDict[channel][0] for channel in channels}
        except KeyError:
            print("Could not find channel(s) in MDAC calibration...")
            return None        
       
        for coluta in colutas:
            for ch in channels:
                mdacCorrDdpu = {}

                mdacCorrDdpu['MDACCorrectionCode0'] = self.mdacWeights[coluta][ch]['MDACCorrectionCode0']
                for i in range(1,8): 
                    mdacCorrDdpu[f'MDACCorrectionCode{i}'] = mdacCorrDdpu[f'MDACCorrectionCode{i-1}']+self.mdacWeights[coluta][ch][f'MDACCorrectionCode{i}']
                
                for corr in mdacCorrDdpu:
                    if corr not in self.GUI.chips[coluta][channelLabel[ch]]:
                       continue
                    val = round(4*mdacCorrDdpu[corr])
                    if (val < 0) or (val >= 131071): 
                        val = 0
                        print("INVALID value in MDAC calibration!")
                    binString = format(val,'017b') # Binary string with 17 zeroes as placeholders
                    self.doConfig(coluta, channelLabel[ch], corr, binString)
                    boxName = coluta + channelLabel[ch] + corr + "Box"
                    self.GUI.updateBox(boxName, binString)

        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        # Check if write succeeded
        if not readbackSuccess:
            print("Writing MDAC constants failed!")

    ############################################
    ########     Old MDAC Calibration    #######
    ############################################

    def convert_to_dec(self,binArray):
        decArray = []
        for num in binArray :
          dec  = int(''.join([str(x) for x in num]),2)
          decArray.append(dec)
        return decArray

    def doMdacCal(self,coluta,channel):
        if channel not in self.chLabelDict :
          return None
        channelLabel = self.chLabelDict[channel][0]

        #get initial COLUTA config here
        initConfig = self.getConfig(coluta)

        #'MDACCALEN', 'CALFLASH', 'CALMDAC' , FLAGEN, MDACCorrectionCode0
        self.doConfig(coluta,channelLabel,"FLAGEN", str(0) )
        self.doConfig(coluta,channelLabel,"MDACCALEN",str(1) )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode0",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode1",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode2",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode3",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode4",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode5",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode6",'00000000000000000' )
        self.doConfig(coluta,channelLabel,"MDACCorrectionCode7",'00000000000000000' )
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess:
          sys.exit("MDAC CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")

        mdacCalList = [128,128,64 ,64 ,32 ,32 ,16 ,16 ,8  ,8  ,4  ,4  ,2  ,2  ,1  ,1  ]
        flashList =   [0  ,1  ,1  ,3  ,3  ,7  ,7  ,15 ,15 ,31 ,31 ,63 ,63 ,127,127,255]
        stepMeas = {}
        for stepNum in range(0,16,1):
          mdacCalVal = str( format(mdacCalList[stepNum],'08b')  )
          flashVal = str(   format(flashList[stepNum],'08b') )
          self.doConfig(coluta,channelLabel,"CALMDAC",str(mdacCalVal) )
          self.doConfig(coluta,channelLabel,"CALFLASH",str(flashVal)  )
          readbackSuccess = self.GUI.sendUpdatedConfigurations()
          time.sleep(0.1)
          if not readbackSuccess:
            sys.exit("MDAC CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")
          self.takeData(coluta)
          #print( self.dataMap[coluta][channel][0:4] )
          decArray = self.convert_to_dec(self.dataMap[coluta][channel] )
          print( stepNum, np.mean(decArray),np.std(decArray))
          stepMeas[stepNum] = np.mean(decArray)
 
        #done, reset config
        #self.doConfig(coluta,channelLabel,"CALMDAC", str(format(0,'08b')) )
        #self.doConfig(coluta,channelLabel,"CALFLASH",str(format(0,'08b'))  )
        #self.doConfig(coluta,channelLabel,"FLAGEN", str(1) )
        #self.doConfig(coluta,channelLabel,"MDACCALEN",str(0) )
        #self.GUI.sendUpdatedConfigurations()      
        self.restoreConfig(coluta,initConfig)

        self.mdacWeights
        self.mdacWeights = {}
        self.mdacWeights["MDACCorrectionCode0"] = stepMeas[0] - stepMeas[1]
        self.mdacWeights["MDACCorrectionCode1"] = stepMeas[2] - stepMeas[3]
        self.mdacWeights["MDACCorrectionCode2"] = stepMeas[4] - stepMeas[5]
        self.mdacWeights["MDACCorrectionCode3"] = stepMeas[6] - stepMeas[7]
        self.mdacWeights["MDACCorrectionCode4"] = stepMeas[8] - stepMeas[9]
        self.mdacWeights["MDACCorrectionCode5"] = stepMeas[10] - stepMeas[11]
        self.mdacWeights["MDACCorrectionCode6"] = stepMeas[12] - stepMeas[13]
        self.mdacWeights["MDACCorrectionCode7"] = stepMeas[14] - stepMeas[15]
        print(self.mdacWeights)

        return

    def writeMdacCal(self,coluta,channel):
        if channel not in self.chLabelDict :
          return None
        channelLabel = self.chLabelDict[channel][0]

        mdacCorr = self.mdacWeights
        if 'MDACCorrectionCode0' not in mdacCorr :
          return None
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
          if (val4x < 0) or (val4x >= 131071) :
            val4x = 0
            print("INVALID VALUE IN MDAC CALIBRATION")
          valLength = 17
          binString = format(val4x,'0'+str(valLength)+'b')
          self.doConfig(coluta,channelLabel,corr,binString)
          boxName = coluta + channelLabel + corr + "Box"
          self.GUI.updateBox(boxName, binString)
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess:
            print("WRITING MDAC CAL FAILED: ONE OR MORE READBACKS FAILED")

    
    ############################################
    #######   SAR Parallel Calibration   #######
    ############################################

    #Currently not working, perhaps because we need to calibrate first
    def writeSarConstantMultichannel(self, colutas, channels):
        self.scaleFactor = 0.97
        print("we began the multichannel writeSar")
        try:
          channelLabel = {channel : self.chLabelDict[channel][0] for channel in channels}
        except KeyError:
          print("Could not find channel(s) in SAR calibration...")
          return None
                 
        chWeightResultDict = self.sarWeights

        #awkward mapping between SAR weight names and DDPU constant names
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
        for coluta in colutas:
          for channel in channels:
            print("For ", coluta, " and ", channel) 
            for corr in mapSarCorrToWeights :
              if corr not in self.GUI.chips[coluta][channelLabel[channel]] :
                continue
              weightLabel = mapSarCorrToWeights[corr]
              if weightLabel not in chWeightResultDict :
                continue
              val = chWeightResultDict[weightLabel]
              valNormed = val/chWeightResultDict["W_1ST_3584"]*3584*self.scaleFactor
              val4x = round(4*valNormed)
              if val4x < 0 or val4x > 16383 :
                val4x = 0
                print("OVERFLOW, CALIB IS BAD!")
              valLength = sarCorrLengths[corr]
              binString = format(val4x,'0'+str(valLength)+'b')
              self.doConfig(coluta,channelLabel[channel],corr,binString)
              boxName = coluta + channelLabel[channel] + corr + "Box"
              self.GUI.updateBox(boxName, binString)
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess:
          sys.exit("WRITING SAR CONST FAILED: ONE OR MORE READBACKS FAILED")
        pass



    def pretty(self, d, indent=0):
       for key, value in d.items():
          print('\t' * indent + str(key))
          if isinstance(value, dict):
             pretty(value, indent+1)
          else:
             print('\t' * (indent+1) + str(value))   




 
    def doSarCalibMultichannel(self, colutas, channels):

      for coluta in colutas:
        if coluta not in self.GUI.chips:
          print("INVALID ASIC")
          return None
      for channel in channels:
        if channel not in self.chLabelDict:
          print("INVALID CH")
          return None

      # Dictionary to store some channel names and initial configurations
      MSBLSB = {}
      initConfigs = {}

      for coluta in colutas:
        # Get initial COLUTA config here
        initConfigs[coluta] = self.getConfig(coluta)
        for channel in channels:
          MSBchannel = channel
          LSBchannel = self.chLabelDict[channel][2]
          MSBSectionName = self.chLabelDict[channel][0]
          LSBSectionName = self.chLabelDict[channel][1]
          MSBLSB[(coluta, channel)] = [MSBchannel, LSBchannel, MSBSectionName, LSBSectionName]
          # Common Setting for Weighting Evaluation
          self.doConfig(coluta,MSBSectionName,'SHORTINPUT', '1')
          self.doConfig(coluta,MSBSectionName,'DREMDACToSAR', '0')
          self.doConfig(coluta,MSBSectionName,'OutputMode', '1')
          self.doConfig(coluta,MSBSectionName,'EXTToSAR', '0')
          self.doConfig(coluta,LSBSectionName,'DATAMUXSelect', '1')
      
        #Decided to test readback success for each coluta
        #This is to save time for now, but wemight want to relocate this
        #To another part of the code
        #readbackSuccess = self.GUI.sendUpdatedConfigurations()
        #if not readbackSuccess: 
          #sys.exit("SAR CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")

      nRepeats = 1
      self.GUI.nSamples = 100000
      self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples))

      #list of weights to measure
      weightsList = ["W_2ND_16","W_2ND_24","W_2ND_32","W_2ND_64","W_2ND_128","W_2ND_224",
                       "W_1ST_Unit","W_1ST_128","W_1ST_256","W_1ST_384","W_1ST_640","W_1ST_1024","W_1ST_2048","W_1ST_3584"] #Note: order matters!!!! must be done from lowest to highest weights

      CAL_Config = configparser.ConfigParser()
      CAL_Config.read("./config/COLUTAV3_PipelineSARCalibrationControls.cfg")
      calibTypeList = ["SWP","SWPB","SWN","SWNB"]


      # indexed by weightName and calibType
      SARCALEN_dict = {}
      CALDIR_dict = {}
      CALPNDAC_dict = {}
      CALREGA_dict = {}
      CALREGB_dict = {}

      for weightName in weightsList:
        for calibType in calibTypeList:
          SARCALEN_dict[(weightName, calibType)] = CAL_Config.get("SARCalibrationControls", str(weightName) + "_SARCALEN_" + str(calibType))   
          CALDIR_dict[(weightName, calibType)] = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALDIR_" + str(calibType) ) 
          CALPNDAC_dict[(weightName, calibType)] = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALPNDAC_" + str(calibType) ) 
          CALREGA_dict[(weightName, calibType)] = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGA_" + str(calibType) ) 
          CALREGB_dict[(weightName, calibType)] = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGB_" + str(calibType) ) 

      weightResultDict = {}#weightResultDict = {"TOTAL": {}}
      for weightName in weightsList:
        bitArrayDict = {}
        for calibType in calibTypeList:    
          for coluta in colutas:
            for channel in channels:
              #Retrive info for coluta/channel pair
              MSBSecName = MSBLSB[(coluta, channel)][2]
              SARCALEN = SARCALEN_dict[(weightName, calibType)]
              CALDIR = CALDIR_dict[(weightName, calibType)]
              CALPNDAC = CALPNDAC_dict[(weightName, calibType)]
              CALREGA = CALREGA_dict[(weightName, calibType)]
              CALREGB = CALREGB_dict[(weightName, calibType)]
              #Do config for each pair
              self.doConfig(coluta,MSBSecName,'SARCALEN', SARCALEN)
              self.doConfig(coluta,MSBSecName,'CALDIR', CALDIR)
              self.doConfig(coluta,MSBSecName,'CALPNDAC', CALPNDAC)
              self.doConfig(coluta,MSBSecName,'CALREGA', CALREGA)
              self.doConfig(coluta,MSBSecName,'CALREGB', CALREGB)

          #Decided to test readback success for colutas for each calibType/weightName pair
          #readbackSuccess = self.GUI.sendUpdatedConfigurations()
          #if not readbackSuccess:
          #  sys.exit("SAR CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")
 
          result = self.SARCalibDataTakingMultichannel(colutas, channels, MSBLSB)        

          BitsArrayP_dict, BitsArrayN_dict = result
          bitArrayDict[calibType] = {"P": BitsArrayP_dict, "N":BitsArrayN_dict, "val": {}}
          
        bitArrayDict["W_P"] = {}
        bitArrayDict["W_N"] = {}
        weightResultDict[weightName] = bitArrayDict
     
      print("Now we are entering the calcWeights Stage of the Program")

      print("regular print")
      print(weightResultDict)

 
      for coluta in colutas:
        for channel in channels:
          print("this is for ", coluta, " and ", channel)
          self.calcWeightsMultichannel(weightsList, weightResultDict, coluta, channel)


      for weightName in weightsList:
        for coluta in colutas:
          for channel in channels:
            totalWeight = ( weightResultDict[weightName]["W_P"][(coluta, channel)] + weightResultDict[weightName]["W_N"][(coluta, channel)] ) / 2.0 
            weightResultDict[weightName]["TOTAL"][(coluta, channel)] = totalWeight
            print("Successs!")
            self.sarWeights[weightName][(coluta, channel)] = weightResultDict[weightName]["Total"][(coluta, channel)]

      self.restoreConfig(coluta, initConfig)
      #add hardcoded values for completeness later
      return None


    #Position stuff
    def calcWeightsMultichannel(self, weightsList, weightResultDict, coluta, channel):
      list_Weighting_Second_Stage_P = [0,0,0,0,0,0,0,0,0,0,0,0,0,10,6,4,2,1,0.5,0.25]
      list_Weighting_Second_Stage_N = [0,0,0,0,0,0,0,0,0,0,0,0,0,10,6,4,2,1,0.5,0.25]
      weightPositionDict = {"W_2ND_16":12,"W_2ND_24":11,"W_2ND_32":10,"W_2ND_64":9,"W_2ND_128":8,"W_2ND_224":7,"W_1ST_128":6 ,"W_1ST_256":5,"W_1ST_384":4,"W_1ST_640":3,"W_1ST_1024":2,"W_1ST_2048":1,"W_1ST_3584":0} #Note: this is a bad solution. also note only 2nd stage weights here
      weightsList2 = ["W_2ND_16","W_2ND_24","W_2ND_32","W_2ND_64","W_2ND_128","W_2ND_224","W_1ST_128","W_1ST_256","W_1ST_384","W_1ST_640","W_1ST_1024","W_1ST_2048","W_1ST_3584"] #Note: order matters!!!! must be done from lowest to highest weights


      for weightName in weightsList2:
        self.calcWeightMultichannel(weightName, weightResultDict, list_Weighting_Second_Stage_P,list_Weighting_Second_Stage_N, coluta, channel)
        if "W_P" not in weightResultDict[weightName] or "W_N" not in weightResultDict[weightName] :
          return None
        W_P = weightResultDict[weightName]["W_P"][(coluta, channel)]
        W_N = weightResultDict[weightName]["W_N"][(coluta, channel)]
        #update weighting list
        #use position dict above to correctly update the list_Weighting_Second_Stage_P/N lists
        print(W_P)
        print(W_N)
        listPos = weightPositionDict[weightName]
        list_Weighting_Second_Stage_P[listPos] = round(W_P,2)
        list_Weighting_Second_Stage_N[listPos] = round(W_N,2)


      ###Maybe think of rewriting this to make it more readable

      weightResultDict["W_1ST_128"]["W_P"][(coluta, channel)]= weightResultDict["W_1ST_128"]["W_P"][(coluta, channel)] + weightResultDict["W_1ST_Unit"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_128"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_128"]["W_N"][(coluta, channel)] + weightResultDict["W_1ST_Unit"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_256"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_256"]["W_P"][(coluta, channel)] + weightResultDict["W_1ST_128"]["W_P"][(coluta, channel)] + weightResultDict["W_1ST_Unit"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_256"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_256"]["W_N"][(coluta, channel)] + weightResultDict["W_1ST_128"]["W_N"][(coluta, channel)] + weightResultDict["W_1ST_Unit"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_128"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_128"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_640"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_640"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_640"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_640"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_1024"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_640"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_1024"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_1024"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_640"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_1024"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_2048"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_640"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_1024"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_2048"]["W_P"][(coluta, channel)]
      weightResultDict["W_1ST_2048"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_640"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_1024"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_2048"]["W_N"][(coluta, channel)]

      weightResultDict["W_1ST_3584"]["W_P"][(coluta, channel)] = weightResultDict["W_1ST_128"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_P"][(coluta, channel)]   + weightResultDict["W_1ST_384"]["W_P"][(coluta, channel)]  \
                                              + weightResultDict["W_1ST_640"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_2048"]["W_P"][(coluta, channel)]  + weightResultDict["W_1ST_3584"]["W_P"][(coluta, channel)] 
      weightResultDict["W_1ST_3584"]["W_N"][(coluta, channel)] = weightResultDict["W_1ST_128"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_256"]["W_N"][(coluta, channel)]   + weightResultDict["W_1ST_384"]["W_N"][(coluta, channel)]  \
                                              + weightResultDict["W_1ST_640"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_2048"]["W_N"][(coluta, channel)]  + weightResultDict["W_1ST_3584"]["W_N"][(coluta, channel)] 
      return None




    def calcWeightMultichannel(self,weightName,weightResultDict,list_Weighting_Second_Stage_P,list_Weighting_Second_Stage_N, coluta, channel):

        Weighting_Second_Stage_P = np.array(list_Weighting_Second_Stage_P)
        Weighting_Second_Stage_P = np.diag(Weighting_Second_Stage_P)
        Weighting_Second_Stage_N = np.array(list_Weighting_Second_Stage_P)
        Weighting_Second_Stage_N = np.diag(Weighting_Second_Stage_N)

        calibTypeList = ["SWP","SWPB","SWN","SWNB"]
        for calibType in calibTypeList :
          if calibType not in weightResultDict[weightName] :
            print("MISSING calibType in weightResultDict")
            return None

          PArray = weightResultDict[weightName][calibType]["P"][(coluta, channel)]
          NArray = weightResultDict[weightName][calibType]["N"][(coluta, channel)]
          calibVal = PArray.dot(Weighting_Second_Stage_P)+NArray.dot(Weighting_Second_Stage_N)
          calibVal = np.sum(calibVal, axis=1)
          calibVal = np.mean(calibVal)
          weightResultDict[weightName][calibType]["val"][(coluta, channel)] = calibVal

        for calibType in calibTypeList :
          if calibType not in weightResultDict[weightName] :
            print("MISSING calibType in weightResultDict")
            return None
          if "val" not in weightResultDict[weightName][calibType] :
            print("MISSING val in weightResultDict")
            return None
        SWP  = weightResultDict[weightName]["SWP"]["val"][(coluta, channel)]
        SWPB = weightResultDict[weightName]["SWPB"]["val"][(coluta, channel)]
        SWN  = weightResultDict[weightName]["SWN"]["val"][(coluta, channel)]
        SWNB = weightResultDict[weightName]["SWNB"]["val"][(coluta, channel)]
        weightResultDict[weightName]["W_P"][(coluta, channel)] = SWP - SWPB
        weightResultDict[weightName]["W_N"][(coluta, channel)]  = SWNB -SWN
        return None      


    def SARCalibDataTakingMultichannel(self, colutas, channels, msblsb):
      BitsArrayP_dict = {}
      BitsArrayN_dict = {}      
      #Take Data ONCE for parallelization
      if len(colutas) == 1:
        self.takeData(coluta=colutas[0])
      else:
        self.takeData(trigger=True)

      try: 
        for coluta in colutas:
          for channel in channels:
            MSB_list_string = self.dataMap[coluta][msblsb[(coluta, channel)][0]]
            LSB_list_string = self.dataMap[coluta][msblsb[(coluta, channel)][1]]
            BitsArrayP_dict[(coluta, channel)], BitsArrayN_dict[(coluta, channel)] = self.sarCalibListDataToTwentyBits(MSB_list_string, LSB_list_string) 
      except:
        return None      

      return BitsArrayP_dict, BitsArrayN_dict
     





    ############################################
    ########    Old SAR Calibration      #######
    ############################################

    def printSarWeights(self):
        print("It has begun")
        if 'W_1ST_3584' not in self.sarWeights :
          return None
        scaleVal = 3584./float(self.sarWeights['W_1ST_3584'])
        print( [ round(self.sarWeights[x]*scaleVal,2) for x in self.sarWeights] )
        print( self.sarWeights )
        weightNameList = ["W_1ST_3584","W_1ST_2048","W_1ST_1024","W_1ST_640","W_1ST_384","W_1ST_256","W_1ST_128",\
                      "W_2ND_224","W_2ND_128","W_2ND_64","W_2ND_32","W_2ND_24","W_2ND_16",\
                      "W_2ND_10","W_2ND_6","W_2ND_4","W_2ND_2","W_2ND_1","W_2ND_0p5","W_2ND_0p25"]
        
        weightList = []
        for weightName in weightNameList :
          weightList.append( round(self.sarWeights[weightName]*scaleVal,2) )
        print(weightList)
        return

    def writeSarConstant(self,coluta,channel):
        self.scaleFactor = 0.97
        if channel not in self.chLabelDict :
          return None
        channelLabel = self.chLabelDict[channel][0]

        if "W_1ST_3584" not in self.sarWeights :
          return None
        chWeightResultDict = self.sarWeights

        #awkward mapping between SAR weight names and DDPU constant names
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
          valNormed = val/chWeightResultDict["W_1ST_3584"]*3584*self.scaleFactor
          val4x = round(4*valNormed)
          if val4x < 0 or val4x > 16383 :
            val4x = 0
            print("OVERFLOW, CALIB IS BAD!")
          valLength = sarCorrLengths[corr]
          #binString = format(6,'014b')
          binString = format(val4x,'0'+str(valLength)+'b')
          #print( corr, self.GUI.chips[coluta][channelLabel][corr] , len(self.GUI.chips[coluta][channelLabel][corr]) ,"\t",val4x, binString )
          #print( corr, len(self.GUI.chips[coluta][channelLabel][corr]) ,"\t",len(binString) )
          self.doConfig(coluta,channelLabel,corr,binString)
          #print( corr, self.GUI.chips[coluta][channelLabel][corr] ,"\t",val4x, binString )
          boxName = coluta + channelLabel + corr + "Box"
          self.GUI.updateBox(boxName, binString)
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess:
          sys.exit("WRITING SAR CONST FAILED: ONE OR MORE READBACKS FAILED")
        #look at current channel DDPU config
        #print(self.GUI.chips[coluta][channelLabel])
        #print(chWeightResultDict)
        pass

    def doSarCalib(self,coluta,channel):
        if coluta not in self.GUI.chips :
          print("INVALID ASIC")
          return None
        if channel not in self.chLabelDict :
          print("INVALID CH")
          return None
        MSBchannel = channel
        LSBchannel = self.chLabelDict[channel][2]
        MSBSectionName = self.chLabelDict[channel][0]
        LSBSectionName = self.chLabelDict[channel][1]

        #get initial COLUTA config here
        initConfig = self.getConfig(coluta)

        # Common Setting for Weighting Evaluation
        self.doConfig(coluta,MSBSectionName,'SHORTINPUT', '1')
        self.doConfig(coluta,MSBSectionName,'DREMDACToSAR', '0')
        self.doConfig(coluta,MSBSectionName,'OutputMode', '1')
        self.doConfig(coluta,MSBSectionName,'EXTToSAR', '0')
        self.doConfig(coluta,LSBSectionName,'DATAMUXSelect', '1')
        readbackSuccess = self.GUI.sendUpdatedConfigurations()
        if not readbackSuccess: 
          sys.exit("SAR CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")

        nRepeats = 1
        self.GUI.nSamples = 8186
        if self.feb2Version == True :
          self.GUI.nSamples = 100000          
        self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples))

        #list of weights to measure
        weightsList = ["W_2ND_16","W_2ND_24","W_2ND_32","W_2ND_64","W_2ND_128","W_2ND_224",
                       "W_1ST_Unit","W_1ST_128","W_1ST_256","W_1ST_384","W_1ST_640","W_1ST_1024","W_1ST_2048","W_1ST_3584"] #Note: order matters!!!! must be done from lowest to highest weights
        if self.testSingleWeight == True :
          weightsList = ["W_2ND_16"] #test only
        weightResultDict = {}
        for weightName in weightsList :
          print("SAR CALIB ",coluta,channel,weightName)
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
          self.sarWeights[weightName] = weightResultDict[weightName]["TOTAL"]
 
        #restore initial config here
        self.restoreConfig(coluta,initConfig)

        #add hardcoded values for completeness
        self.sarWeights["W_2ND_10"] = 10
        self.sarWeights["W_2ND_6"] = 6
        self.sarWeights["W_2ND_4"] = 4
        self.sarWeights["W_2ND_2"] = 2
        self.sarWeights["W_2ND_1"] = 1
        self.sarWeights["W_2ND_0p5"] = 0.5
        self.sarWeights["W_2ND_0p25"] = 0.25
        print("DONE TEST")
        return None

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

        if MSBchannel not in self.chLabelDict :
          print("INVALID CH")
          return None
        MSBSectionName = self.chLabelDict[MSBchannel][0]

        calibTypeList = ["SWP","SWPB","SWN","SWNB"]
        bitArrayDict = {}
        for calibType in calibTypeList :
          #do configuration
          SARCALEN  = CAL_Config.get("SARCalibrationControls", str(weightName) + "_SARCALEN_" + str(calibType) )
          CALDIR    = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALDIR_" + str(calibType) )
          CALPNDAC  = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALPNDAC_" + str(calibType) )
          CALREGA   = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGA_" + str(calibType) )
          CALREGB   = CAL_Config.get("SARCalibrationControls", str(weightName) + "_CALREGB_" + str(calibType) )

          self.doConfig(coluta,MSBSectionName,'SARCALEN', SARCALEN)
          self.doConfig(coluta,MSBSectionName,'CALDIR', CALDIR)
          self.doConfig(coluta,MSBSectionName,'CALPNDAC', CALPNDAC)
          self.doConfig(coluta,MSBSectionName,'CALREGA', CALREGA)
          self.doConfig(coluta,MSBSectionName,'CALREGB', CALREGB)
          readbackSuccess = self.GUI.sendUpdatedConfigurations()
          time.sleep(0.1)
          if not readbackSuccess:
            sys.exit("SAR CALIBRATION STOPPED: ONE OR MORE READBACKS FAILED")

          #record data
          result = self.SARCalibDataTaking(weightName + '_' + calibType ,coluta,MSBchannel ,LSBchannel)
          if result == None : 
            return None
          BitsArrayP , BitsArrayN  = result
          bitArrayDict[calibType] = {"P":BitsArrayP , "N":BitsArrayN}
        
        return bitArrayDict


    def SARCalibDataTaking(self,Evaluating_Indicator,coluta, MSBchannel,LSBchannel):
        MSB_list_string = []
        LSB_list_string = []
        #different methods for different GUIs
        if self.cv3tbVersion == True :
          self.GUI.takeSamples(6,'coluta',doDraw=False,isDAC=False,saveToDisk=False)
          coluta_binary_data = self.GUI.ODP.colutaBinaryDict
          MSB_list_string = coluta_binary_data[MSBchannel]
          LSB_list_string = coluta_binary_data[LSBchannel]
        if self.feb2Version == True :
          self.takeData(coluta)
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
