import time
import math
import instrumentControlMod

class STANDARDRUNS(object):
    def __init__(self,GUI):
        self.GUI = GUI #just pass GUI object to access configuration and data-taking methods....
        #initialize parameters for data-taking
        self.attVal = 0
        self.pulseAmp = 0.
        self.freq = 0.
        self.measType = "default"
        self.measChan = "channel79"
        self.testNum = 0
        self.measStep = 0
        self.awgChan = "1" #default?
        self.doAwgControl = True
        self.updateGuiMetadata()

        instrumentControlMod.initializeInstrumentation(self.GUI)
        if self.GUI.function_generator == None :
          self.doAwgControl = False

    def test(self):
        return None
     
    #update metadata related to standard data runs in GUI
    def updateGuiMetadata(self):
        self.GUI.att_val = self.attVal #define here for now, should go in tab
        self.GUI.awgAmplitude = self.pulseAmp #define here for now, should go in tab
        self.GUI.awgFreq = self.freq #define here for now, should go in tab
        self.GUI.runType = self.measType
        self.GUI.measChan = self.measChan
        self.GUI.testNum = self.testNum
        self.GUI.measStep = self.measStep
        return None

    #interface to GUI initialization
    def initializeAwg(self):
        if self.doAwgControl ==False :
          return None
        if self.measType == "pulse" :
          self.GUI.function_generator.applyPhysicsPulse()     
        return None

    #reset AWG
    def resetAwg(self):
        #self.function_generator.device.write("*RST")
        return None

    #function to interface with GUI pulse control
    def setPulserAmplitude(self,pulseAmp):
        self.pulseAmp = pulseAmp
        if self.doAwgControl == True :
          self.GUI.pulse_amplitudeBox.setPlainText(str(self.pulseAmp)) #update GUI test for reference
          #self.function_generator.applyPhysicsPulse() #reinitializes everything
          self.GUI.function_generator.device.write("SOURce" + str(self.awgChan) + ":VOLTage:HIGH 0") #correct
          self.GUI.function_generator.device.write("SOURce" + str(self.awgChan) + ":VOLTage:LOW " + str(-1*float(self.pulseAmp))) #correct

        return None

    #interface to GUI data-taking controls
    def takeData(self):
        self.GUI.takeTriggerData(self.measType)
        return None

    #interface to GUI settings
    def setCommonGuiSettings(self):
        self.GUI.nSamples = 3000000 #necessary for singleADC pulse measurements
        self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples)) #set this somewhere else?
        getattr(self.GUI,'daqModeBox').setCurrentIndex(1) #ensure ADC mode
        return None

    #interface to GUI
    def getChId(self):
        chToColutaDict = {"channel048":("COLUTA13",7),"channel049":("COLUTA13",7),"channel050":("COLUTA13",7),"channel051":("COLUTA13",7),\
                          "channel052":("COLUTA14",6),"channel053":("COLUTA14",6),"channel054":("COLUTA14",6),"channel055":("COLUTA14",6),\
                          "channel056":("COLUTA15",5),"channel057":("COLUTA15",5),"channel058":("COLUTA15",5),"channel059":("COLUTA15",5),\
                          "channel060":("COLUTA16",4),"channel061":("COLUTA16",4),"channel062":("COLUTA16",4),"channel063":("COLUTA16",4),\
                          "channel064":("COLUTA17",3),"channel065":("COLUTA17",3),"channel066":("COLUTA17",3),"channel067":("COLUTA17",3),\
                          "channel068":("COLUTA18",2),"channel069":("COLUTA18",2),"channel070":("COLUTA18",2),"channel071":("COLUTA18",2),\
                          "channel072":("COLUTA19",1),"channel073":("COLUTA19",1),"channel074":("COLUTA19",1),"channel075":("COLUTA19",1),\
                          "channel076":("COLUTA20",0),"channel077":("COLUTA20",0),"channel078":("COLUTA20",0),"channel079":("COLUTA20",0)}
        chBox = getattr(self.GUI, 'stdRunsChSelectBox')
        chId = None
        try:
            chId = chBox.currentText()
        except:
            print("Invalid channelId")
        if chId not in chToColutaDict :
            print("Invalid channelId")
        self.measChan = chId
        adcIndex = chToColutaDict[chId][1]
        #getattr(self.GUI,'daqModeBox').setCurrentIndex(1) #ensure ADC mode
        getattr(self.GUI,'daqADCSelectBox').setCurrentIndex(adcIndex)
        return None

    def doPulseRun(self):
        if self.awgChan != "1" and self.awgChan != "2": #Specific to LeCroy, should generalize
          print("Standard Pulse Data, must specify source channel, DONE")
          return
        print("Pulse Data Start")

        #get channel of interest info from GUI
        self.getChId()

        #setup required settings for pulser data taking
        self.setCommonGuiSettings()

        #set required metadata
        self.measType = "pulse"
        self.measStep = 0
        self.updateGuiMetadata()

        #initialize function generator for pulse output
        if self.doAwgControl :
          self.initializeAwg()

        #loop through amps, take data
        #standardAmps = ['0.1','1.0'] #debug amp list
        #standardAmps = ['0.005','0.01','0.015','0.020','0.025','0.03','0.035','0.04','0.045','0.05','0.06','0.08','0.1','0.2','0.4','0.6','0.8','1.0','2.0','3.0','4.0','5.0','6.0']
        standardAmps = ['0.01', '0.01125', '0.0125', '0.015', '0.02', '0.025', '0.05', '0.1', '0.15', '0.2', '0.25', '0.5', '0.75', '1.0', '1.25', '1.5', '1.75', '2.0', '2.25', '2.5'] #250Ohm case
        for stepNum,amp in enumerate(standardAmps):
            print(f'Starting pulse amplitude {amp} measurements')
            self.measStep = stepNum
            self.setPulserAmplitude(amp)
            #update metadata for measurement
            self.updateGuiMetadata()
            #take specified number of readouts per pulser setting, typically 1 for FELIX readout
            numReadouts = 1
            for num in range(0,numReadouts,1):
                if int(num) % 10 == 0: print("\tReadout #",num)
                self.takeData()
            #done readout loop
        #done amp loop

        #DONE, turn off pulser
        self.setPulserAmplitude('0.0')
        print("Pulse Data Done")
        return None

    #END CLASS
