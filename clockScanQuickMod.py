import json
import numpy as np

class CLOCKSCANQUICK():
    def __init__(self,GUI):
        self.GUI = GUI
        self.filterChannel = None
        pass

    def testTakeData(self):
        chanData = self.GUI.takeTriggerData_noDataFile('sarCalib')
        self.dataMap = {}
        result = {}
        for chanNum,data in enumerate(chanData) :
          loData = data[0]
          hiData = data[1]
          if len(loData) == 0 or len(hiData) == 0 : continue
          #check for fake data in parsed data, corresponds to channel without data recorded
          if isinstance(loData[0], list) : continue
          #print(chanNum)
          if chanNum != self.filterChannel : continue
          print("\tLO",np.mean(loData),np.std(loData),len(loData),loData)
          print("\tHI",np.mean(hiData),np.std(hiData),len(hiData),hiData)
          result[chanNum] = {"loMean":round(np.mean(loData),2),"loRms":round(np.std(loData),2),"hiMean":round(np.mean(hiData),2),"hiRms":round(np.std(hiData),2) }
        return result

    def setParam_phaseSelect(self,lpgbt,eprxChnCntr,phaseSelect):
        phaseSelectStr = str('{0:04b}'.format(phaseSelect))
        self.GUI.chips[lpgbt].setConfiguration(eprxChnCntr,"XPhaseSelect",phaseSelectStr)

    def setParam_invDelay(self,coluta,invDelayNum):
        inv =  int(invDelayNum / 8)
        delay640 = int(invDelayNum % 8)
        invStr = str(inv)
        delay640Str = str('{0:03b}'.format(delay640))
        self.GUI.chips[coluta].setConfiguration('global','INV640',invStr)
        self.GUI.chips[coluta].setConfiguration('global','DELAY640',delay640Str)

    def setParam_lpgbtPhase(self,coluta,chNames,lpgbtPhase):
        lpgbtPhaseStr = str('{0:04b}'.format(lpgbtPhase))
        for ch in chNames :
          self.GUI.chips[coluta].setConfiguration(ch,"LPGBTPhase",lpgbtPhaseStr)
          boxName = coluta+ch+'LPGBTPhaseBox'
          self.GUI.updateBox(boxName,lpgbtPhaseStr)

    def setParam_cp40clkDelay(self,lpgbt,lpgbtReg,lpgbtConfig,clkDelay):
        #self.writeToLPGBT(lpgbt,lpgbtReg,clkDelay, disp = False)
        self.GUI.chips[lpgbt].setConfiguration(lpgbtConfig,lpgbtConfig,clkDelay) #

    def test_doUpdateParams(self):
        isTestGood = False
        maxTry = 3
        tryCount = 0
        while isTestGood == False and tryCount < maxTry :
          isTestGood = self.GUI.sendUpdatedConfigurations()
          tryCount = tryCount + 1
        if isTestGood == False :
          print("ERROR CONFIG FAILURE")
        return isTestGood


    def testTest(self,lpgbt,coluta,chNames,lpgbtReg_clkDelay,lpgbtConfig_cp40clkDelay,eprxChnCntr):
        #testdebug
        if True :
          self.setParam_cp40clkDelay(lpgbt,lpgbtReg_clkDelay,lpgbtConfig_cp40clkDelay,"00110000")
          self.setParam_phaseSelect(lpgbt,eprxChnCntr,6)
          self.setParam_invDelay(coluta,9)
          self.setParam_lpgbtPhase(coluta,chNames,11)
          self.test_doUpdateParams()

        #print(self.GUI.chips[lpgbt][lpgbtConfig_cp40clkDelay][lpgbtConfig_cp40clkDelay])
        print("lpgbtConfig_cp40clkDelay",self.GUI.chips[lpgbt][lpgbtConfig_cp40clkDelay][lpgbtConfig_cp40clkDelay])
        print("XPhaseSelect",self.GUI.chips[lpgbt]["eprx10chncntr"]["XPhaseSelect"])
        print('INV640',self.GUI.chips[coluta]['global']['INV640'])
        print('DELAY640',self.GUI.chips[coluta]['global']['DELAY640'])
        for ch in chNames :
          print("LPGBTPhase",self.GUI.chips[coluta][ch]["LPGBTPhase"])

        result = self.testTakeData()       
        print(result)

        return


    def testFunc(self):
        print("HELLO")
        self.filterChannel = 75 #included COLUTA19, ch7 + ch8
        coluta = 'coluta19'
        adcIndex = 1
        lpgbt = "lpgbt16"
        #chNames = ["ch1","ch2","ch3","ch4","ch5","ch6","ch7","ch8"]
        chNames = ["ch7","ch8"]
        lpgbtReg_clkDelay = 0x05d #PS0delay CP40 CLK DELAY register for COLUTA 19, lpgbt16 PS0
        lpgbtConfig_cp40clkDelay = "ps0delay" #PS0delay CLK DELAY register for COLUTA 19, lpgbt16 PS0
        eprxChnCntr = "eprx10chncntr" #Configuration of the channel 0 in group 1, setting "XPhaseSelect" for this control, ADC19 DATA7 goes to lpgbt16 EDIN10
        #eprxChnCntr = "eprx12chncntr" #setting "XPhaseSelect" for this control, ADC19 DATA8 goes to lpgbt16 EDIN12
        #clkDelays_40MHz = ["00000000","00010000","00100000","00110000","01000000"] #only writing PS0 clkDelay register, not config
        clkDelays_40MHz = ["00000000"]
        #clkDelays_40MHz = ["00000000","00010000"]

        #self.serializerTestMode(coluta, "1")
        self.GUI.nSamples = 10000 #necessary for singleADC pulse measurements
        self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples)) #set this somewhere else?
        getattr(self.GUI,'daqModeBox').setCurrentIndex(1) #ensure ADC mode
        getattr(self.GUI,'daqADCSelectBox').setCurrentIndex(adcIndex)
        self.GUI.sendUpdatedConfigurations()

        #self.testTest(lpgbt,coluta,chNames,lpgbtReg_clkDelay,lpgbtConfig_cp40clkDelay,eprxChnCntr)
        #return

        allResults = {}
        for clkDelay in clkDelays_40MHz : #clk delay 40MHz scan
          print("CP40 CLK DELAY",clkDelay)
          self.setParam_cp40clkDelay(lpgbt,lpgbtReg_clkDelay,lpgbtConfig_cp40clkDelay,clkDelay)
          #for phaseSelect in range(0,16,1): #phase select scan
          #for phaseSelect in range(6,8,1): #phase select scan
          phaseSelect = 6
          if True:
            print("PHASE SELECT",phaseSelect)
            self.setParam_phaseSelect(lpgbt,eprxChnCntr,phaseSelect)
            for invDelayNum in range(0,16,1): #inv/delay 640 scan
            #for invDelayNum in range(4,8,1): #inv/delay 640 scan
              self.setParam_invDelay(coluta,invDelayNum)
              #for lpgbtPhase in range(0,16,1): #lpgbt phase scan
              for lpgbtPhase in range(0,4,1): #lpgbt phase scan
              #lpgbtPhase = 2
              #if True :
                self.setParam_lpgbtPhase(coluta,chNames,lpgbtPhase)
                #set params into config
                isTestGood = self.test_doUpdateParams()
                if isTestGood == False :
                  print("ERROR CONFIG FAILURE")
                  return None
                #take data
                print("\n","CLK DELAY",clkDelay,"PHASE SELECT",phaseSelect,"invDelayNum",invDelayNum,"lpgbtPhase",lpgbtPhase,"\n")
                result = self.testTakeData()       
                #add result to result dict
                if clkDelay not in allResults :
                  allResults[clkDelay] = {}
                if phaseSelect not in allResults[clkDelay] :
                  allResults[clkDelay][phaseSelect] = {}
                if invDelayNum not in allResults[clkDelay][phaseSelect] :
                  allResults[clkDelay][phaseSelect][invDelayNum] = {}
                allResults[clkDelay][phaseSelect][invDelayNum][lpgbtPhase] = result
              #end lpgbt phase loop
            #end invdelay loop
          #end phaseSelect looop
        #end clkDelays_40MHz loop
        
        #dump results
        print( allResults )
        with open("testClockScan.json", 'w') as fp:
          json.dump(allResults, fp, sort_keys=True, indent=4)
        return None
