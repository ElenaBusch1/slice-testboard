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
        self.GUI.awgAmplitude = pulseAmp
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
        self.GUI.nSamples = 100000       
        self.GUI.nSamplesBox.setPlainText(str(self.GUI.nSamples)) #set this somewhere else?
        return None

    def doPulseRun(self):
        if self.awgChan != "1" and self.awgChan != "2": #Specific to LeCroy, should generalize
          print("Standard Pulse Data, must specify source channel, DONE")
          return
        print("Pulse Data Start")

        #set required metadata
        self.measType = "pulse"
        self.measStep = 0
        self.updateGuiMetadata()

        #setup required settings for pulser data taking
        self.setCommonGuiSettings()

        #initialize function generator for pulse output
        if self.doAwgControl :
          self.initializeAwg()

        #loop through amps, take data
        #standardAmps = ['0.1','1.0'] #debug amp list
        standardAmps = ['0.005','0.01','0.015','0.020','0.025','0.03','0.035','0.04','0.045','0.05','0.06','0.08','0.1','0.2','0.4','0.6','0.8','1.0','2.0','4.0','6.0']
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
