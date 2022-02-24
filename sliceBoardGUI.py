from PyQt5 import uic, QtWidgets
import os
import sys
import time
import configparser
import numpy as np
import json
import chipConfiguration as CC
import sliceMod
import dataParser
import clockMod
import serialMod
import powerMod
import parseDataMod
import instrumentControlMod
import serializerValidation
import itertools
import status
import subprocess
import threading
from functools import partial
import configureLpGBT1213
from collections import OrderedDict, defaultdict
from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from flxMod import ecReadLpGBT as ecReadFromLpGBT
from flxMod import icWriteToLpGBT, ecWriteToLpGBT
from flxMod import takeManagerData
from monitoring import MPLCanvas
from datetime import datetime
from tests import lpgbt_14_test
from standardRunsModule import STANDARDRUNS
from sarCalibModule import SARCALIBMODULE
from calibModule import CALIBMODULE

qtCreatorFile = os.path.join(os.path.abspath("."), "sliceboard.ui")
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

class sliceBoardGUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, qApp, pArgs):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # General GUI options and signals
        self.pArgs = pArgs
        self.qApp = qApp
        #self.pOptions = pOptions
        self.setupUi(self)

        # Used to find serial port
        self.description = 'TESTBOARDAB'

        # Port and serial dummy values
        self.port36, self.port45 = "Placeholder A", "Placeholder B"
        self.serial36, self.serial45 = None, None

        # PySerial connection parameters
        self.baudrate = 1e6
        self.parity = 'N'
        self.stopbits = 1
        self.bytesize = 8
        self.timeout = 2
        
        # Error configuration Box items
        self.failedConfigurations = []
        
        # Some version-dependent parameters/values

        #self.nSamples = 1000000  # default number of samples to parse from standard readout
        self.nSamples = 1000  # default number of samples to parse from standard readout
        self.discarded = 0  # first N samples of readout are discarded by software (MSB end)
        self.dataWords = 32  # number of bytes for each data FPGA coutner increment
        self.controlWords = 8 # number of bytes for each control FPGA counter increment

        self.i2cCmdFreq = 2
        self.i2cConfigReg = 0x0

        # Readback configs as they are writen
        self.READBACK = False

        self.getMetadataFromJSON()
        self.opened = True

	# Data taking parameters
        self.att_val = '-99'
        self.awg_amp = '-99'
        self.awg_freq = '-99'
        self.testNum = '-99'
        self.measStep = '-99'
        self.daqMode = 'trigger'
        self.daqADCSelect = '7'
        self.singleADCMode_ADC = 'trigger'
        self.measChan = "default"
        self.LAUROCmode = '-99'

        # Default attributes for hdf5 output, overwritten by instrument control
        self.runType = 'sine'
        self.sineFrequency = '1.00'
        self.awgAmplitude = '0.50'
        self.awgFreq = 1200 # Sampling freq of external AWG
        self.pulseLength = 64 # Pulse length in bunch crossings
 
        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        self.status36 = status.Status(self, "36")
        self.status45 = status.Status(self, "45")

        # Instrument control
        #self.IPaddress = self.ipAddressBox.toPlainText()
        #self.IC = instrumentControlMod.InstrumentControl(self,'./config/instrumentConfig.cfg')
        #self.function_generator = getattr(self.IC,'function_generator')
        self.function_generator = None

        # Instance of dataParser class
        dataParserConfig = "./config/dataConfig.cfg"
        self.ODP = dataParser.dataParser(self, dataParserConfig)

        # dict that will be filled with settings, like self.chips[chip][section][setting]
        self.chips = {}
        self.powerSettings = {}
        self.chipsConfig = os.path.join(os.path.abspath("."), "config", "chips.cfg")
        self.powerConfig = os.path.join(os.path.abspath("."), "config", "power.cfg")
        self.voltageSettings = {}
        self.temperatureSettings = {}

        # Fill internal dictionaries with configurations from .cfg files
        self.setupConfigurations()
        self.configResults = {} #config status dict

        # Establish link between GUI buttons and internal configuration dictionaries
        self.connectButtons()
        self.connectPowerButtons()
        self.connectCopyButtons()

        #self.test2Button.clicked.connect(lambda: powerMod.vrefTest(self))
        #self.test3Button.clicked.connect(lambda: parseDataMod.main(self, "lauroc-1.dat"))
        self.test2Button.clicked.connect(self.testFunc)
        self.test3Button.clicked.connect(self.testFunc2)
        #self.test3Button.clicked.connect(self.doReset)
   
        # instrument buttons
        self.initializeInstrumentButton.clicked.connect(lambda:instrumentControlMod.initializeInstrumentation(self))

        # Data buttons
        self.takePedestalDataButton.clicked.connect(lambda: self.takeTriggerData("pedestal"))
        self.takeSineDataButton.clicked.connect(lambda: self.takeTriggerData("sine"))
        self.takePulseDataButton.clicked.connect(lambda: self.takeTriggerData("pulse"))
        self.incrementRunNumberButton.clicked.connect(self.incrementRunNumber)

        #self.clockScanButton.clicked.connect(lambda: clockMod.scanClocks(self, self.allCOLUTAs))
        self.serializerValidationButton.clicked.connect(lambda: serializerValidation.validateData(self, self.allCOLUTAs))
        self.clockScanButton.clicked.connect(lambda: clockMod.scanClocks(self, self.getColutasClockScan()))
        self.selectAllColutaClockScanButton.clicked.connect(self.selectAllColutas)
        self.dcdcConverterButton.clicked.connect(powerMod.enableDCDCConverter)
        self.lpgbt12ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt12"))
        self.lpgbt13ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt13"))

        self.lpgbtI2CWriteButton.clicked.connect(self.sendLPGBTRegisters)
        self.lpgbtI2CReadButton.clicked.connect(self.readLPBGTRegisters)

        #self.configureClocksButton.clicked.connect(self.configure_clocks_test)
        #self.configurelpgbt12icButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.lpgbt11ConfigureButton.clicked.connect(self.i2cDataLpGBT)
        self.configureAllButton.clicked.connect(self.configureAll)
        self.coluta16ConfigureButton.clicked.connect(lambda: self.sendFullCOLUTAConfig("box"))
        self.lpgbtConfigureButton.clicked.connect(self.sendFullLPGBTConfigs)
        self.laurocControlConfigureButton.clicked.connect(lambda: self.sendFullLAUROCConfigs("box"))
        self.sendUpdatedConfigurationsButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.laurocConfigsButton.clicked.connect(self.collectLaurocConfigs)
        #self.dataLpGBTConfigsButton.clicked.connect(self.collectDataLpgbtConfigs)
        #self.controlLpGBTConfigsButton.clicked.connect(self.collectControlLpgbtConfigs)
        #self.colutaConfigsButton.clicked.connect(self.collectColutaConfigs)

        #Configuration Buttons
        self.readTemperatureButton.clicked.connect(lambda: powerMod.checkAllTemps(self))
        self.readVoltageButton.clicked.connect(lambda: powerMod.checkAllVoltages(self))
        self.selectAllVoltagesButton.clicked.connect(lambda: powerMod.selectAllVoltages(self, '1'))
        self.selectAllTemperaturesButton.clicked.connect(lambda: powerMod.selectAllTemps(self, '1'))
        self.unselectAllVoltagesButton.clicked.connect(lambda: powerMod.selectAllVoltages(self, '0'))
        self.unselectAllTemperaturesButton.clicked.connect(lambda: powerMod.selectAllTemps(self, '0'))
        self.calculateVREFButton.clicked.connect(lambda: powerMod.vrefTest(self))
        self.scanVREFTUNEButton.clicked.connect(lambda: powerMod.vrefCalibrate(self))
        self.readbackConfigCheckBox.stateChanged.connect(self.updateReadback)
        #self.configureControlLpGBTButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.laurocConfigureButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.powerConfigureButton.clicked.connect(self.sendPowerUpdates)

        copyConfig = lambda w,x,y,z : lambda : self.copyConfigurations(w,sourceSectionName=x,targetChipNames=y,targetSectionNames=z)
        allDREChannels = ["ch1", "ch2", "ch3", "ch4"]
        allMDACChannels = ["ch5", "ch6", "ch7", "ch8"]
        allDataLpGBTs = ["lpgbt9", "lpgbt10", "lpgbt11", "lpgbt14", "lpgbt15", "lpgbt16"]
        allControlLpGBTs = ["lpgbt12", "lpgbt13"]

    
        # Plotting
        #self.takeSamplesButton.clicked.connect(lambda: self.takeSamples())
        self.nSamplesBox.document().setPlainText(str(self.nSamples))
        self.AttValBox.document().setPlainText(str(self.att_val))
        self.nSamplesBox.textChanged.connect(self.updateNSamples)
        #self.dataDisplay = MPLCanvas(self.dataDisplayWidget,x=np.arange(2),style='r.',
        #                                        ylim=[0,65536],ylabel='ADC Counts')
        #self.dataGridLayout.addWidget(self.dataDisplay,0,0)
        #self.displayGridLayout.addWidget(self.dataDisplay,0,0)

        #Standard Runs
        self.stdRuns = STANDARDRUNS(self)
        self.stdRunsPulseDataButton.clicked.connect(self.stdRuns.doPulseRun)
        self.stdRun32BitPedestalDataButton.clicked.connect(self.stdRuns.do32BitModePedestalRun)
        self.stdRun32BitSerializerDataButton.clicked.connect(lambda: self.stdRuns.get32BitModeSerializerData(even=True, Odd=False))

        ## Calibration runs
        self.sarMdacCal = SARCALIBMODULE(self)
        self.calibMod = CALIBMODULE()
        self.stdRunsCalibAllButton.clicked.connect(self.sarMdacCal.runFullCalibInFeb2Gui)
        self.stdRunsLoadCalibButton.clicked.connect(self.sarMdacCal.getFullCalibInFeb2Gui)

        ## SAR Calibration
        self.stdRunsSarCalibButton.clicked.connect(self.sarMdacCal.runSarCalibInFeb2Gui)
        self.stdRunsSarCalibAllButton.clicked.connect(lambda: self.sarMdacCal.runSarCalibInFeb2Gui(runAll=True))

        ## MDAC Calibration
        self.stdRunsMdacCalibButton.clicked.connect(self.sarMdacCal.runMdacCalibInFeb2Gui)
        self.stdRunsMdacCalibAllButton.clicked.connect(lambda: self.sarMdacCal.runMdacCalibInFeb2Gui(runAll=True))

        self.isConnected = True
        #self.startup()
        #self.lpgbt_i2c_read()
        # self.sendConfigurationsFromLpGBT()
        self.runNumberString = str(self.runNumber)
        self.setWindowTitle("Run Number: {} ".format(self.runNumberString))

        self.runNumberString = str(self.runNumber)
        self.setWindowTitle("Run Number: {} ".format(self.runNumberString)) 


    def testFunc(self):
        #self.set_DCDC(dcdcName="PA_A",onOff="off")
        #self.set_DCDC(dcdcName="PA_B",onOff="off")
        #self.set_DCDC(dcdcName="ADC_A",onOff="off")
        #self.set_DCDC(dcdcName="ADC_B",onOff="off")
        #self.set_DCDC(dcdcName="LPGBT_A",onOff="off")
        #self.set_DCDC(dcdcName="LPGBT_B",onOff="off")

        #self.function_generator.sendFakeStart()
        #return
        if True :
          print("I2C ERROR TEST")
          print("LAUROC13")
          self.readFromLPGBT("lpgbt9", 0x19f, 1, disp=True)
          print("LAUROC14")
          self.readFromLPGBT("lpgbt9", 0x1a0, 1, disp=True)
          print("LAUROC15")
          self.readFromLPGBT("lpgbt10", 0x19f, 1, disp=True)
          print("LAUROC16")
          self.readFromLPGBT("lpgbt11", 0x19f, 1, disp=True)
          print("LAUROC17")
          self.readFromLPGBT("lpgbt14", 0x19f, 1, disp=True)
          print("LAUROC18")
          self.readFromLPGBT("lpgbt15", 0x19f, 1, disp=True)
          print("LAUROC19")
          self.readFromLPGBT("lpgbt15", 0x1a0, 1, disp=True)
          print("LAUROC20")
          self.readFromLPGBT("lpgbt16", 0x19f, 1, disp=True)
          return

        if False :
          self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="lauroc")
          self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="lauroc")
        
        if True  :
          #self.set_DCDC(dcdcName="LPGBT_B",onOff="on")
          self.colutaCP40MHzDelayTest(stopLaurocCP40=True)
          #self.laurocCP40MHzPhaseTest()
          return

        if False :
          #turn on reset before modifying COLUTA clock
          testChip = "coluta17"
          boardSide = "B"
          delVal = 0x00

          laurocs = ["lauroc13","lauroc14","lauroc15","lauroc16","lauroc17","lauroc18","lauroc19","lauroc20"]
          for lauroc in laurocs:
            self.chipCP40Control(chip=lauroc,onOff="off")
          self.set_RSTB(RST_AB=boardSide,setStartStop="resetStart",chipType="all")
          self.setCP40MHzDelay(chip=testChip,useFineTune=False,delVal=delVal)
          #renable chip clock, turn off reset
          #self.chipCP40Control(chip=coluta,onOff="on")
          self.set_RSTB(RST_AB=boardSide,setStartStop="resetStop",chipType="coluta")

          #time.sleep(1)
          #readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=False)
          #print("readbackSuccess",readbackSuccess)
          
          while True :
            #time.sleep(1)
            readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=False)
            print("readbackSuccess",readbackSuccess)
            time.sleep(1)

          return None

        if False :
          #while True :
          self.setAllCP40MHz(onOff="off") #turn off all CP40 clocks

          self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
          self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
          time.sleep(0.5)
          self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
          self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")
          time.sleep(0.5)

          input("Enter to start lpGBT write")

          self.singleI2CWriteToChip(chip="lpgbt9",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="lpgbt16",data=0x15,disp=True)
          #self.singleI2CWriteToChip(chip="lauroc20_l15m2",data=0x15,disp=True)
          return None

        if False :
        #while True :
          testChip = getattr(self, 'colutaConfigureBox').currentText()
          #testChip = "coluta17"
          #self.singleI2CWriteToChip(chip="lauroc17_l15m2",data=0x15,disp=True)
          self.i2cCmdFreq = 2
          #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
          self.i2cConfigReg = 0x0
          readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=True)
          #readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta=testChip, channel="ch8", READBACK = True, writeVal= 0x1, disp=True)
          self.i2cConfigReg = 0x0 #default
          print("readbackSuccess",readbackSuccess)
          #time.sleep(1)
          return None

        if True :
        #while True :
          #testChip = getattr(self, 'laurocConfigureBox').currentText()
          #testChip = "lauroc19"
          testChip = getattr(self, 'laurocConfigureBox').currentText()
          #testChip_mod = testChip + "_l15m2"
          testChip_mod = testChip
          #self.setCP40MHzInvert(testChip,invVal=0x0,freq=0x1)
          #testChip = getattr(self, 'colutaConfigureBox').currentText()

          #self.setAllCP40MHz(onOff="off") #turn off all CP40 clocks
          #self.chipCP40Control(chip=testChip,onOff="on")

          #self.set_DCDC(dcdcName="ADC_A",onOff="off")
          #self.set_DCDC(dcdcName="ADC_B",onOff="off")
          #self.set_DCDC(dcdcName="PA_A",onOff="off")
          #self.set_DCDC(dcdcName="PA_B",onOff="off")
          #self.set_DCDC(dcdcName="PA_A",onOff="on")
          #self.set_DCDC(dcdcName="PA_B",onOff="on")

          self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
          #self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
          time.sleep(0.5)
          self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="lauroc")
          #self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="lauroc")
          time.sleep(0.5)

          print("START WRITE")
          #self.singleI2CWriteToChip(chip="lauroc17_l15m2",data=0x15,disp=True)
          #readbackSuccess = self.writeToLAUROC(testChip, 0x0, 0x1)
          self.i2cCmdFreq = 2
          #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
          self.i2cConfigReg = 0x00
          readbackSuccess = self.singleI2CWriteToChip(chip=testChip_mod,data=0x80,disp=True,doReadback=True)
          #readbackSuccess = self.singleI2CReadFromChip(chip=testChip,disp=True)
          print("readbackSuccess",readbackSuccess)
          self.i2cCmdFreq = 2 #default
          self.i2cConfigReg = 0x00 #default
          return None
          
        #return None

        if False  :
          testChip = getattr(self, 'colutaConfigureBox').currentText()
          #self.setAllCP40MHz(onOff="off") #turn off all CP40 clocks
          #self.chipCP40Control(chip=testChip,onOff="on")
         
          #self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
          #self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
          #time.sleep(0.5)
          #self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
          #self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")        
          readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=False)
          #self.chipCP40Control(chip=testChip,onOff="on")
          #readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta=testChip, channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
          #readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=False)
          #readbackSuccess = self.writeToColuta_singleByteWrite(coluta=testChip,  channel="ch1", READBACK = True,writeVal=0x1, disp=False)
          print("readbackSuccess",readbackSuccess)

          #self.writeToCOLUTAChannel(testChip, "ch8", READBACK = True)
        #return None
        
        self.i2cCmdFreq = 2
        self.i2cConfigReg = 0x00
        #self.setupI2cBus("lauroc20")
        #while True:
        if False :
        #  self.testFunc2()
           readbackSuccess = self.writeToColuta_singleByteWrite(coluta="coluta16",  channel="ch1", READBACK = True,writeVal=0x1, disp=True)
           readbackSuccess = self.writeToColuta_singleByteWrite(coluta="coluta17",  channel="ch1", READBACK = True,writeVal=0x1, disp=True)
        #   readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta13", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta14", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta15", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta16", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta17", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta18", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta19", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta="coluta20", channel="ch8", READBACK = False, writeVal= 0x1, disp=False)
        #  self.singleI2CWriteToChip(chip="coluta13",data=0x15,disp=True)
           time.sleep(0.5)
        ##return None
        #vtrx = "vtrx6_m2"
        if False :
          print("\nALL TEST\n")
          self.i2cCmdFreq = 2
          self.i2cConfigReg = 0x00
          #self.multiI2CWriteToChip(chip="vtrx1_m0",bytes=[0x0,0x1F],disp=True)
          #self.multiI2CWriteToChip(chip="vtrx1_m1",bytes=[0x0,0x1F],disp=True)
          #self.multiI2CWriteToChip(chip="vtrx1_m2",bytes=[0x0,0x1F],disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m2",data=0x15,disp=True)
          time.sleep(1)
          #continue
          self.singleI2CWriteToChip(chip="vtrx2_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx2_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx2_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx3_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx3_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx3_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx4_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx5_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx5_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx5_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx6_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx6_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx6_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx7_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx7_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx7_m2",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx8_m0",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx8_m1",data=0x15,disp=True)
          self.singleI2CWriteToChip(chip="vtrx8_m2",data=0x15,disp=True)
          #self.singleI2CWriteToChip(chip="lauroc17_l15m2",data=0x15,disp=True)
          #self.singleI2CWriteToChip(chip="lauroc18_l15m2",data=0x15,disp=True)
          #self.singleI2CWriteToChip(chip="lauroc19_l15m2",data=0x15,disp=True)
          #self.singleI2CWriteToChip(chip="lauroc20_l15m2",data=0x15,disp=True)
          #self.multiI2CWriteToChip(chip="vtrx6",bytes=[0x0,0x1F],disp=True)
          time.sleep(1)
        #vtrxList = ["vtrx3","vtrx4","vtrx5","vtrx6"]
        #for vtrx in vtrxList :
        #  print(vtrx)
        #  for regNum in range(0,0x1D+1,1):        
        #    self.singleI2CWriteToChip(chip=vtrx,data=regNum,disp=False)
        #    readVal = self.singleI2CReadFromChip(chip=vtrx,disp=False)
        #    print("REG ADDR\t",hex(regNum),"\tVAL\t",[hex(x) for x in readVal],"\t",hex(readVal[0]))
        #  time.sleep(1)

        return None

    def turnAllOff(self):
        self.set_DCDC(dcdcName="ADC_A",onOff="off")
        self.set_DCDC(dcdcName="ADC_B",onOff="off")
        self.set_DCDC(dcdcName="PA_A",onOff="off")
        self.set_DCDC(dcdcName="PA_B",onOff="off")

    def resetAll(self):
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="coluta")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="coluta")
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="lauroc")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="lauroc")
        time.sleep(0.5)
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="coluta")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="coluta")
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="lauroc")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="lauroc")

    def testFunc2(self):
        #testChip = getattr(self, 'laurocConfigureBox').currentText()
        #readbackSuccess = self.writeToLAUROC(testChip, 0x0, 0x1)

        #self.setupI2cBus("coluta13")

        #self.setAllCP40MHz(onOff="off") #turn off all CP40 clocks
        #laurocs = ["lauroc13","lauroc14","lauroc15","lauroc16"]
        #for lauroc in laurocs:
        #  self.chipCP40Control(chip=lauroc,onOff="off")
        #colutas = ["coluta13","coluta14","coluta15","coluta16"]
        #for coluta in colutas:
        #  self.chipCP40Control(chip=coluta,onOff="on")

        #self.set_DCDC(dcdcName="LPGBT_A",onOff="off")
        #self.set_DCDC(dcdcName="LPGBT_B",onOff="off")
        #self.set_DCDC(dcdcName="ADC_A",onOff="off")
        #self.set_DCDC(dcdcName="ADC_B",onOff="off")
        #self.set_DCDC(dcdcName="PA_A",onOff="off")
        #self.set_DCDC(dcdcName="PA_B",onOff="off")

        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        time.sleep(0.5)
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")
        return None

        if False:        
          self.turnAllOff()
          input("Turn DCDC off all ADC + PA")

          self.set_DCDC(dcdcName="LPGBT_A",onOff="off")
          self.set_DCDC(dcdcName="LPGBT_B",onOff="off")
          input("Turn DCDC off all ADC + PA + LPGBT")
          print("DONE CONTROL LPGBT TEST")
          return
          #self.configureAll()

        self.turnAllOff()
        input("Reconfigure, turn DCDC off all ADC + PA")

        self.turnAllOff()
        self.set_DCDC(dcdcName="ADC_A",onOff="on")
        input("Turn ADC_A ON only")

        self.turnAllOff()
        self.set_DCDC(dcdcName="ADC_B",onOff="on")
        input("Turn ADC_B ON only")

        self.turnAllOff()
        self.set_DCDC(dcdcName="PA_A",onOff="on")
        input("Turn PA_A ON only")

        self.turnAllOff()
        self.set_DCDC(dcdcName="PA_B",onOff="on")
        input("Turn PA_B ON only")

        self.turnAllOff()
        self.set_DCDC(dcdcName="ADC_A",onOff="on")
        self.set_DCDC(dcdcName="ADC_B",onOff="on")
        self.set_DCDC(dcdcName="PA_A",onOff="on")
        self.set_DCDC(dcdcName="PA_B",onOff="on")
        input("Turn on all ADC + PA")

        self.resetAll()
        input("All Reset")

        colutas = self.allCOLUTAs
        #laurocs = self.allLAUROCs
        laurocs = ["lauroc13","lauroc14","lauroc15","lauroc16"]
        for coluta in colutas:
            self.resetAll()
            self.sendFullCOLUTAConfig(coluta)
            time.sleep(0.5)
            input("Configure only"+str(coluta))

        for lauroc in laurocs:
            self.resetAll()
            self.sendFullLAUROCConfigs(lauroc)
            time.sleep(0.5)
            input("Configure only"+str(lauroc))

        self.resetAll()
        for coluta in colutas:
            self.sendFullCOLUTAConfig(coluta)
            time.sleep(0.5)
        for lauroc in laurocs:
            self.sendFullLAUROCConfigs(lauroc)
            time.sleep(0.5)
        input("All configured")

        #time.sleep(1)
        #self.set_DCDC(dcdcName="ADC_A",onOff="on")
        #self.set_DCDC(dcdcName="ADC_B",onOff="on")
        #self.set_DCDC(dcdcName="PA_A",onOff="on")
        #self.set_DCDC(dcdcName="PA_B",onOff="on")
        #self.set_DCDC(dcdcName="LPGBT_A",onOff="on")
        #self.set_DCDC(dcdcName="LPGBT_B",onOff="on")
        #self.set_DCDC(dcdcName="ADC_A",onOff="on")
        #self.set_DCDC(dcdcName="ADC_B",onOff="on")
        print("DONE")
        return None
        #time.sleep(0.5)
        #self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        #self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="coluta")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="coluta")
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="lauroc")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="lauroc")
        time.sleep(0.5)
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="coluta")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="coluta")
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="lauroc")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="lauroc")
        #self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="coluta")
        #self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="coluta")
        #time.sleep(0.5)
        #self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="coluta")
        #self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="coluta")
       
        #self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        #self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")

        return None

    def selectAllColutas(self):
        for coluta in self.allCOLUTAs:
            name = coluta + "ClockScanCheckBox"
            box = getattr(self, name)
            box.setChecked(True)

    def getColutasClockScan(self):
        colutasForClockScan = []
        for coluta in self.allCOLUTAs:
            name = coluta + "ClockScanCheckBox"
            box = getattr(self, name)
            if box.isChecked(): colutasForClockScan.append(coluta)
        if not colutasForClockScan: return(None)
        else: return(colutasForClockScan)  

    ########################## Basic read/write control for all chips ##########################

    def writeToLPGBT(self, lpgbt, register, dataBits, disp = False):
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            readbackSuccess = self.writeToControlLPGBT(lpgbt,register,dataBits)
        elif lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            readbackSuccess = self.writeToDataLPGBT(lpgbt,register,dataBits)
        else:
            print("Bad LPGBT value in writeToLPGBT")
            return False
        if disp:
            print("Writing", lpgbt, hex(register), ":", [hex(x) for x in dataBits])
        return readbackSuccess

    def readFromLPGBT(self, lpgbt, register, nBytes, disp = False):
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            readback = self.readFromControlLPGBT(lpgbt, register, nBytes)
        elif lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            readback = self.readFromDataLPGBT(lpgbt, register, nBytes)
        else:
            print("Bad LPGBT value in readFromLPGBT")
        if disp:
            print("Reading", lpgbt, hex(register), ":", [hex(x) for x in readback])
        return readback

    def writeToControlLPGBT(self, lpgbt, register, dataBits):
        """ Writes max 4 bytes through the EC or IC channels"""
        chip = self.chips[lpgbt]
        if lpgbt[-2:] == '11' or lpgbt[-2:] == '12': 
            ICEC_CHANNEL = 0
        elif lpgbt[-2:] == '13' or lpgbt[-2:] == '14': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpGBT specified (writeToControlLpgbt)")
            sys.exit(1)
        # print(lpgbt, ICEC_CHANNEL)
        if len(dataBits) > 4:
            print("Error: trying to send more than 4 dataBits in writeToControlLPGBT")

        if lpgbt in ['lpgbt11', 'lpgbt14']:
            ecWriteToLpGBT(int(chip.i2cAddress, 2), register, dataBits, ICEC_CHANNEL=ICEC_CHANNEL)
        elif lpgbt in ['lpgbt12', 'lpgbt13']:
            writeToLpGBT(int(chip.i2cAddress, 2), register, dataBits, ICEC_CHANNEL=ICEC_CHANNEL)
        else:
            print("Invalid lpGBT specified (writeToControlLpgbt)")

        readbackSuccess = True
        readback = self.readFromControlLPGBT(lpgbt, register, len(dataBits))
        if dataBits != readback:
            print("Writing ", lpgbt, register, " failed")
            readbackSuccess = False        
        return readbackSuccess
        """
        print("DATA BITS HERE -------------------- ", dataBits)
        print("READBACK HERE --------------------- ", readback)
        """

    def readFromControlLPGBT(self, lpgbt, register, nBytes):
        """ Reads max 16 bytes through the EC or IC channels"""
        chip = self.chips[lpgbt]
        if lpgbt[-2:] == '11' or lpgbt[-2:] == '12': 
            ICEC_CHANNEL = 0
        elif lpgbt[-2:] == '13' or lpgbt[-2:] == '14': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpGBT specified (readFromControlLpgbt)")
            sys.exit(1)
        # print(lpgbt, ICEC_CHANNEL)
        if nBytes > 16:
            print("Error: trying to send more than 16 dataBits in readFromControlLPGBT")

        if lpgbt in ['lpgbt11', 'lpgbt14']:
            readback = ecReadFromLpGBT(int(chip.i2cAddress, 2), register, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
        elif lpgbt in ['lpgbt12', 'lpgbt13']:
            #print(register, nBytes)
            readback = readFromLpGBT(int(chip.i2cAddress, 2), register, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
            #print(readback)
        else:
            print("Invalid lpGBT specified (readFromControlLpgbt)")
        return readback

    def writeToDataLPGBT(self, lpgbt, register, data):
        """ Writes a maxiumum of 14 bytes to given register in data lpgbt """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lpgbt].lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(self.chips[lpgbt].i2cAddress,2)

        if self.chips[lpgbt].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[lpgbt].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToDataLpgbt)")
            return
        if (len(data)>14):
            print("Error: length of data in writeToDataLpgbt too long")
            return

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 #no pull up, low drive strength
        configRegVal = configRegVal + self.i2cConfigReg
        self.writeToControlLPGBT("lpgbt"+self.chips[lpgbt].lpgbtMaster, 0x0f7, [configRegVal]) #send I2C address value to control lpGBT
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer, , freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal  + ((len(data)+2) << 2) #multi-byte write = len(data) + 2
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)

        #print("Writing", [hex(byte) for byte in data], "to register ", hex(register))
        regH, regL = u16_to_bytes(register)

        # We will write 16 bytes to i2cM1Data at a time
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        # Write 2 byte register address, then 14 bytes of configuration
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [regL, regH, *data[:2]], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
        if len(data) > 2:
            writeToLpGBT(lpgbtI2CAddr, 0x0f9, [*data[2:6]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
        if len(data) > 6:    
            writeToLpGBT(lpgbtI2CAddr, 0x0f9, [*data[6:10]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xa], ICEC_CHANNEL=ICEC_CHANNEL)
        if len(data) > 10:
            writeToLpGBT(lpgbtI2CAddr, 0x0f9, [*data[10:]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xb], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xc], ICEC_CHANNEL=ICEC_CHANNEL)
        
        # Check to see if the i2c Bus Transaction is finished before proceeding
        #print("Writing")
        self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        readbackSuccess = True
        readback = self.readFromDataLPGBT(lpgbt, register, len(data))
        if data != readback:
            print("Writing ", lpgbt, register, " failed")
            readbackSuccess = False
        return readbackSuccess

        """
        print("DATA HERE ------------------------- ", data)
        print("READBACK HERE --------------------- ", readback)
        """

    def readFromDataLPGBT(self, lpgbt, register, nBytes):
        """ Reads nBytes back from the lpgbt, starting at the given register """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lpgbt].lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(self.chips[lpgbt].i2cAddress,2)

        if self.chips[lpgbt].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[lpgbt].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToDataLpgbt)")
            return

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 #no pull up, low drive strength
        configRegVal = configRegVal + self.i2cConfigReg
        self.writeToControlLPGBT("lpgbt"+self.chips[lpgbt].lpgbtMaster, 0x0f7, [configRegVal]) #send I2C address value to control lpGBT
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10001000 #SCL driven by CMOS buffer, multi-byte write = 2, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)

        #print("Reading register ", hex(register))
        regH, regL = u16_to_bytes(register)
        # We will write 2 bytes to the data lpGBT
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        # Write 2 byte register address
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [regL, regH, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xc], ICEC_CHANNEL=ICEC_CHANNEL)
        # We will read 14 bytes from the data lpGBT
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [0x80 + (nBytes << 2) + int(self.i2cCmdFreq), 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd,  [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL) 
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xd], ICEC_CHANNEL=ICEC_CHANNEL)
        # readFromLpGBT(lpgbtI2CAddr, 0x179, 16, ICEC_CHANNEL=ICEC_CHANNEL)
        
        # Check to see if the i2c Bus Transaction is finished before proceeding
        #print("Reading")
        self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        ReverseReadback = readFromLpGBT(lpgbtI2CAddr, 0x189 - nBytes, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
        #print("Read: ", [hex(val) for val in ReverseReadback[::-1]])
        return ReverseReadback[::-1]

    def writeToLAUROC(self, lauroc, register, data):
        """ Writes data to LAUROC one register at a time """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)
        lpgbtName = "lpgbt"+self.chips[lauroc].lpgbtMaster

        #chip I2C address info
        i2cControl = self.chips[lauroc].i2cMaster
        if i2cControl not in ["0","1","2"]:
          print("ERROR: (writeToLAUROC) control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 #no pull up, low drive strength
        configRegVal = configRegVal + self.i2cConfigReg
        self.writeToLPGBT(lpgbt=lpgbtName, register=configReg, dataBits=[configRegVal], disp = False) #send I2C address value to control lpGBT
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer, multi-byte write = NA, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)
        self.writeToLPGBT(lpgbt=lpgbtName, register=dataReg, dataBits=[i2cCtrlRegVal, 0x00, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x0], disp = False)

        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x2], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x2], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x2], disp = False)

        # Check to see if the i2c Bus Transaction is finished before proceeding
        #print("Checking Write")
        """
        outcome = self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)
        if outcome == 'reset':
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
            writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
            outcome = self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)
            if outcome == 'reset': print("Failed after reset")
        """

        readbackSuccess = True
        readback = self.readFromLAUROC(lauroc, register)
        if readback[0] != data:
            readbackSuccess = False
            #print("Writing ", lauroc, register, " failed")
        if self.READBACK:
            print("Writing", lauroc, hex(register), ":", hex(data))
            print("Reading", lauroc, hex(register), ":", hex(readback[0]))
            if readback[0] == data:
                print("Successfully readback what was written!")
            else:
                print("Readback does not agree with what was written")
        return readbackSuccess

    def readFromLAUROC(self, lauroc, register):
        """ Reads from LAUROC one register at a time """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)
        lpgbtName = "lpgbt"+self.chips[lauroc].lpgbtMaster

        #chip I2C address info
        i2cControl = self.chips[lauroc].i2cMaster
        if i2cControl not in ["0","1","2"]:
          print("ERROR: control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6,"readByte":0x163},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd,"readByte":0x178},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104,"readByte":0x18d},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]
        readByteReg = i2cBusInfo[i2cControl]["readByte"]

        #get readByteReg
        #readVal = self.readFromLPGBT(lpgbt=controlLpgbt, register=readByteReg, nBytes=1, disp = disp)        #get readByteReg
        #readVal = self.readFromLPGBT(lpgbt=controlLpgbt, register=readByteReg, nBytes=1, disp = disp)
        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x2], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x2], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=addrReg, dataBits=[int(f'0{laurocI2CAddr:04b}010',2), 0x00, 0x00, 0x00], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x3], disp = False)

        # Check to see if the i2c Bus Transaction is finished before proceeding
        #print("Checking Read")
        #self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        #readback = readFromLpGBT(lpgbtI2CAddr, 0x178, 1, ICEC_CHANNEL = ICEC_CHANNEL)
        readback = self.readFromLPGBT(lpgbt=lpgbtName, register=readByteReg, nBytes=1, disp = False)
        return readback


    def writeToCOLUTAChannel(self, coluta, channel, READBACK = False):
        """ Write full configuration for given COLUTA channel """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToCOLUTAChannel)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        dataBits = self.colutaI2CWriteControl(coluta, channel, broadcast=False)
        dataBits64 = [dataBits[64*i:64*(i+1)] for i in range(len(dataBits)//64)]

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b00100000 #SCL NOT driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)

        readbackSuccess = True
        for word in dataBits64:
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            #print("0x0f9:", [hex(x) for x in [0b00100000, 0x00, 0x00, 0x00, 0x0]])
            #print("0x0f9:", [hex(x) for x in [*dataBits8[4:][::-1], 0x8]])
            #print("0x0f9:", [hex(x) for x in [*dataBits8[:4][::-1], 0x9]])
            #print("0x0f7:", [hex(x) for x in [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe]])
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
            readback = self.readFromCOLUTAChannel(coluta, word)
            if readback[:6] != dataBits8[:6]: readbackSuccess = False
            if READBACK:
                print("Writing", [hex(x) for x in dataBits8[:6]])
                print("Reading", [hex(x) for x in readback])
                if readback[:6] == dataBits8[:6]:
                    print("Successfully readback what was written!")
                else:
                    print("Readback does not agree with what was written")     
        return readbackSuccess 

    def readFromCOLUTAChannel(self, coluta, word):
        """ Readback from region defined by word (refer to colutaI2CWriteControl for definition of word) """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (readFromCOLUTAChannel)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])        
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b00100000 #SCL NOT driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)

        readBackBits = '01' + word[-14:]
        readBackBits = readBackBits.zfill(64)
        readBackBits8 = [int(readBackBits[8*i:8*(i+1)], 2) for i in range(len(readBackBits)//8)]
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
        
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
        # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
        readback = readFromLpGBT(int(lpgbtI2CAddr, 2), 0x189-8, 6, ICEC_CHANNEL=ICEC_CHANNEL) 
        return readback

    def writeToCOLUTAGlobal(self, coluta):
        """ Write all COLUTA Global bits """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToCOLUTAGlobal)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])        
        dataBitsGlobal = self.colutaI2CWriteControl(coluta, "global")
        dataBitsGlobal64 = [dataBitsGlobal[64*i:64*(i+1)] for i in range(len(dataBitsGlobal)//64)]
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b00100000 #SCL NOT driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)
       
        counter = 1
        full_write = []
        for word in dataBitsGlobal64[::-1]:
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            for x in dataBits8:
                full_write.append(x)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
            counter += 1
            if self.READBACK:
                print("Writing Global: ", [hex(x) for x in dataBits8])

        readback = self.readFromCOLUTAGlobal(coluta)
        readbackSuccess = True
        if full_write != readback: readbackSuccess = False
        return readbackSuccess

    def readFromCOLUTAGlobal(self, coluta):
        """ Read all COLUTA global bits """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (readFromCOLUTAGlobal)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b00100000 #SCL NOT driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq)

        counter = 1
        full_readback = []
        for _ in range(2):
            addrModification = counter*8
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
            readback = readFromLpGBT(int(lpgbtI2CAddr, 2), 0x189-8, 8, ICEC_CHANNEL=ICEC_CHANNEL)
            for x in readback:
                full_readback.append(x)
            if self.READBACK:
                print("Reading Global: ", [hex(x) for x in readback])
            counter += 1   
        return full_readback

    def lpgbtReset(self, lpgbt):
        print("Resetting", lpgbt, "master")
        chip = self.chips[lpgbt]
        if lpgbt == 'lpgbt12':
            ICEC = 0
        elif lpgbt == 'lpgbt13':
            ICEC = 1
        else:
            print("Invalid lpgbtMaster specified (lpgbtReset)")
            sys.exit(1)

        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x00], ICEC_CHANNEL = ICEC)
        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x07], ICEC_CHANNEL = ICEC)
        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x00], ICEC_CHANNEL = ICEC)

    def i2cTransactionCheck(self, lpgbtI2CAddr, ICEC_CHANNEL):
        lpgbt = 'lpgbt13'
        if lpgbtI2CAddr == 114: lpgbt = 'lpgbt12' 
        i2cTransactionFinished = False
        counter = 0
        while not i2cTransactionFinished:
            bit = readFromLpGBT(lpgbtI2CAddr, 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            if bit[0] == 4:
                i2cTransactionFinished = True
                continue
            elif bit[0] == 8:
                self.lpgbtReset(lpgbt)
                print('bit:', bit[0])
                return 'reset' 
            print('bit:', bit[0])
            counter += 1
            time.sleep(0.1)
            if counter == 5:
                print("I2C Transaction Failed after 0.5s")
                break
        return 'none'

    ########################## Functions to Write/Read from GUI Interface ##########################

    def sendLPGBTRegisters(self):
        """ Sends user specified value to user specified register in user specified lpgbt
            The repeat paramters sends the same value to multiple consecutive registers """
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        chip = self.chips[lpgbt]

        registerBox = getattr(self, 'lpgbtregisterBox')
        valueBox = getattr(self, 'lpgbtvalueBox')
        repeatBox = getattr(self, 'lpgbtReadLengthBox')

        try:
            reg_addr = int(registerBox.toPlainText(),16)
        except:
            print("Invalid register address")
            return
        try:
            value = int(valueBox.toPlainText(),16)
        except:
            print("Invalid value - must be hex string")
            return
        try:
            repeat = int(repeatBox.toPlainText(),10)
        except:
            print("Repeat is 1")
            repeat = 1

        lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(chip.i2cAddress,2)

        i = 0
        while i < repeat:
            if (repeat - i) < 4:
                data =  [value for _ in range(repeat - i)]
            else:
                data = [value, value, value, value]
            self.writeToLPGBT(lpgbt, reg_addr + i, data, disp=True)
            i += len(data)

    def readLPBGTRegisters(self):
        """ Reads value from user specified register in user specified lpgbt
            The repeat paramters determines how many consecutive registers are read """
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        chip = self.chips[lpgbt]

        registerBox = getattr(self, 'lpgbtregisterBox')
        repeatBox = getattr(self, 'lpgbtReadLengthBox')

        try:
            reg_addr = int(registerBox.toPlainText(),16)
        except:
            print("Invalid register address")
            return
        try:
            repeat = int(repeatBox.toPlainText(),10)
        except:
            print("Invalid value - must be decimal")
            return

        lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(chip.i2cAddress,2)
        i=0
        while i < repeat:
            if repeat - i < 4:
                count = repeat - i
            else:
                count = 4
            readback = self.readFromLPGBT(lpgbt, reg_addr + i, count, disp=True)
            i += count          


    ########################## Functions to Send Full Configurations ##########################
    def configureAll(self):
        self.configResults = {}
        """ Configures LPGBT9-16, COLUTA13-20 and LAUROC13-20 """
        colutas = self.allCOLUTAs
        laurocs = self.allLAUROCs

        print("Configuring lpgbt12")
        self.sendFullControlLPGBTConfigs("lpgbt12")
        time.sleep(0.5)
        print("Configuring lpgbt13")
        self.sendFullControlLPGBTConfigs("lpgbt13")
        time.sleep(0.5)
        print("Configuring lpgbt14")
        self.sendFullControlLPGBTConfigs("lpgbt14")
        time.sleep(0.5)
        print("Configuring lpgbt11")
        self.sendFullControlLPGBTConfigs("lpgbt11")
        time.sleep(0.5)
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        print("Configuring lpgbt10")
        self.sendFullDataLPGBTConfigs("lpgbt10")
        time.sleep(0.5)
        print("Configuring lpgbt9")
        self.sendFullDataLPGBTConfigs("lpgbt9")
        time.sleep(0.5)
        print("Configuring lpgbt15")
        self.sendFullDataLPGBTConfigs("lpgbt15")
        time.sleep(0.5)
        print("Configuring lpgbt16")
        self.sendFullDataLPGBTConfigs("lpgbt16")
        time.sleep(0.5)
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")
 
        #if input("Configure all colutas?(y/n)\n") != 'y':
        #    print("Exiting config all")
        #    return
        for coluta in colutas:
            print("Configuring", coluta)
            self.sendFullCOLUTAConfig(coluta)
            time.sleep(0.5) 

        return

        #if input("Configure all laurocs?(y/n)\n") != 'y':
        #    print("Exiting config all")
        #    return 
        for lauroc in laurocs:
            print("Configuring", lauroc)
            self.sendFullLAUROCConfigs(lauroc)
            time.sleep(0.5)

        self.sarMdacCal.getFullCalibInFeb2Gui()

        print("Done Configuring")
        print("Configuration results")
        for chip in self.configResults :
          if self.configResults[chip] == False:
            self.failedConfigurations.append(chip)
          print(chip,"",self.configResults[chip])
        self.updateErrorConfiguration()
          

    def sendFullLPGBTConfigs(self):
        """ Directs 'Configure LpGBT' button to data or control lpgbt methods """
        lpgbt = getattr(self, 'lpgbtConfigureBox').currentText()
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            self.sendFullControlLPGBTConfigs(lpgbt)
        else:
            self.sendFullDataLPGBTConfigs(lpgbt)

    def sendFullControlLPGBTConfigs(self, lpgbt):
        """ Sends all current configurations for given control lpgbt"""

        # Collect configuration in groups of 4
        chip = self.chips[lpgbt]
        chipList = list(chip.values())
        sectionChunks = defaultdict(list)
        for iSection in range(0, len(chip), 4):
            startReg = int(chipList[iSection].address, 0)
            for i in range(4):
                try:
                    bits = int(chipList[iSection+i].bits, 2)
                except IndexError:
                    bits = 0
                sectionChunks[startReg].append(bits)

        readbackSuccess = True
        ## Set all configs once without reading back to enable readbacks
        for (register, dataBits) in sectionChunks.items():
            self.writeToControlLPGBT(lpgbt, register, dataBits)

        ## Configure again and check configurations
        for (register, dataBits) in sectionChunks.items():
            self.writeToControlLPGBT(lpgbt, register, dataBits)
            readback = self.readFromControlLPGBT(lpgbt, register, len(dataBits))
            if readback[:len(dataBits)] != dataBits: 
                readbackSuccess = False
                print("Writing", lpgbt, hex(register), ":", [hex(x) for x in dataBits])
                print("Reading", lpgbt, hex(register), ":", [hex(x) for x in readback])
                print("Readback does not agree with what was written")     
            if self.READBACK:
                print("Writing", lpgbt, hex(register), ":", [hex(x) for x in dataBits])
                print("Reading", lpgbt, hex(register), ":", [hex(x) for x in readback])
                if readback[:len(dataBits)] == dataBits:
                    print("Successfully readback what was written!")
                else:
                    print("Readback does not agree with what was written")     

        self.configResults[lpgbt] = readbackSuccess
        print("Done configuring", lpgbt, ", success =", readbackSuccess)
        self.updateErrorConfigurationList(readbackSuccess, lpgbt)



    def sendFullDataLPGBTConfigs(self, lpgbt):
        """ Sends all current configurations for given data lpgbt"""
        #print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[lpgbt].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        #Collect configuration in groups of 14 registers
        chip = self.chips[lpgbt]
        chipList = list(chip.values())
        dataBits14 = defaultdict(list)
        for iSection in range(0, len(chip), 6):
            startReg = int(chipList[iSection].address, 0)
            for i in range(6):
                try:
                    bits = int(chipList[iSection+i].bits, 2)
                except IndexError:
                    bits = 0
                dataBits14[startReg].append(bits)

        readbackSuccess = True
        for (register, dataBits) in dataBits14.items():
            self.writeToDataLPGBT(lpgbt, register, dataBits)
            readback = self.readFromDataLPGBT(lpgbt, register, len(dataBits))
            if readback[:len(dataBits)] != dataBits: readbackSuccess = False
            if self.READBACK:
                print("Writing", lpgbt, hex(register), ":", [hex(x) for x in dataBits])
                print("Reading", lpgbt, hex(register), ":", [hex(x) for x in readback])
                if readback[:6] == dataBits[0:6]:
                    print("Successfully readback what was written!")
                else:
                    print("Readback does not agree with what was written")
        self.configResults[lpgbt] = readbackSuccess
        print("Done configuring", lpgbt, ", success =", readbackSuccess)
        self.updateErrorConfigurationList(readbackSuccess, lpgbt)

    def sendFullLAUROCConfigs(self, laurocName):
        """ Sends all current configurations for given lauroc """
        if laurocName == 'box':
            lauroc = getattr(self, 'laurocConfigureBox').currentText()
        else:
            lauroc = laurocName
        print("Configuring", lauroc)
        #print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[lauroc].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        #make sure LAUROC clock is on
        #self.chipCP40Control(chip=lauroc,onOff="on")

        chip = self.chips[lauroc]
        chipList = list(chip.values())
        sectionChunks = defaultdict()
        for iSection in range(0, len(chip)):
            startReg = int(chipList[iSection].address, 0)
            try:
                bits = int(chipList[iSection].bits, 2)
            except IndexError:
                bits = 0
            sectionChunks[startReg] = bits

        readbackSuccess = True
        for iSection in range(0, len(chip)):
            startReg = int(chipList[iSection].address, 0)
            data = sectionChunks[startReg]
            self.writeToLAUROC(lauroc, startReg, data)
            readback = self.readFromLAUROC(lauroc, startReg)
            if self.READBACK:
                print("Writing", lauroc, hex(startReg), ":", hex(data))
                print("Reading", lauroc, hex(startReg), ":", hex(readback[0]))
                if readback[0] == data:
                    print("Successfully readback what was written!")
                else:
                    print("Readback does not agree with what was written")
            if readback[0] != data: 
              readbackSuccess = False
              break
        self.configResults[lauroc] = readbackSuccess
        print("Done configuring", lauroc, ", success =", readbackSuccess)
        #make sure LAUROC clock is off
        #self.chipCP40Control(chip=lauroc,onOff="off")
        self.updateErrorConfigurationList(readbackSuccess, lauroc)

    def sendFullCOLUTAConfig(self, colutaName):
        """ Configure all coluta channels and global bits """
        #colutaName = "coluta20"
        if colutaName == 'box':
            coluta = getattr(self, 'colutaConfigureBox').currentText()
        else:
            coluta = colutaName
        #print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[coluta].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        numRetry = 1

        channels = ["ch"+str(i) for i in range(1,9)]
        readbackSuccess = True
        for ch in channels:
            print("Configuring ", ch, coluta)
            readbackChSucess = False
            for num in range(0,numRetry,1):
              readbackChSucess = self.writeToCOLUTAChannel(coluta, ch, self.READBACK)
              if readbackChSucess == True : break
            readbackSuccess = readbackSuccess & readbackChSucess

        globalSuccess = False
        for num in range(0,numRetry,1):
          globalSuccess = self.writeToCOLUTAGlobal(coluta)
          if globalSuccess == True : break
        readbackSuccess = readbackSuccess & globalSuccess
        self.configResults[coluta] = readbackSuccess
        print("Done configuring", coluta, ", success =", readbackSuccess)
        self.updateErrorConfigurationList(readbackSuccess, coluta)

    def colutaI2CWriteControl(self, chipName, sectionName, broadcast=False):
        """Same as fifoAWriteControl(), except for I2C."""
        section = self.chips[chipName][sectionName]
        address = section.address # FPGA address, '0' for I2C
        if broadcast:
            if int(sectionName[-1]) <= 4:
                i2cAddress = 15<<0  #  15 = 00001111
            else:
                i2cAddress = 15<<4  # 240 = 11110000
        else:
            i2cAddress = int(address)  # Internal address, '8' for global

        controlBits = section.bits

        # Based on the I2C configurations split the data byte into chunks
        # For the global configuration bits, the subaddress are 8,16
        # For the channel configuration bits,
        # the subaddresses are 0,3,6,9,12,15,18,21,24,27,30,31
        if sectionName== 'global':
            split = 64
            subAddressList = [8*(i+1) for i in range( int( np.floor(len(controlBits)/split) ) )]
            overlapLSBIndex = 64

        elif sectionName== 'readonly__':
            return

        elif sectionName.startswith('ch'):
            split = 48
            subAddressList = [3*i for i in range( int( np.floor(len(controlBits)/split) ) )]
            subAddressList.append( int( (len(controlBits)-split)/16 ) ) # Adds the subaddress '31'
            overlapLSBIndex = 496

        else:
            self.showError('COLUTAMOD: Unknown configuration, cannot split into data chunks')
            return

        # Arrange the subaddress list MSB->LSB
        subAddressList.reverse()

        # We then need to split up control data which has more than 64 bits. We still only
        # have 64 bits to use, but 16 of these bits are then needed for sub-address, etc.
        # Therefore, we will split into chuncks of 48 bits and send N/48 I2C commands. If
        # the number of bits is not a multiple of split, we use bits from previous I2C command
        # to get 48 bits for the I2C command.
        # Create the list of the MSB indices
        #LSBBitList = [ split*i if (len(controlBits)-split*(i+1)>0) else overlapLSBIndex for i in range(len(subAddressList))]
        MSBBitList = [ len(controlBits)-split*(i+1) if (len(controlBits)-split*(i+1)>0) else 0 for i in range(len(subAddressList))] #previous commit
        MSBBitList.reverse()

        # Create the list of LSB indices
        LSBBitList = [ msb+split for msb in MSBBitList]
        #MSBBitList = [ lsb+split for lsb in LSBBitList]

        # Create the list of data bits to send
        dataBitsList = []
        for msb,lsb in zip(MSBBitList,LSBBitList):
            dataBitsList.append(controlBits[msb:lsb])
            #dataBitsList.append(controlBits[lsb:msb])

        # Then, we need to make and send i2c commands out of each these chunks
        allBits = ''
        if sectionName== 'global':
            # For global bits, sub address is the I2C address
            for dataBits,subAddress in zip(dataBitsList,subAddressList):
                allBits += dataBits

        elif sectionName.startswith('ch'):
            for dataBits,subAddress in zip(dataBitsList,subAddressList):
                subAddrStr = '{0:06b}'.format(subAddress)
                dataBits = makeI2CSubData(dataBits,'1','0',subAddrStr,f'{i2cAddress:08b}')
                allBits += dataBits

        else:
            self.showError('COLUTAMOD: Unknown configuration bits.')

        return allBits


    ########################## Functions to Set Up Configurations ##########################

    def setupConfigurations(self):
        """Sets up a Configuration object for each chip listed in self.chipsConfig"""
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.chipsConfig)

        for chip in config["Chips"]:
            cfgFile, specFile, chipType, lpgbtMaster, i2cMaster, i2cAddr = [x.strip() for x in config["Chips"][chip].split(',')]
            self.chips[chip] = CC.Configuration(self, cfgFile, specFile, chipType, lpgbtMaster, i2cMaster, i2cAddr)

        powerconfig = configparser.ConfigParser()
        powerconfig.optionxform = str
        powerconfig.read(self.powerConfig)

        for powerSetting in powerconfig["powerSettings"]:
            lpgbt, pin = [x.strip() for x in powerconfig["powerSettings"][powerSetting].split(',')]
            self.powerSettings[powerSetting] = [lpgbt, pin]
        
        for voltageSetting in powerconfig["voltageSettings"]:
            lpgbt, pin = [x.strip() for x in powerconfig["voltageSettings"][voltageSetting].split(',')]
            self.voltageSettings[voltageSetting] = [lpgbt, pin]

        for tempSetting in powerconfig["temperatureSettings"]:
            lpgbt, pin = [x.strip() for x in powerconfig["temperatureSettings"][tempSetting].split(',')]
            self.temperatureSettings[tempSetting] = [lpgbt, pin]

        self.updateGUIText()


    def updateConfigurations(self, boxName, chipName, sectionName, settingName):
        previousValue = self.chips[chipName][sectionName][settingName]
        length = len(previousValue)
        name = chipName + sectionName + settingName
        #boxName = name + "Box"
        try:
            box = getattr(self, boxName)
        except AttributeError:
            print ('AttributeError')
            return
        if isinstance(box, QtWidgets.QPlainTextEdit):
            plainText = box.toPlainText()
            try:
                decimal = int(plainText)
            except ValueError:
                decimal = 0
            binary = f"{decimal:b}".zfill(length)
            if len(binary) > length:
                print("Setting overflow! Configuration not changed.")
                try:
                    previousDecimalStr = str(int(previousValue, 2))
                    box.document().setPlainText(previousDecimalStr)
                except ValueError:
                    print("Invalid input! Cannot convert to binary.")
                return
        elif isinstance(box, QtWidgets.QComboBox):
            index = box.currentIndex()
            binary = f"{index:b}".zfill(length)
        elif isinstance(box, QtWidgets.QCheckBox):
            binary = str(int(box.isChecked()))
        else:
            binary = ""
            print(f"Could not find setting box {boxName}")
        self.chips[chipName].setConfiguration(sectionName, settingName, binary)
        print(f"Updated {chipName} {sectionName}, {settingName}: {binary}")


    def sendUpdatedConfigurations(self):
        """ Write all updated configuations for all chips """
        badLAUROCS = [lauroc for lauroc in [f'lauroc{i}' for i in range(13,21)] if lauroc not in self.allLAUROCs]
        badCOLUTAs = [coluta for coluta in [f'coluta{i}' for i in range(13,21)] if coluta not in self.allCOLUTAs]
        badChips = badCOLUTAs+badLAUROCS
        print("updating")
        success = True
        for (chipName, chipConfig) in self.chips.items():
            if chipName in badChips:
                continue
            updates = {}
            for (sectionName, section) in chipConfig.items():
                if section.updated:
                    addr = int(self.chips[chipName][sectionName].address,0)
                    data = int(self.chips[chipName][sectionName].bits,2)
                    updates[addr] = [sectionName,data]
                    print('Updating',chipName,sectionName,sep=' ')
                    section.updated = False

            if len(updates.keys()) == 0:
                print("No updates for ", chipName)
                continue

            lpgbtMaster = "lpgbt"+self.chips[chipName].lpgbtMaster
            self.lpgbtReset(lpgbtMaster) 
            if chipName in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
                dataToSend = self.sortUpdates(updates, 4)
                for (addr, data) in dataToSend.items():
                    readbackSuccess = self.writeToControlLPGBT(chipName, addr, data)
                    success = readbackSuccess and success
            elif chipName in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
                dataToSend = self.sortUpdates(updates, 14)
                for (addr, data) in dataToSend.items():
                    readbackSuccess = self.writeToDataLPGBT(chipName, addr, data)
                    success = readbackSuccess and success
            elif chipName.find('lauroc') == 0:
                #make sure LAUROC clock is on
                self.chipCP40Control(chip=chipName,onOff="on")
                for (addr, data) in updates.items():
                    readbackSuccess = self.writeToLAUROC(chipName, addr, data[1])
                    success = readbackSuccess and success
                self.chipCP40Control(chip=chipName,onOff="off")
            elif chipName.find('coluta') == 0:
                for (addr, data) in updates.items():
                    if data[0] == 'global':
                        readbackSuccess = self.writeToCOLUTAGlobal(chipName)
                        success = readbackSuccess and success
                    else:
                        readbackSuccess = self.writeToCOLUTAChannel(chipName, data[0])
                        success = readbackSuccess and success
            else:
                print('ChipName Not recognized: ', chipName)
        print("Done Updating")
        if not success: print("Readback in one or more chips failed")
        return success


    def sortUpdates(self, updates, maxConsecutive):
        #Sort into groups of maxConsecutive addresses 
        orderedUpdates = OrderedDict(sorted(updates.items(), key = lambda t:t[0]))
        addrs = orderedUpdates.keys()
        addrGroups, last = [[]], None
        for addr in addrs:
            if (last is None or abs(last - addr) == 1) and (len(addrGroups[-1]) < maxConsecutive):
                addrGroups[-1].append(addr)
            else:
                addrGroups.append([addr])
            last = addr

        dataWrites = {}
        for addrGroup in addrGroups:
            firstAddr = addrGroup[0]
            currentAddr = addrGroup[0]
            finalAddr = addrGroup[-1]
            dataToSend = []
            while currentAddr <= finalAddr:
                try:
                    dataToSend.append(orderedUpdates[currentAddr][1])
                except KeyError:
                    print("Bad key in sortUpdates")
                currentAddr += 1
            dataWrites[firstAddr] = dataToSend
        return dataWrites


    ########################## GUI Control Functions ########################## 

    def startup(self):
        """Runs the standard board startup / connection routine"""
        if self.pArgs.no_connect:
            pass
        #else:
            # Real startup routine when board is connected
            # Find the ports and store the names
            #portDict = serialMod.findPorts(self)
            # self.port36, self.port45 = portDict['AB46BJOXA'], portDict['AB470WYIA']
            #self.port45 = portDict['AB46BJOX']
            # self.port45 = portDict['AB470WYI']
            # Set up the serial connection to each port, pause, and test
            # self.serial36, self.serial45 = serialMod.setupSerials(self)
            #self.serial45 = serialMod.setupSerials(self)
            #time.sleep(0.01)
            #self.handshake()
            # Reset the status bits to zero, then reset FPGAs
            # self.status36.initializeUSB()
            # self.status36.send()
            # self.status36.sendSoftwareReset()
            #self.status45.initializeUSB()
            #self.status45.send()
            #self.status45.sendSoftwareReset()

    def updateStatusBar(self,message='Ready'):
        """Updates the status bar on the GUI frontpage"""
        self.statusBar.showMessage('Run '+str(self.runNumber).zfill(4)+' - '+messaage)

    def handshake(self):
        """Checks the serial connections. Gives green status to valid ones"""
        A, B = serialMod.checkSerials(self)
        if A:
            pass
            # self.fifo36StatusBox.setStyleSheet("background-color: rgb(0, 255, 0);")
            # self.fifo36StatusBox.setText("Connected")
        if B:
            pass
            # self.fifo45StatusBox.setStyleSheet("background-color: rgb(0, 255, 0);")
            # self.fifo45StatusBox.setText("Connected")
        if A and B:
            self.isConnected = True



    def updateGUIText(self):
        for (chipName, chipConfig) in self.chips.items():
            for (sectionName, section) in chipConfig.items():
                for (settingName, setting) in section.items():
                    name = chipName + sectionName + settingName
                    if "Fill" in name or name[-2:] == "__": continue
                    boxName = name + "Box"
                    try:
                        box = getattr(self, boxName)
                    except AttributeError:
                        continue
                    if isinstance(box, QtWidgets.QPlainTextEdit):
                        print( chipName, sectionName ,  settingName, setting )
                        decimalString = str(int(setting, 2))
                        box.document().setPlainText(decimalString)
                    elif isinstance(box, QtWidgets.QComboBox):
                        setIndex = int(setting, 2)
                        box.setCurrentIndex(setIndex)
                    elif isinstance(box, QtWidgets.QCheckBox):
                        box.setChecked(bool(int(setting)))
                    elif isinstance(box, QtWidgets.QLabel):
                        pass
                    else:
                        print(f"Could not find setting box {boxName}")

    def isLinkReady(self, port):
        status = getattr(self, "status" + port)
        maxIter = 5
        counter = 0
        bytesToString = None
        while not bytesToString and counter<maxIter:
            serialMod.flushBuffer(self, port)
            status.sendFifoAOperation(2,1,4)
            nControlBits = 8
            nControlBytes = int(nControlBits/self.controlWords)
            controlBits = serialMod.readFromChip(self,port,nControlBits)
            if not isinstance(controlBits,bool):
                controlBits = controlBits[:nControlBytes]
            else:
                controlBits = bytearray(0)
            status.send()
            bytesToString = sliceMod.byteArrayToString(controlBits)
            counter += 1
            time.sleep(0.5)
        print(bytesToString)
        if bytesToString:
            isReady = bytesToString[4]=='1'
        else:
            isReady = False
        return isReady

    def connectCopyButtons(self):
        copyConfig = lambda w,x,y,z : lambda : self.copyConfigurations(w,sourceSectionName=x,targetChipNames=y,targetSectionNames=z)
        #allLAUROCs = [f"lauroc{num}" for num in range(13, 21)]
        #allCOLUTAs = [f"coluta{num}" for num in range(13, 21)]
        allDREChannels = ["ch1", "ch2", "ch3", "ch4"]
        allMDACChannels = ["ch5", "ch6", "ch7", "ch8"]
        allDataLpGBTs = ["lpgbt9", "lpgbt10", "lpgbt11", "lpgbt14", "lpgbt15", "lpgbt16"]
        allControlLpGBTs = ["lpgbt12", "lpgbt13"]

        for i in range(13,21):
            boxName = 'COLUTA'+str(i)+'CopyMDACTo'+str(i)+'Button'
            box = getattr(self, boxName)
            box.clicked.connect(copyConfig("coluta"+str(i), "ch5", ["coluta"+str(i)], allMDACChannels))

        self.LAUROC13CopyAllButton.clicked.connect(copyConfig("lauroc13", None, self.allLAUROCs, None))

        self.COLUTA13CopyGlobalButton.clicked.connect(copyConfig("coluta13", "global", self.allCOLUTAs, ["global"]))

        self.COLUTA13CopyDRETo13Button.clicked.connect(copyConfig("coluta13", "ch1", ["coluta13"], allDREChannels))
        self.COLUTA13CopyCh1ToAllButton.clicked.connect(copyConfig("coluta13", "ch1", self.allCOLUTAs, ["ch1"]))
        self.COLUTA13CopyDREToAllButton.clicked.connect(copyConfig("coluta13", "ch1", self.allCOLUTAs, allDREChannels))

        self.COLUTA13CopyCh5ToAllButton.clicked.connect(copyConfig("coluta13", "ch5", self.allCOLUTAs, ["ch5"]))
        self.COLUTA13CopyMDACToAllButton.clicked.connect(copyConfig("coluta13", "ch5", self.allCOLUTAs, allMDACChannels))

        self.lpGBT9CopyAllButton.clicked.connect(copyConfig("lpgbt9", None, allDataLpGBTs, None))
        self.lpGBT12CopyAllButton.clicked.connect(copyConfig("lpgbt12", None, allControlLpGBTs, None))

        self.coluta13SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta13', "1"))
        self.coluta14SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta14', "1"))
        self.coluta15SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta15', "1"))
        self.coluta16SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta16', "1"))
        self.coluta17SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta17', "1"))
        self.coluta18SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta18', "1"))
        self.coluta19SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta19', "1"))
        self.coluta20SerializerTestModeOnButton.clicked.connect(lambda: self.serializerTestMode('coluta20', "1"))

        self.coluta13SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta13', "0"))
        self.coluta14SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta14', "0"))
        self.coluta15SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta15', "0"))
        self.coluta16SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta16', "0"))
        self.coluta17SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta17', "0"))
        self.coluta18SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta18', "0"))
        self.coluta19SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta19', "0"))
        self.coluta20SerializerTestModeOffButton.clicked.connect(lambda: self.serializerTestMode('coluta20', "0"))

        # Connect lauroc 25/50 ohm mode buttons
        for mode in ["25", "50"]:
            for lauroc in self.allLAUROCs:
                buttonName = lauroc+"_"+mode+"OhmModeButton"
                try:
                    button = getattr(self, buttonName)
                except AttributeError:
                    print("Bad button name", buttonName)
                    continue
                button.clicked.connect(partial(self.LAUROC_25_50_OhmMode, lauroc, mode))
                          
    def connectButtons(self):
        """Create a signal response for each configuration box"""
        for (chipName, chipConfig) in self.chips.items():
            for (sectionName, section) in chipConfig.items():
                for (settingName, setting) in section.items():
                    name = chipName + sectionName + settingName
                    if "Fill" in name or name[-2] == "__": continue
                    boxName = name + "Box"
                    try:
                        box = getattr(self, boxName)
                    except AttributeError:
                        continue
                    # Call the appropriate method for each type of input box
                    if isinstance(box, QtWidgets.QPlainTextEdit):
                        # noinspection PyUnresolvedReferences
                        box.textChanged.connect(partial(self.updateConfigurations, boxName, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QComboBox):
                        # noinspection PyUnresolvedReferences
                        box.currentIndexChanged.connect(partial(self.updateConfigurations, boxName, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QCheckBox):
                        # noinspection PyUnresolvedReferences
                        box.stateChanged.connect(partial(self.updateConfigurations, boxName, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QLabel):
                        pass
                    else:
                        print(f"Could not find setting box {boxName}")
                    #print(boxName)

    def connectPowerButtons(self):
        """Create a signal response for each power setting box"""
        #powerSettings = {'dcdc_en_pa_a': ['lpgbt12','2'], 'dcdc_en_lpgbt_b': ['lpgbt12','4'], 'dcdc_en_adc_a': ['lpgbt12','11']}
        sectionNames =  ['piodirh', 'piodirl', 'pioouth', 'piooutl', 'piodrivestrengthh', 'piodrivestrengthl']
        sectionNamesL = [name for name in sectionNames if name[-1] == 'l']
        #print(sectionNamesL)
        sectionNamesH = [name for name in sectionNames if name[-1] == 'h']
        #print(sectionNamesH)
        for powerSetting in self.powerSettings:
            name = 'power' + powerSetting
            if "Fill" in name or name[-2] == "__": continue
            boxName = name + 'Box'
            try:
                box = getattr(self, boxName)
            except AttributeError:
                continue

            chip = self.powerSettings[powerSetting][0]
            pin = self.powerSettings[powerSetting][1]
            if isinstance(box, QtWidgets.QCheckBox):
                if int(pin) < 8:
                    for sectionName in sectionNamesL:
                        settingName = sectionName[:-1] + pin
                        box.stateChanged.connect(partial(self.updateConfigurations, boxName, chip, sectionName, settingName))
                else:
                    for sectionName in sectionNamesH:
                        settingName = sectionName[:-1] + pin
                        box.stateChanged.connect(partial(self.updateConfigurations, boxName, chip, sectionName, settingName))
            else:
                print(f"Could not find setting box {boxName}")

    def initializeUSBISSModule(self):

        chip = self.chips["lpgbt13"]

        writeMessage = [0x5a, 0x01]
        configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        configureLpGBT1213.readFromUSBISS(self.i2cPort)

        writeMessage = [0x5a, 0x03]
        configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        configureLpGBT1213.readFromUSBISS(self.i2cPort)

        writeMessage = [0x5a, 0x02, 0x40, 0x01, 0x37]
        configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        configureLpGBT1213.readFromUSBISS(self.i2cPort)

        # Check for existence of device with giben i2c address
        writeMessage = [0x58, int(chip.i2cAddress, 2) << 1]
        # # writeMessage = [0x58, 0xd0]
        configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        configureLpGBT1213.readFromUSBISS(self.i2cPort)

        print("USB-ISS is initialized")

    def disableParity(self):
        print("Disabling parity")
        chip = self.chips["lpgbt12"]
        writeToLpGBT(int(chip.i2cAddress, 2), 0x03c, [0x01], ICEC_CHANNEL=0)
        #readFromLpGBT(int(chip.i2cAddress, 2), 0x03c, 1, ICEC_CHANNEL=0)


    def showError(self, message):
        """Error message method. Called by numerous dependencies."""
        errorDialog = QtWidgets.QErrorMessage(self)
        errorDialog.showMessage(message)
        errorDialog.setWindowTitle("Error")

    def takeTriggerData_noDataFile(self, measType):
        """Runs takeTriggerData script"""
        # Collect metadata
        self.runType = measType
        flxADCMapping = self.flxMapping
        self.daqMode = getattr(self,'daqModeBox').currentText()
        ADCSelect = getattr(self,'daqADCSelectBox').currentText()
        try:
            self.daqADCSelect = flxADCMapping[ADCSelect]
        except:
            print("Unknown FLX mapping for this COLUTA. \n Exiting ...")
            return
        if self.daqMode == "singleADC":
            self.singleADCMode_ADC = ADCSelect
        else:
            self.singleADCMode_ADC = 'trigger'

        # Establish output file
        # using default file
        outputDirectory = './'
        outputFile = "test.dat"
        stampedOutputFile = "test-1.dat"
        outputPath = outputDirectory+"/"+outputFile
        outputPathStamped = outputDirectory+"/"+stampedOutputFile

        if self.opened:
            # Take dummy data - first data always bad
            takeManagerData(outputDirectory, outputFile, self.daqMode, int(self.daqADCSelect))
            self.opened = False  
        takeManagerData(outputDirectory, outputFile, self.daqMode, int(self.daqADCSelect))
        #time.sleep(5) #this is unnecessary with takeManagerData

        #parseDataMod parseData only uses "adc" attribute
        attributes = {}
        attributes['adc'] = self.singleADCMode_ADC
        chanData = parseDataMod.parseData(outputPathStamped,self.daqMode, self.nSamples,attributes)

        print("Removing "+outputPathStamped)
        subprocess.call("rm "+outputPathStamped, shell=True)
        return chanData

    def takeTriggerData(self, measType):
        """Runs takeTriggerData script"""
        # Collect metadata
        self.runType = measType
        flxADCMapping = self.flxMapping
        self.daqMode = getattr(self,'daqModeBox').currentText()
        ADCSelect = getattr(self,'daqADCSelectBox').currentText()
        try:
            self.daqADCSelect = flxADCMapping[ADCSelect]
        except:
            print("Unknown FLX mapping for this COLUTA. \n Exiting ...")
            return
        if self.daqMode == "singleADC":
            self.singleADCMode_ADC = ADCSelect
        else:
            self.singleADCMode_ADC = 'trigger'

        # Establish output file
        if not os.path.exists("../Runs"):
            os.makedirs("../Runs")
        if self.opened:
            # increment run number automatically when GUI opens
            self.incrementRunNumber()
        outputDirectory = '../Runs'
        outputFile = "run"+str(self.runNumber).zfill(4)+".dat"
        stampedOutputFile = "run"+str(self.runNumber).zfill(4)+"-1.dat"
        outputPath = outputDirectory+"/"+outputFile
        outputPathStamped = outputDirectory+"/"+stampedOutputFile

        if self.opened:
            # Take dummy data - first data always bad
            takeManagerData(outputDirectory, outputFile, self.daqMode, int(self.daqADCSelect))
            self.opened = False  
        takeManagerData(outputDirectory, outputFile, self.daqMode, int(self.daqADCSelect))
        #subprocess.call("python takeTriggerData.py -o "+outputPath+" -t "+self.daqMode+" -a "+self.daqADCSelect, shell=True)
        #takeDataMod.takeData(outputPath, self.daqMode, self.daqADCSelect)
        #time.sleep(5)
        parseDataMod.main(self, outputPathStamped)
        #subprocess.call("python scripts/parseData.py -f "+outputPath+" -t "+self.daqMode+" -h "+saveHists, shell=True)        
        saveBin = self.saveBinaryCheckBox.isChecked() 
        if not saveBin:
            print("Removing "+outputPathStamped)
            subprocess.call("rm "+outputPathStamped, shell=True)
            #subprocess.call("rm test.txt")
        # subprocess.call("python ")        

    def incrementRunNumber(self):
        self.runNumber += 1
        print("Run Number", self.runNumber)
        self.runNumberString = str(self.runNumber)
        self.setWindowTitle("Run Number: {}".format(self.runNumberString))

        with open('../metadata.txt','r') as f:
            temp = json.load(f)
            temp['runNumber'] = self.runNumber

        with open('../metadata.txt','w') as f:
            json.dump(temp,f)

    def makeMetadataJSON(self):
        print("Hello! We need to collect some system information to get started.")
        runNumber = input("Enter run number: ")
        boardID = input("Enter boardID: ")
        awgType = input("Enter AWGtype: ")
        assembled = input("Is your board fully assembled (8 ADCs, 8 PA/Ss)? Enter y or n: ")
        if (assembled == 'y'):
            colutas = [f'coluta{i}' for i in range(13,21)]
            laurocs = [f'lauroc{i}' for i in range(13,21)]
        else:
            colutaNumStr = input('Please enter the indicies of COLUTAs on your board seperated by commas. Ex) 16,17,20 : ')
            laurocNumStr = input('Please enter the indicies of LAUROCs on your board seperated by commas. Ex) 16,20 : ')
            colutaNums = colutaNumStr.split(",")
            laurocNums = laurocNumStr.split(",")
            colutas = ['coluta'+num for num in colutaNums]
            laurocs = ['lauroc'+num for num in laurocNums]

        print("Thanks! Default FLX mapping information will be used. Please modify by hand if necessary.")
        metadata = {}
        metadata['runNumber'] = int(runNumber)
        metadata['boardID'] = boardID
        metadata['awgType'] = awgType
        metadata['flxMapping'] = {"COLUTA"+str(i+13):str(i) for i in range(0,8)}
        metadata["allCOLUTAs"] = colutas
        metadata["allLAUROCs"] = laurocs
        with open('../metadata.txt', 'w') as outfile:
            json.dump(metadata, outfile)

    def getMetadataFromJSON(self):
        if not os.path.exists('../metadata.txt'):
            self.makeMetadataJSON()
        with open('../metadata.txt') as json_file:
            metadata = json.load(json_file)
            self.runNumber = metadata["runNumber"]   
            self.boardID = metadata["boardID"]
            self.awgType = metadata["awgType"]
            self.flxMapping = metadata["flxMapping"]
            self.allLAUROCs = metadata["allLAUROCs"]
            self.allCOLUTAs = metadata["allCOLUTAs"]

    def fifoAReadData(self, port):
        """Requests measurement, moves data to buffer, and performs read operation"""

        # 1) Send a start measurement command to the chip
        # 2) Clear the serial buffer (MANDATORY!!!!!)
        # 3) Fill the serial buffer with data from the chip
        # 4) Read the data filled in the serial buffer
        address = 1  # LpGBT address
        status = getattr(self, "status" + port)
        status.send()  # reset the rising edge
        status.sendStartMeasurement()
        serialMod.flushBuffer(self, port)  # not sure if we need to flush buffer, D.P.
        # One analog measurement will return 16 bytes, thus ask for 2*number of samples requested
        status.sendFifoAOperation(2, int(2*(self.discarded+self.nSamples)), address=address)
        time.sleep(0.01)  # Wait for data to be filled in the USB buffer
        print("Requestion datawords:", self.dataWords, "discarded", self.discarded, "samples", self.nSamples)
        dataByteArray = serialMod.readFromChip(self, port, self.dataWords*(self.discarded+self.nSamples))
        status.send()  # reset the rising edge
        first = self.discarded * self.dataWords
        last = (self.discarded + self.nSamples) * self.dataWords
        return dataByteArray[first:last]


    def lpgbt45readBack(self):
        if not self.isConnected and not self.pArgs.no_connect:
            self.showError("Board is not connected")
            return

        dataByteArray = self.fifoAReadData("45")

        if self.pArgs.no_connect: return

        dataString = sliceMod.byteArrayToString(dataByteArray)
        dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)])
        #dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)][:100])

        dataStringChunks829 = ''
        counter = 0
        for word in [dataString[i:i+8] for i in range(0,len(dataString), 8)]:
            dataStringChunks829 += word
            dataStringChunks829 += '\n'
            # if counter%29 == 0:
            if (counter+1)%32 == 0:
                dataStringChunks829 += '\n'
            counter += 1
        
        with open("colutaOutput.txt", "w") as f:
            f.write(dataStringChunks16)
        #print(dataStringChunks16)

    def updateAtt(self):
        self.att_val = int(self.AttValBox.toPlainText())

    def updateNSamples(self):
        self.nSamples = int(self.nSamplesBox.toPlainText())
        # try:
        #     self.nSamples = int(self.nSamplesBox.toPlainText())
        #     if self.nSamples==self.dualPortBufferDepth+1:
        #         self.nSamples = 2047.5
        #     elif self.nSamples > self.dualPortBufferDepth+2:
        #         self.showError('ERROR: Exceeded maximum number of samples. Max value: 4096.')
        #         self.nSamples = 2047.5
        # except Exception:
        #     self.nSamples = 0

    def updateReadback(self):
        self.READBACK = self.readbackConfigCheckBox.isChecked()

    def copyConfigurations(self, sourceChipName, sourceSectionName = None, targetChipNames = None, targetSectionNames = None):
        """Copy configuration bits from one chip/channel to other chip(s)/channel(s)"""
        if targetChipNames is None:  # Apparently python does weird stuff if we just make the default [], so do this instead
            targetChipNames = []
        if targetSectionNames is None:
            targetSectionNames = []

        if sourceSectionName is None:
            self.copyConfigurationsNotCOLUTA(sourceChipName, targetChipNames = targetChipNames)
        else:
            self.copyConfigurationsCOLUTA(sourceChipName, sourceSectionName, targetChipNames=targetChipNames, targetSectionNames=targetSectionNames)


    def copyConfigurationsNotCOLUTA(self, sourceChipName, targetChipNames = None):
        """Copy configuration bits from one chip to other chips
           Only for chips without channels with identical sets of bits (i.e. not the COLUTAs)"""
        if targetChipNames is None:
            targetChipNames = []

        sourceChip = self.chips[sourceChipName]
        for (sourceSectionName, sourceSection) in sourceChip.items():
            for (sourceSettingName, sourceSetting) in sourceSection.items():
                for targetChipName in targetChipNames:
                    if sourceChipName == targetChipName: continue
                    targetChip = self.chips[targetChipName]
                    targetSectionName = sourceSectionName
                    targetSection = targetChip[targetSectionName]
                    targetSettingName = sourceSettingName
                    targetSetting = targetSection[targetSettingName]
                    if sourceSetting == targetSetting: continue  # Don't want to mark as updated if nothing changed
                    boxName = targetChipName + targetSectionName + targetSettingName + "Box"
                    self.updateBox(boxName, sourceSetting)


    def copyConfigurationsCOLUTA(self, sourceChipName, sourceSectionName, targetChipNames = None, targetSectionNames = None):
        """Copy configuration bits from one chip/channel to other chip(s)/channel(s)
           Only for COLUTAs since different channels have similar sets of bits"""
        if targetChipNames is None:
            targetChipNames = []
        if targetSectionNames is None:
            targetSectionNames = []
        
        print("Warning: LPGBTPhase will not be copied")
        sourceChip = self.chips[sourceChipName]
        sourceSection = sourceChip[sourceSectionName]
        for (sourceSettingName, sourceSetting) in sourceSection.items():
            for targetChipName in targetChipNames:
                targetChip = self.chips[targetChipName]
                for targetSectionName in targetSectionNames:
                    if sourceChipName == targetChipName and sourceSectionName == targetSectionName: continue
                    targetSection = targetChip[targetSectionName]
                    targetSettingName = sourceSettingName
                    targetSetting = targetSection[targetSettingName]
                    if sourceSetting == targetSetting: continue  # Don't want to mark as updated if nothing changed
                    if targetSettingName == 'LPGBTPhase': continue # Don't copy clock settings
                    boxName = targetChipName + targetSectionName + targetSettingName + "Box"
                    self.updateBox(boxName, sourceSetting)


    def updateBox(self, boxName, settingValue):
        try:
            box = getattr(self, boxName)
        except AttributeError:
            print("Attribute Error in updateBox for ", boxName)
            return
        if isinstance(box, QtWidgets.QPlainTextEdit):
            decimalString = str(sliceMod.binaryStringToDecimal(settingValue))
            box.document().setPlainText(decimalString)
        elif isinstance(box, QtWidgets.QComboBox):
            setIndex = sliceMod.binaryStringToDecimal(settingValue)
            box.setCurrentIndex(setIndex)
        elif isinstance(box, QtWidgets.QCheckBox):
            if settingValue == '1':
                box.setChecked(True)
            elif settingValue == '0':
                box.setChecked(False)
            else:
                self.showError(f'CHIPCONFIGURATION: Error updating GUI. {boxName}')
        elif isinstance(box, QtWidgets.QLabel):
            pass
        else:
            print(f'Could not find setting box {boxName}.')


    def serializerTestMode(self, colutaName, setting):
        coluta = self.chips[colutaName]
        for i in range(1,9):
            channel = coluta[f"ch{i}"]
            boxName = colutaName + f"ch{i}" + "SerializerTestModeBox"
            self.updateBox(boxName, setting)

    def LAUROC_25_50_OhmMode(self, laurocName, mode):
        ## Sets 25 Ohm mode or 50 ohm mode. See LAUROC2 data sheet, page 28
        lauroc = self.chips[laurocName]

        #25 Ohm Setting, 50 Ohm Setting
        settings = {
            "datain2sw_DC_g20": ['1', '1'],
            "datain2sw_ibo_g20": ['0','0'],
            "datain2dac_g20": [f'{63:b}'.zfill(6),f'{63:b}'.zfill(6)],
            "datain3sw_ibi_25": ['1','1'],
            "datain3sw_ibo": ['0','0'], 
            "datain3sw_R025_10mA": ['1', '0'],
            "datain3sw_R025_5mA": ['0','0'],
            "datain4cr_hg_s1": [f'{0:b}'.zfill(3),f'{0:b}'.zfill(3)],
            "datain4rc_hg_s1": [f'{9:b}'.zfill(4),f'{10:b}'.zfill(4)],
            "datain5rc_hg_s2": [f'{8:b}'.zfill(4),f'{8:b}'.zfill(4)],
            "datain5rc_lg_s2": [f'{9:b}'.zfill(4),f'{11:b}'.zfill(4)],
            "datain6cr_lg_s1": [f'{3:b}'.zfill(3),f'{0:b}'.zfill(3)],
            "datain6rc_lg_s1": [f'{9:b}'.zfill(4),f'{11:b}'.zfill(4)],
            "datain8c2": [f'{230:b}'.zfill(8),f'{79:b}'.zfill(8)],
            "datain12c2": [f'{230:b}'.zfill(8),f'{79:b}'.zfill(8)],
            "datain16c2": [f'{230:b}'.zfill(8),f'{79:b}'.zfill(8)],
            "datain20c2": [f'{230:b}'.zfill(8),f'{79:b}'.zfill(8)],
            "datain9dacb_VDC_hg": [f'{62:b}'.zfill(6),f'{62:b}'.zfill(6)],
            "datain13dacb_VDC_hg": [f'{62:b}'.zfill(6),f'{62:b}'.zfill(6)],
            "datain17dacb_VDC_hg": [f'{62:b}'.zfill(6),f'{62:b}'.zfill(6)],
            "datain21dacb_VDC_hg": [f'{62:b}'.zfill(6),f'{62:b}'.zfill(6)],
            "datain11dacb_VDC_lg": [f'{32:b}'.zfill(6),f'{32:b}'.zfill(6)], 
            "datain15dacb_VDC_lg": [f'{32:b}'.zfill(6),f'{32:b}'.zfill(6)],
            "datain19dacb_VDC_lg": [f'{32:b}'.zfill(6),f'{32:b}'.zfill(6)],
            "datain23dacb_VDC_lg": [f'{32:b}'.zfill(6),f'{32:b}'.zfill(6)],
            "datain26dacb_VDC_sum": [f'{20:b}'.zfill(6),f'{48:b}'.zfill(6)]
        }
        if mode == "25": idx = 0
        elif mode == "50": idx = 1
        for setting, values in settings.items():
            boxName =  laurocName + setting + "Box"
            self.updateBox(boxName, values[idx])

        ## cmd_gain_sum not implemented as button in GUI
        lauroc.setConfiguration("datain27", "cmd_gain_sum", '000')
        print(f"Updated {laurocName} datain27, cmd_gain_sum: 000")
        self.LAUROCmode = mode

    def updateErrorConfigurationList(self, readback, chip):
        print("performed test for", chip)
        if readback == True:
            if chip in self.failedConfigurations:
                self.failedConfigurations.remove(chip)
                self.updateErrorConfiguration()
        else:
            if chip not in self.failedConfigurations:
                self.failedConfigurations.append(chip)
                self.updateErrorConfiguration()

    def updateErrorConfiguration(self):
        #The line of code below removes any duplicate entries
        self.failedConfigurations = list(dict.fromkeys(self.failedConfigurations))
        if len(self.failedConfigurations) == 0:
            self.configurationStatus.setText("Successful Configuration")
            self.configurationStatus.setStyleSheet("background-color: lightgreen; border: 1px solid black")
        else:
            self.configurationStatus.setText(f"Unsuccessful Configuration == {self.failedConfigurations}")
            self.configurationStatus.setStyleSheet("background-color: red; border: 1px solid black")

    #Utility functions for board control

    def set_RSTB(self,RST_AB="",setStartStop="",chipType="all"):
        if RST_AB != "A" and RST_AB != "B" : return None
        if setStartStop != "resetStart" and setStartStop != "resetStop" : return None
        chipTypes = ["coluta","lauroc","vtrx","all"]
        if chipType not in chipTypes : return None
        #PA_RSTB_A : lpGBT12, GPIO pin 0, dir reg = 0x53 bit 0 , out reg = 0x55 bit 0
        #PA_RSTB_B : lpGBT13, GPIO pin 0, dir reg  = 0x53 bit 0 , out reg = 0x55 bit 0
        #ADC_RSTB_A : lpGBT12, GPIO pin 1, dir reg = 0x53 bit 1 , out reg = 0x55 bit 1
        #ADC_RSTB_B : lpGBT13, GPIO pin 1, dir reg  = 0x53 bit 1 , out reg = 0x55 bit 1
        lpgbt = "lpgbt12"
        if RST_AB == "B": lpgbt = "lpgbt13"
        #get current control reg val
        ctrlRegAddr = 0x55 #hardcoded, not using config dict here
        regReadVal = self.readFromLPGBT(lpgbt=lpgbt, register=ctrlRegAddr, nBytes=1, disp = False)
        if len(regReadVal) != 1 :
          print("ERROR in set_RSTB, could not read register 0x55")
          return None
        regReadVal = regReadVal[0]
        
        regMask = 0x00 #reset nothing
        if lpgbt == "lpgbt12" :
          #regMask = 0x03 #reset LAUROC+COLUTAs
          regMask = 0x0B #reset LAUROC+COLUTAs+VTRXs, all
          if chipType == "lauroc" : regMask = 0x01 #only reset LAUROC
          if chipType == "coluta" : regMask = 0x02 #only reset COLUTA
          if chipType == "vtrx"   : regMask = 0x08 #only reset VTRX
        if lpgbt == "lpgbt13" :
          #regMask = 0x03 #reset LAUROC+COLUTAS
          regMask = 0x23 #reset LAUROC+COLUTAs+VTRXs, all
          if chipType == "lauroc" : regMask = 0x01 #only reset LAUROC
          if chipType == "coluta" : regMask = 0x02 #only reset COLUTA
          if chipType == "vtrx"   : regMask = 0x20 #only reset VTRX

        #first set RSTB = 1, ie stop reset
        self.writeToLPGBT(lpgbt, ctrlRegAddr, [ (regReadVal | regMask) ], disp = False)
        time.sleep(0.1)        
        if setStartStop == "resetStart" :
          #set RSTB = 0, ie start reset
          self.writeToLPGBT(lpgbt, ctrlRegAddr, [ (regReadVal & ~regMask) ], disp = False)
          time.sleep(0.1)
        #print("DONE set_RSTB")
        return None

    def chipCP40Control(self,chip,onOff):
        if onOff != "on" and onOff != "off" :
          return None
        chipClockMap = { "coluta20":{"lpGBT":"lpgbt16","ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta19":{"lpGBT":"lpgbt16","ctrlReg":"ps0config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta18":{"lpGBT":"lpgbt15","ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta17":{"lpGBT":"lpgbt14","ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta16":{"lpGBT":"lpgbt11","ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta15":{"lpGBT":"lpgbt10","ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta14":{"lpGBT":"lpgbt10","ctrlReg":"ps0config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "coluta13":{"lpGBT":"lpgbt9" ,"ctrlReg":"ps2config"      ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc20":{"lpGBT":"lpgbt16","ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc19":{"lpGBT":"lpgbt15","ctrlReg":"epclk2chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc18":{"lpGBT":"lpgbt15","ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc17":{"lpGBT":"lpgbt14","ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc16":{"lpGBT":"lpgbt11","ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc15":{"lpGBT":"lpgbt10","ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc14":{"lpGBT":"lpgbt9" ,"ctrlReg":"epclk2chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lauroc13":{"lpGBT":"lpgbt9" ,"ctrlReg":"epclk0chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt9"  :{"lpGBT":"lpgbt12","ctrlReg":"epclk20chncntrh","ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt10" :{"lpGBT":"lpgbt12","ctrlReg":"epclk20chncntrh","ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt11" :{"lpGBT":"lpgbt12","ctrlReg":"epclk24chncntrh","ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt14" :{"lpGBT":"lpgbt13","ctrlReg":"epclk8chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt15" :{"lpGBT":"lpgbt13","ctrlReg":"epclk9chncntrh" ,"ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                         "lpgbt16" :{"lpGBT":"lpgbt13","ctrlReg":"epclk10chncntrh","ctrlBit":0,"bitMask":0x07,"defaultVal":0x01},\
                       }
        if chip not in chipClockMap :
          return None
        ctrlLpGBT = chipClockMap[chip]["lpGBT"]
        ctrlReg = chipClockMap[chip]["ctrlReg"]
        ctrlBit = chipClockMap[chip]["ctrlBit"]
        ctrlBitMask = chipClockMap[chip]["bitMask"]
        defaultVal = chipClockMap[chip]["defaultVal"]
        if ctrlLpGBT not in self.chips :
          return None
        if ctrlReg not in self.chips[ctrlLpGBT] :
          return None
        ctrlRegVal = self.chips[ctrlLpGBT][ctrlReg]
        ctrlRegAddr = int(self.chips[ctrlLpGBT][ctrlReg].address , 0 )
        #get current control reg val
        regReadVal = self.readFromLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, nBytes=1, disp = False)
        if len(regReadVal) != 1 :
          return None
        regReadVal = regReadVal[0]
        newRegVal = (regReadVal & (~ctrlBitMask)) #zero-out relevant control bits, turn off
        if onOff == "on" :
          newRegVal = (newRegVal | defaultVal)
        #write new val to register
        self.writeToLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, dataBits=[newRegVal], disp = False) #GPIO0 LOW OUTPUT bit0 low
        #check new value
        regReadVal = self.readFromLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, nBytes=1, disp = False)
        if len(regReadVal) != 1 :
          return None
        regReadVal = regReadVal[0]
        if regReadVal != newRegVal :
          print("ERROR: Turning",chip,"CP40MHz",onOff,"failed!")
          return None
        return None


    def colutaCP40MHzDelayTest_testColuta(self,config=None,results={}):
        if config == None :
          return None
        numTest = 100
        lpgbtNum = config["lpgbtNum"]
        delReg = config["delReg"]
        coluta = config["coluta"]
        controlLpGBT = config["controlLpGBT"]
        boardSide = config["boardSide"]
        results[coluta] = {}
        goodDelay = []

        adcSide = "ADC_" + str(boardSide)
        useFineTune = False

        #self.setAllCP40MHz(onOff="off") #turn off all CP40 clocks
        for delVal in range(0,512,16): #works for coarse or fine tuning
        #for delVal in range(0,512,1): #only works for fine tuning case
            print("TESTING",coluta,"DELAY",hex(delVal))

            #power cycle COLUTAs
            #self.set_DCDC(dcdcName=adcSide,onOff="off")
            #time.sleep(0.5)
            #self.set_DCDC(dcdcName=adcSide,onOff="on")

            #turn on reset before modifying COLUTA clock
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStart",chipType="all")
            self.lpgbtReset(controlLpGBT) #make sure I2C bus still works
            #self.chipCP40Control(chip=coluta,onOff="off")
            self.setCP40MHzDelay(chip=coluta,useFineTune=useFineTune,delVal=delVal)

            #renable chip clock, turn off reset
            #self.chipCP40Control(chip=coluta,onOff="on")
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStop",chipType="coluta")

            #test loop, try COLUTA reg write multiple times and record # successes
            testCount = 0
            failCount = 0 
            writeVal = 1
            for testNum in range(0,numTest,1):
                #readbackSuccess = self.writeToCOLUTAChannel_singleWrite(coluta=coluta, channel="ch8", READBACK = True, writeVal= writeVal, disp=False)
                readbackSuccess = self.writeToColuta_singleByteWrite(coluta=coluta, channel="ch8", READBACK = True, writeVal= writeVal, disp=False)
                testCount += 1
                if readbackSuccess == False : failCount += 1
                if writeVal == 1 : writeVal = 2
                else : writeVal = 1
                if failCount >= 1 : break
            #end test loop
            results[coluta][delVal] = [testCount,failCount,numTest]
            if failCount == 0 : goodDelay.append(delVal)
            print("\t",hex(delVal),"\t",testCount,"\t",failCount,"\t", 1 - failCount / float(testCount) )
        #end delay loop

        #print result
        print( coluta )
        for delay in results[coluta]:
            print(hex(delay),"\t",round((delay>>4)*0.78125,2),"\t",results[coluta][delay][0],"\t",results[coluta][delay][1],"\t",results[coluta][delay][0]/results[coluta][delay][2])
        #end config loop


    def setCP40MHzDelay(self,chip,useFineTune=False,delVal=0x0):
        chipClockMap = { "coluta20":{"lpGBT":"lpgbt16","ctrlReg":0x062},\
                         "coluta19":{"lpGBT":"lpgbt16","ctrlReg":0x05c},\
                         "coluta18":{"lpGBT":"lpgbt15","ctrlReg":0x062},\
                         "coluta17":{"lpGBT":"lpgbt14","ctrlReg":0x062},\
                         "coluta16":{"lpGBT":"lpgbt11","ctrlReg":0x062},\
                         "coluta15":{"lpGBT":"lpgbt10","ctrlReg":0x062},\
                         "coluta14":{"lpGBT":"lpgbt10","ctrlReg":0x05c},\
                         "coluta13":{"lpGBT":"lpgbt9" ,"ctrlReg":0x062},\
                       }
        if chip not in chipClockMap :
          print("ERROR: setCP40MHzDelay)Chip not in dict, returning")
          return False
        lpgbtNum = chipClockMap[chip]["lpGBT"]
        configReg = chipClockMap[chip]["ctrlReg"]

        #read orig config reg
        origRegVal = self.readFromLPGBT(lpgbt=lpgbtNum,register=configReg,nBytes=1, disp = False)
        if len(origRegVal) != 1 :
          print("lpGBT register read failed", lpgbtNum,configReg,origRegVal)
          return None

        #make new config reg val
        newRegVal = (origRegVal[0] & 0x3F)
        if useFineTune == True : newRegVal = newRegVal + 0x40
        if delVal >= 256 : newRegVal = newRegVal + 0x80

        #write updated config reg
        readbackSuccess = self.writeToLPGBT(lpgbt=lpgbtNum,register=configReg,dataBits=[ (newRegVal & 0xFF) ], disp = False)
        if readbackSuccess == False :
          print("lpGBT register write failed", lpgbtNum,configReg,dataBits)
          return None

        #write update delay register
        readbackSuccess = self.writeToLPGBT(lpgbt=lpgbtNum,register=configReg+1,dataBits=[ (delVal & 0xFF) ], disp = False)
        if readbackSuccess == False :
          print("lpGBT register write failed", lpgbtNum,configReg+1,dataBits)
          return None
        return None


    def colutaCP40MHzDelayTest(self,stopLaurocCP40=False):
        configList = [{"lpgbtNum":"lpgbt9" ,"delReg":0x063,"coluta":"coluta13","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      {"lpgbtNum":"lpgbt10","delReg":0x05d,"coluta":"coluta14","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      {"lpgbtNum":"lpgbt10","delReg":0x063,"coluta":"coluta15","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      {"lpgbtNum":"lpgbt11","delReg":0x063,"coluta":"coluta16","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      {"lpgbtNum":"lpgbt14","delReg":0x063,"coluta":"coluta17","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt15","delReg":0x063,"coluta":"coluta18","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt16","delReg":0x05d,"coluta":"coluta19","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt16","delReg":0x063,"coluta":"coluta20","controlLpGBT":"lpgbt13","boardSide":"B"},
        ]
        results = {}

        #first reset LAUROC+VTRx permanently while COLUTA test runs
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="coluta")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="coluta")

        #turn off LAUROC clocks 
        laurocs = ["lauroc13","lauroc14","lauroc15","lauroc16","lauroc17","lauroc18","lauroc19","lauroc20"]
        if stopLaurocCP40 == True :
          for lauroc in laurocs:
            self.chipCP40Control(chip=lauroc,onOff="off")

        for config in configList :
          self.colutaCP40MHzDelayTest_testColuta(config,results)

        #end LAUROC+VTRx reset
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")
          
        #print results
        print( results )
        for coluta in results :
          print(coluta)
          for delay in results[coluta]:
            #print(hex(delay),"\t",round((delay>>4)*0.78125,2),"\t",results[coluta][delay][0],"\t",results[coluta][delay][1])
            if len(results[coluta][delay]) > 0 :
              print(hex(delay),"\t",round((delay>>4)*0.78125,2),"\t",1-results[coluta][delay][1]/results[coluta][delay][0])
        return None

    def setCP40MHzInvert(self,chip,invVal=0x0,freq=0x1):
        chipClockMap = { "lauroc20":{"lpGBT":"lpgbt16","ctrlReg":0x06c},\
                         "lauroc19":{"lpGBT":"lpgbt15","ctrlReg":0x070},\
                         "lauroc18":{"lpGBT":"lpgbt15","ctrlReg":0x06c},\
                         "lauroc17":{"lpGBT":"lpgbt14","ctrlReg":0x06c},\
                         "lauroc16":{"lpGBT":"lpgbt11","ctrlReg":0x06c},\
                         "lauroc15":{"lpGBT":"lpgbt10","ctrlReg":0x06c},\
                         "lauroc14":{"lpGBT":"lpgbt9","ctrlReg" :0x070},\
                         "lauroc13":{"lpGBT":"lpgbt9" ,"ctrlReg":0x06c},\
                         "lauroc20_l15m2":{"lpGBT":"lpgbt16","ctrlReg":0x06c},\
                         "lauroc19_l15m2":{"lpGBT":"lpgbt15","ctrlReg":0x070},\
                         "lauroc18_l15m2":{"lpGBT":"lpgbt15","ctrlReg":0x06c},\
                         "lauroc17_l15m2":{"lpGBT":"lpgbt14","ctrlReg":0x06c},\
                       }
        if chip not in chipClockMap :
          print("ERROR: setCP40MHzDelayChip not in dict, returning")
          return False
        lpgbtNum = chipClockMap[chip]["lpGBT"]
        configReg = chipClockMap[chip]["ctrlReg"]

        #read orig config reg
        origRegVal = self.readFromLPGBT(lpgbt=lpgbtNum,register=configReg,nBytes=1, disp = False)
        if len(origRegVal) != 1 :
          print("lpGBT register read failed", lpgbtNum,configReg,origRegVal)
          return None

        #make new config reg val
        newRegVal = (origRegVal[0] & 0xBF)
        if invVal == 0x1 :
          newRegVal = newRegVal + 0x40
        #newRegVal = newRegVal + (freq & 0x7)

        #write updated config reg
        readbackSuccess = self.writeToLPGBT(lpgbt=lpgbtNum,register=configReg,dataBits=[ (newRegVal & 0xFF) ], disp = False)
        if readbackSuccess == False :
          print("lpGBT register write failed", lpgbtNum,configReg,(newRegVal & 0xFF))
          return None
        return None


    def laurocCP40MHzPhaseTest(self):
        configList = [#{"lpgbtNum":"lpgbt9" ,"phaseReg":0x06c,"lauroc":"lauroc13","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      #{"lpgbtNum":"lpgbt9" ,"phaseReg":0x070,"lauroc":"lauroc14","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      #{"lpgbtNum":"lpgbt10","phaseReg":0x06c,"lauroc":"lauroc15","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      #{"lpgbtNum":"lpgbt11","phaseReg":0x06c,"lauroc":"lauroc16","controlLpGBT":"lpgbt12","boardSide":"A"},\
                      #{"lpgbtNum":"lpgbt14","phaseReg":0x06c,"lauroc":"lauroc17","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      #{"lpgbtNum":"lpgbt15","phaseReg":0x06c,"lauroc":"lauroc18","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      #{"lpgbtNum":"lpgbt15","phaseReg":0x070,"lauroc":"lauroc19","controlLpGBT":"lpgbt13","boardSide":"B"},\
                      #{"lpgbtNum":"lpgbt16","phaseReg":0x06c,"lauroc":"lauroc20","controlLpGBT":"lpgbt13","boardSide":"B"},
                      {"lpgbtNum":"lpgbt14","phaseReg":0x06c,"lauroc":"lauroc17_l15m2","controlLpGBT":"lpgbt15","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt15","phaseReg":0x06c,"lauroc":"lauroc18_l15m2","controlLpGBT":"lpgbt15","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt15","phaseReg":0x070,"lauroc":"lauroc19_l15m2","controlLpGBT":"lpgbt15","boardSide":"B"},\
                      {"lpgbtNum":"lpgbt16","phaseReg":0x06c,"lauroc":"lauroc20_l15m2","controlLpGBT":"lpgbt15","boardSide":"B"},
        ]
        results = {}

        testLauroc = getattr(self, 'laurocConfigureBox').currentText()
        numTest = 100
        #self.READBACK = False

        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="lauroc")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="lauroc")

        #time.sleep(1)
        #readbackSuccess = self.writeToLAUROC("lauroc13", 0x0, 0x2)
        #print(readbackSuccess)
        #return None

        for config in configList :
          lpgbtNum = config["lpgbtNum"]
          phaseReg = config["phaseReg"]
          lauroc = config["lauroc"]
          controlLpGBT = config["controlLpGBT"]
          boardSide = config["boardSide"]
          results[lauroc] = {}
          goodVals = []
          #self.setAllCP40MHz(onOff="off")
          for phaseVal in [0,1]:
            print("TESTING",lauroc,"DELAY",hex(phaseVal))
            #reset all chips while adjusting clocks
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStart",chipType="lauroc")
            #self.chipCP40Control(chip=lauroc,onOff="off")

            self.setCP40MHzInvert(lauroc,invVal=phaseVal)

            #stop reset
            #self.chipCP40Control(chip=lauroc,onOff="on")
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStop",chipType="lauroc")
            
            #test loop, try COLUTA reg write multiple times and record # successes
            testCount = 0
            failCount = 0
            writeVal = 1
            for testNum in range(0,numTest,1):
              readbackSuccess = self.writeToLAUROC(lauroc, 0x0, writeVal)
              if readbackSuccess == True :
                testCount += 1
              else :
                failCount += 1
              if writeVal == 1 :
                writeVal = 2
              else :
                writeVal = 1
              if failCount > 10 :
                break
            results[lauroc][phaseVal] = testCount
            #self.lpgbtReset(controlLpGBT) #make sure I2C bus still works
            if testCount == numTest :
              goodVals.append(phaseVal)
            #make sure all chips still function
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStart",chipType="lauroc")
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStop",chipType="lauroc")

          #end phase loop
          if len(goodVals) > 0 :
            goodVal = goodVals[0]
            print("Identified good value",lauroc,hex(goodVal))
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStart",chipType="lauroc")
            #read current reg value and update phase
            self.setCP40MHzInvert(lauroc,invVal=goodVal)
            self.set_RSTB(RST_AB=boardSide,setStartStop="resetStop",chipType="lauroc")

        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")

        #end lauroc/config loop
        print( results )
        for lauroc in results :
          print(lauroc)
          for val in results[lauroc]:
            #print(delay,"\t",hex(delay),"\t",round(delay*0.78125,2),"\t",results[coluta][delay]/10.)
            print(val,"\t\t",results[lauroc][val]/float(numTest))
        pass
        return None

    def setAllCP40MHz(self,onOff):
        cp40MHzChips = ["coluta20","coluta19","coluta18","coluta17","coluta16","coluta15","coluta14","coluta13",\
                        "lauroc20","lauroc19","lauroc18","lauroc17","lauroc16","lauroc15","lauroc14","lauroc13"]
        for chip in cp40MHzChips :
          self.chipCP40Control(chip=chip,onOff=onOff)

    def writeToCOLUTAChannel_singleWrite(self, coluta, channel, READBACK = False,writeVal=None,disp=True):
        """ Write full configuration for given COLUTA channel """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToCOLUTAChannel)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        dataBits = self.colutaI2CWriteControl(coluta, channel, broadcast=False)
        dataBits64 = [dataBits[64*i:64*(i+1)] for i in range(len(dataBits)//64)]
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b00100000 #SCL NOT driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #update frequency
        #print( dataBits64 )
        if len(dataBits64) == 0 :
            return
        wordNum = 2
        word = dataBits64[wordNum]
        dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
        if writeVal != None :
          dataBits8[0] = writeVal
          #print( [hex(x) for x in dataBits8] )

        #do a COLUTA write
        if True :    
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
         
        if False : 
            self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        #do readback
        readbackSuccess = False
        if READBACK:
            readBackBits = '01' + word[-14:]
            readBackBits = readBackBits.zfill(64)
            readBackBits8 = [int(readBackBits[8*i:8*(i+1)], 2) for i in range(len(readBackBits)//8)]
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
            readback = readFromLpGBT(int(lpgbtI2CAddr, 2), 0x189-8, 6, ICEC_CHANNEL=ICEC_CHANNEL) 
            #if readback[:6] != dataBits8[:6]: readbackSuccess = False
            #print("Writing", [hex(x) for x in dataBits8[:6]])
            #print("Reading", [hex(x) for x in readback])
            if readback[:6] == dataBits8[:6]:
              readbackSuccess = True
              #print("Successfully readback what was written!")
            else:
              if disp == True :
                print("Readback does not agree with what was written")     

        return readbackSuccess

    def writeToColuta_singleByteWrite(self, coluta, channel, READBACK = False,writeVal=None,disp=True):
        """ Write full configuration for given COLUTA channel """
        if self.chips[coluta].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[coluta].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToCOLUTAChannel)")
            return

        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[coluta].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[coluta].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        dataBits = self.colutaI2CWriteControl(coluta, channel, broadcast=False)
        dataBits64 = [dataBits[64*i:64*(i+1)] for i in range(len(dataBits)//64)]

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)     #SCL/SDA pull up disabled, low drive strength
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        #colutaI2CAddrH = colutaI2CAddrH + 8 # set SDA drive strength high
        colutaI2CAddrH = colutaI2CAddrH + self.i2cConfigReg # enable SDA pullup
        #colutaI2CAddrH = colutaI2CAddrH + 32 # set SCL drive strength high
        #colutaI2CAddrH = colutaI2CAddrH + 64 # enable SCL pullup
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000100 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        #i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #update frequency
        if True :
          writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [i2cCtrlRegVal, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
          writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)

        if len(dataBits64) == 0 :
            return

        if disp == True :
            print(coluta,"\t",channel)
            print("I2C ADDRESS\t",hex(colutaI2CAddrH),"\t",hex(colutaI2CAddrL))
        wordToWrite = 0
        wordNum = 0
        #for wordNum, word in enumerate(dataBits64):
        #    if wordNum != wordToWrite : 
        #      continue
        if True :
            word = dataBits64[wordNum]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            if writeVal != None :
              dataBits8[0] = writeVal
            #print("NEW WORD")
            #for data in dataBits8 :
            #  print("\t", hex(data) )

            #do a COLUTA write  
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)

            #self.readFromCOLUTAChannel(coluta,word)
            #writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            #writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
        #finish word loop
        time.sleep(0.001)

        #check status bit
        readbackSuccess = False
        if READBACK == True :
          bit = readFromLpGBT(int(lpgbtI2CAddr, 2), 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
          if bit[0] == 4:
            readbackSuccess = True
          #print("readbackSuccess",readbackSuccess)
        return readbackSuccess


    def set_DCDC(self,dcdcName="",onOff=""):
        if onOff != "on" and onOff != "off" :
          print("ERROR: (set_DCDC) invalid onOff input",onOff)
          return None
        dcdcDict = { "PA_A"   :{"lpGBT":"lpgbt12","GPIO":2 ,"ctrlReg":"piooutl","ctrlBit":2},\
                     "ADC_A"  :{"lpGBT":"lpgbt12","GPIO":11,"ctrlReg":"pioouth","ctrlBit":3},\
                     "LPGBT_A":{"lpGBT":"lpgbt13","GPIO":4 ,"ctrlReg":"piooutl","ctrlBit":4},\
                     "PA_B"   :{"lpGBT":"lpgbt13","GPIO":2 ,"ctrlReg":"piooutl","ctrlBit":2},\
                     "ADC_B"  :{"lpGBT":"lpgbt13","GPIO":3 ,"ctrlReg":"piooutl","ctrlBit":3},\
                     "LPGBT_B":{"lpGBT":"lpgbt12","GPIO":4 ,"ctrlReg":"piooutl","ctrlBit":4},\
                   }
        if dcdcName not in dcdcDict :
          print("ERROR: (set_DCDC) invalid DCDC name",dcdcName)
          return None
        ctrlLpGBT = dcdcDict[dcdcName]["lpGBT"]
        ctrlReg = dcdcDict[dcdcName]["ctrlReg"]
        ctrlBit = dcdcDict[dcdcName]["ctrlBit"]
        if ctrlLpGBT not in self.chips :
          print("ERROR: (set_DCDC) invalid control lpGBT",ctrlLpGBT)
          return None
        if ctrlReg not in self.chips[ctrlLpGBT] :
          print("ERROR: (set_DCDC) control register not in lpGBT configuration",ctrlReg)
          return None
        ctrlRegAddr = int(self.chips[ctrlLpGBT][ctrlReg].address , 0 )
        
        #get current control reg val
        regReadVal = self.readFromLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, nBytes=1, disp = False)
        if len(regReadVal) != 1 :
          print("ERROR: (set_DCDC) register read failed")
          return None
        regReadVal = regReadVal[0]

        #define new register value to write
        ctrlBitMask = (0x1 << ctrlBit)
        newRegVal = (regReadVal & (~ctrlBitMask)) #zero-out relevant control bits
        if onOff == "on" :
          newRegVal = (newRegVal | ctrlBitMask) #set control bit to 1
        
        #write new val to register
        self.writeToLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, dataBits=[newRegVal], disp = False) #GPIO0 LOW OUTPUT bit0 low
        #check new value
        regReadVal = self.readFromLPGBT(lpgbt=ctrlLpGBT, register=ctrlRegAddr, nBytes=1, disp = False)
        if len(regReadVal) != 1 :
          print("ERROR: (set_DCDC) updated register read failed")
          return None
        regReadVal = regReadVal[0]
        if regReadVal != newRegVal :
          print("ERROR: (set_DCDC) Setting",dcdcName,onOff,"failed!")
          return None
        return None

    def doReset(self) :
        print("RESET")
        self.set_RSTB(RST_AB="A",setStartStop="resetStart",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStart",chipType="all")
        time.sleep(1)
        self.set_RSTB(RST_AB="A",setStartStop="resetStop",chipType="all")
        self.set_RSTB(RST_AB="B",setStartStop="resetStop",chipType="all")

    def setupI2cBus(self,chip):
        if chip not in self.chips :
          print("ERROR: (setupI2cBus) invalid chip ", chip )
          return None
        lpgbtName = "lpgbt"+self.chips[chip].lpgbtMaster

        #chip I2C address info dict
        i2cControl = self.chips[chip].i2cMaster
        if i2cControl not in ["0","1","2"]:
          print("ERROR: (setupI2cBus) control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: (setupI2cBus) control lpGBT bus not in bus info", i2cControl )
          return None
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]

        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configVal = 0b00000000
        #configVal = configVal + 8 # set SDA drive strength high
        configVal = configVal + self.i2cConfigReg # enable SDA pullup
        #configVal = configVal + 32 # set SCL drive strength high
        #configVal = configVal + 64 # enable SCL pullup
        self.writeToLPGBT(lpgbt=lpgbtName, register=configReg, dataBits=[configVal], disp = False) #send I2C address value to control lpGBT
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10100000 #SCL driven by CMOS buffer, multi-byte write = 8, freq = 100kHz
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #update frequency
        self.writeToLPGBT(lpgbt=lpgbtName, register=dataReg, dataBits=[i2cCtrlRegVal], disp = False)
        self.writeToLPGBT(lpgbt=lpgbtName, register=cmdReg, dataBits=[0x0], disp = False)
        return None


    def singleI2CWriteToChip(self,chip=None,data=None,disp=True,doReadback=True):
        if chip == None :
          return None
        if chip not in self.chips :
          print("ERROR: invalid chip specified",chip)
          return None
        controlLpgbtNum = self.chips[chip].lpgbtMaster
        controlLpgbt = "lpgbt" + str(controlLpgbtNum)        
        #if controlLpgbt not in ["lpgbt11","lpgbt12","lpgbt13","lpgbt14"] :
        #  print("ERROR: invalid control lpGBT specified",controlLpgbt)
        #  return None
        if controlLpgbt not in self.chips :
          print("ERROR: control lpGBT not in chips dict",controlLpgbt)
          return None

        #chip I2C address info
        i2cControl = self.chips[chip].i2cMaster
        i2cAddress = self.chips[chip].i2cAddress
        if i2cControl not in ["0","1","2"]:
          print("ERROR: control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6,"status":0x161},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd,"status":0x176},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104,"status":0x18b},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        i2cAddress = i2cAddress.replace("x","0") #will not work with addressing on certain chips
        i2cAddressVal = int(str(i2cAddress),2)
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]
        statusReg = i2cBusInfo[i2cControl]["status"]

        dataVal = 0
        try:
            dataVal = int(data)
        except:
            print("Invalid value")
            return
        if dataVal < 0 or dataVal > 255 :
            print("Invalid value")
            return

        #define I2C control register values
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 
        configRegVal = configRegVal + self.i2cConfigReg

        #self.i2cCmdFreq = 2
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer
        #i2cCtrlRegVal = 0b00000000 #SCL NOT sdriven by CMOS buffer
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #add freq value

        if disp == True :
          print("Single I2C write")
          print("Write to bus",i2cControl,"chip",chip,"chip address",i2cAddress,"\t",hex(i2cAddressVal),"\tdataVal",hex(dataVal))
          print("controlLpgbt", controlLpgbt, "\tconfigReg", hex(configReg), "\tconfigRegVal",hex(configRegVal) )
          print("controlLpgbt", controlLpgbt, "\tcmdReg", hex(cmdReg), "\ti2cCtrlRegVal",hex(i2cCtrlRegVal) )
         

        #set correct bits in I2CMX config
        self.writeToLPGBT(controlLpgbt, configReg, [configRegVal]) #No pull ups, low drive strength, ext addr bits set to 0
        #self.writeToLPGBT(controlLpgbt, configReg, [0b00001000]) #No pull ups, low drive strength, ext addr bits set to 0
        #self.writeToLPGBT(controlLpgbt, configReg, [0b00100000]) #No pull ups, SCL hight drive strength, SDA low drive strength, ext addr bits set to 0
        #self.writeToLPGBT(controlLpgbt, configReg, [0b00111000]) #No pull ups, SCL hight drive strength, SDA low drive strength, ext addr bits set to 0

        #control reg update 
        self.writeToLPGBT(controlLpgbt, dataReg, [i2cCtrlRegVal]) #SCL CMOS buffer driver, number of bytes, 200kHz
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x0]) #send I2C write command to control lpGBT

        #actually do write
        self.writeToLPGBT(controlLpgbt, addrReg, [i2cAddressVal]) #send chip I2C address value to control lpGBT
        self.writeToLPGBT(controlLpgbt, dataReg, [dataVal]) #I2C data value, contains chip register write info, exact process depends on chip
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x2])  #send I2C write command to control lpGBT

        readbackSuccess = False
        if doReadback == True :
          statusVal = self.readFromLPGBT(lpgbt=controlLpgbt,register=statusReg, nBytes=1, disp = False)
          if len(statusVal) == 1 :
            if statusVal[0] == 4:
              readbackSuccess = True

        if disp == True :
          #bit = readFromLpGBT(int(lpgbtI2CAddr, 2), 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
          print("Done write")
        return readbackSuccess

    def singleI2CReadFromChip(self,chip=None,disp=True):
        if chip == None :
          return None
        if chip not in self.chips :
          print("ERROR: invalid chip specified",chip)
          return None
        controlLpgbtNum = self.chips[chip].lpgbtMaster
        controlLpgbt = "lpgbt" + str(controlLpgbtNum)        
        if controlLpgbt not in ["lpgbt11","lpgbt12","lpgbt13","lpgbt14"] :
          print("ERROR: invalid control lpGBT specified",controlLpgbt)
          return None
        if controlLpgbt not in self.chips :
          print("ERROR: control lpGBT not in chips dict",controlLpgbt)
          return None

        #chip I2C address info
        i2cControl = self.chips[chip].i2cMaster
        i2cAddress = self.chips[chip].i2cAddress
        if i2cControl not in ["0","1","2"]:
          print("ERROR: control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6,"readByte":0x163},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd,"readByte":0x178},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104,"readByte":0x18d},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        i2cAddress = i2cAddress.replace("x","0") #will not work with addressing on certain chips
        i2cAddressVal = int(str(i2cAddress),2)
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]
        readByteReg = i2cBusInfo[i2cControl]["readByte"]

        if disp == True :
          print("Single Byte I2C read")
          print("Write to bus",i2cControl,"chip address",i2cAddress,"\t",i2cAddressVal)
          print("controlLpgbt", controlLpgbt, "cmdReg", hex(cmdReg) )

        #set correct bits in I2CMX config
        #[0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000
        configRegVal = configRegVal + self.i2cConfigReg
        self.writeToLPGBT(controlLpgbt, configReg, [configRegVal]) #No pull ups, low drive strength, ext addr bits set to 0

        #control reg update 
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #add freq value
        self.writeToLPGBT(controlLpgbt, dataReg, [i2cCtrlRegVal]) #SCL CMOS buffer driver, number of bytes, 200kHz
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x0]) #send I2C write command to control lpGBT

        #actually do READ
        self.writeToLPGBT(controlLpgbt, addrReg, [i2cAddressVal]) #send chip I2C address value to control lpGBT
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x3]) #send I2C single byte read command to control lpGBT

        #get readByteReg
        readVal = self.readFromLPGBT(lpgbt=controlLpgbt, register=readByteReg, nBytes=1, disp = disp)

        if disp == True :
          print("Done read",readVal)
        return readVal

    def multiI2CWriteToChip(self,chip=None,bytes=None,disp=True):
        if chip == None :
          return None
        if chip not in self.chips :
          print("ERROR: invalid chip specified",chip)
          return None
        controlLpgbtNum = self.chips[chip].lpgbtMaster
        controlLpgbt = "lpgbt" + str(controlLpgbtNum)        
        #if controlLpgbt not in ["lpgbt11","lpgbt12","lpgbt13","lpgbt14"] :
        #  print("ERROR: invalid control lpGBT specified",controlLpgbt)
        #  return None
        if controlLpgbt not in self.chips :
          print("ERROR: control lpGBT not in chips dict",controlLpgbt)
          return None
        if len(bytes) == 0 or len(bytes) > 4 :
          print("ERROR: invalid number of bytes specified:", len(bytes), bytes)
          return
        if int(self.i2cCmdFreq) < 0 or int(self.i2cCmdFreq) > 3 :
          print("ERROR: invalid I2C frequency setting",int(self.i2cCmdFreq))
          return

        #chip I2C address info
        i2cControl = self.chips[chip].i2cMaster
        i2cAddress = self.chips[chip].i2cAddress
        if i2cControl not in ["0","1","2"]:
          print("ERROR: control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        i2cAddress = i2cAddress.replace("x","0") #will not work with config process on most chips
        i2cAddressVal = int(str(i2cAddress),2)
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]

        if disp == True :
          print("Multi-byte I2C write to ",chip)
          print("\tcontrolLpgbt", controlLpgbt,"\tbus",i2cControl,"\tcmdReg", hex(cmdReg) )
          print("\tChip I2C address",i2cAddress,"\taddr val",i2cAddressVal,"\twrite bytes", [hex(x) for x in bytes])

        #ICMCONFIG [0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 + self.i2cConfigReg
        self.writeToLPGBT(controlLpgbt, configReg, [configRegVal]) #No pull ups, low drive strength, ext addr bits set to 0

        #control reg update
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer, multi-byte write = 8
        i2cCtrlRegVal = i2cCtrlRegVal  + (len(bytes) << 2) #multi-byte write = len(data) 
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #add freq value
        self.writeToLPGBT(controlLpgbt, dataReg, [i2cCtrlRegVal] )#specifies 4 bytes for multi-reg write commands, 200kHz interface
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x0]) #send I2C write command to control lpGBT

        #actually do write
        self.writeToLPGBT(controlLpgbt, addrReg, [i2cAddressVal] ) #send I2C chip address value to control lpGBT
        self.writeToLPGBT(controlLpgbt, dataReg, bytes ) #send I2C data value to control lpGBT
        self.writeToLPGBT(controlLpgbt, cmdReg, [0x8]) #send I2C multi-byte write command to control lpGBT, I2C_W_MULTI_4BYTE0
        self.writeToLPGBT(controlLpgbt, cmdReg, [0xC]) #send I2C write command to control lpGBT, I2C_WRITE_MULTI 
        print("Done write")
        return

    def multiI2CReadToChip(self,chip=None,nBytes=None,disp=True):
        if chip == None :
          return None
        if chip not in self.chips :
          print("ERROR: invalid chip specified",chip)
          return None
        controlLpgbtNum = self.chips[chip].lpgbtMaster
        controlLpgbt = "lpgbt" + str(controlLpgbtNum)        
        if controlLpgbt not in ["lpgbt11","lpgbt12","lpgbt13","lpgbt14"] :
          print("ERROR: invalid control lpGBT specified",controlLpgbt)
          return None
        if controlLpgbt not in self.chips :
          print("ERROR: control lpGBT not in chips dict",controlLpgbt)
          return None
        nBytes = int(nBytes)
        if nBytes == 0 or nBytes > 4 :
          print("ERROR: invalid number of bytes specified:", nBytes)
          return
        if int(self.i2cCmdFreq) < 0 or int(self.i2cCmdFreq) > 3 :
          print("ERROR: invalid I2C frequency setting",int(self.i2cCmdFreq))
          return

        #chip I2C address info
        i2cControl = self.chips[chip].i2cMaster
        i2cAddress = self.chips[chip].i2cAddress
        if i2cControl not in ["0","1","2"]:
          print("ERROR: control lpGBT bus not valid", i2cControl )
          return None
        i2cBusInfo = { "0":{"addr":0x0f1,"i2cmConfig":0x0f0,"data0":0x0f2,"cmd":0x0f6},\
                       "1":{"addr":0x0f8,"i2cmConfig":0x0f7,"data0":0x0f9,"cmd":0x0fd},\
                       "2":{"addr":0x0ff,"i2cmConfig":0x0fe,"data0":0x100,"cmd":0x104},\
                     }
        if i2cControl not in i2cBusInfo :
          print("ERROR: control lpGBT bus not in bus info", i2cControl )
          return None
        i2cAddress = i2cAddress.replace("x","0") #will not work with config process on most chips
        i2cAddressVal = int(str(i2cAddress),2)
        addrReg = i2cBusInfo[i2cControl]["addr"]
        dataReg = i2cBusInfo[i2cControl]["data0"]
        cmdReg = i2cBusInfo[i2cControl]["cmd"]
        configReg = i2cBusInfo[i2cControl]["i2cmConfig"]

        nBytes = 2
        if disp == True :
          print("Multi-byte I2C read from ",chip)
          print("\tcontrolLpgbt", controlLpgbt,"\tbus",i2cControl,"\tcmdReg", hex(cmdReg) )
          print("\tChip I2C address",i2cAddress,"\taddr val",i2cAddressVal,"\tnumber bytes", nBytes)

        #ICMCONFIG [0x0f7] 6-I2CM1SCLPullUpEnable,5-I2CM1SCLDriveStrength,4-I2CM1SDAPullUpEnable,3-I2CM1SDADriveStrength,2:0-I2CM1AddressExt[2:0]
        configRegVal = 0b00000000 + self.i2cConfigReg
        self.writeToControlLPGBT(controlLpgbt, configReg, [configRegVal]) #No pull ups, low drive strength, ext addr bits set to 0

        #control reg update
        #i2c control reg: [7] - SCLDriveMode,  [6:2] - NBYTE[4:0], [1:0] - FREQ[1:0]
        i2cCtrlRegVal = 0b10000000 #SCL driven by CMOS buffer, multi-byte write = 8
        i2cCtrlRegVal = i2cCtrlRegVal  + ((nBytes) << 2) #multi-byte write = len(data) 
        i2cCtrlRegVal = i2cCtrlRegVal + int(self.i2cCmdFreq) #add freq value
        self.writeToControlLPGBT(controlLpgbt, dataReg, [i2cCtrlRegVal] )#specifies 4 bytes for multi-reg write commands, 200kHz interface
        self.writeToControlLPGBT(controlLpgbt, cmdReg, [0x0]) #send I2C write command to control lpGBT

        #actually do write
        self.writeToControlLPGBT(controlLpgbt, addrReg, [i2cAddressVal] ) #send I2C chip address value to control lpGBT
        self.writeToControlLPGBT(controlLpgbt, cmdReg, [0xD]) #send I2C read command to control lpGBT, I2C_READ_MULTI
        print("Done read")
        return

## Helper functions
def u16_to_bytes(val):
    byte1 = (val >> 8) & 0xff
    byte0 = (val >> 0) & 0xff
    return byte1, byte0

def makeI2CSubData(dataBits,wrFlag,readBackMux,subAddress,adcSelect):
    '''Combines the control bits and adds them to the internal address'''
    # {{dataBitsSubset}, {wrFlag,readBackMux,subAddress}, {adcSelect}}, pad with zeros
    return (dataBits+wrFlag+readBackMux+subAddress+adcSelect).zfill(64)

