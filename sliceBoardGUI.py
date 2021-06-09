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
import status
import subprocess
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

        # Some version-dependent parameters/values

        #self.nSamples = 1000000  # default number of samples to parse from standard readout
        self.nSamples = 1000  # default number of samples to parse from standard readout
        self.discarded = 0  # first N samples of readout are discarded by software (MSB end)
        self.dataWords = 32  # number of bytes for each data FPGA coutner increment
        self.controlWords = 8 # number of bytes for each control FPGA counter increment

        # Readback configs as they are writen
        self.READBACK = False

        self.getMetadataFromJSON()
        self.opened = True

	# Data taking parameters
        self.att_val = '-99'
        self.awg_amp = '-99'
        self.awg_freq = '-99'
        self.measStep = '-99'
        self.daqMode = 'trigger'
        self.daqADCSelect = '7'
        self.singleADCMode_ADC = 'trigger'

        # Default attributes for hdf5 output, overwritten by instrument control
        self.runType = 'sine'
        self.sineFrequency = '1.00'
        self.sineAmplitude = '0.50'
        self.awgFreq = 1200 # Sampling freq of external AWG
        self.pulseLength = 64 # Pulse length in bunch crossings
 
        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        self.status36 = status.Status(self, "36")
        self.status45 = status.Status(self, "45")

        # Instrument control
        #self.IPaddress = self.ipAddressBox.toPlainText()
        #self.IC = instrumentControlMod.InstrumentControl(self,'./config/instrumentConfig.cfg')
        #self.function_generator = getattr(self.IC,'function_generator')

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
        self.test3Button.clicked.connect(lambda: parseDataMod.main(self, "lauroc-1.dat"))
        self.test2Button.clicked.connect(takeManagerData)
   
        # instrument buttons
        self.initializeInstrumentButton.clicked.connect(lambda:instrumentControlMod.initializeInstrumentation(self))

        # Data buttons
        self.takePedestalDataButton.clicked.connect(lambda: self.takeTriggerData("pedestal"))
        self.takeSineDataButton.clicked.connect(lambda: self.takeTriggerData("sine"))
        self.takePulseDataButton.clicked.connect(lambda: self.takeTriggerData("pulse"))
        self.incrementRunNumberButton.clicked.connect(self.incrementRunNumber)

        self.clockScanButton.clicked.connect(lambda: clockMod.scanClocks(self, self.allCOLUTAs))
        #self.clockScanButton.clicked.connect(lambda: clockMod.scanClocks(self, ["coluta20"]))
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
        self.nSamplesBox.textChanged.connect(self.updateNSamples)
        #self.dataDisplay = MPLCanvas(self.dataDisplayWidget,x=np.arange(2),style='r.',
        #                                        ylim=[0,65536],ylabel='ADC Counts')
        #self.dataGridLayout.addWidget(self.dataDisplay,0,0)
        #self.displayGridLayout.addWidget(self.dataDisplay,0,0)

        self.isConnected = True
        #self.startup()
        #self.lpgbt_i2c_read()
        # self.sendConfigurationsFromLpGBT()

    def testFunc(self):
        while True:
          #print("Configuring LAUROC20")
          #self.sendFullLAUROCConfigs("lauroc20")
          print("Configuring COLUTA20")
          self.sendFullCOLUTAConfig("coluta20")
          time.sleep(0.5)

    ########################## Basic read/write control for all chips ##########################

    def writeToLPGBT(self, lpgbt, register, dataBits, disp = False):
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            self.writeToControlLPGBT(lpgbt,register,dataBits)
        elif lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            self.writeToDataLPGBT(lpgbt,register,dataBits)
        else:
            print("Bad LPGBT value in writeToLPGBT")
        if disp:
            print("Writing", lpgbt, hex(register), ":", [hex(x) for x in dataBits])


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

        #print("Writing", [hex(byte) for byte in data], "to register ", hex(register))
        regH, regL = u16_to_bytes(register)

        # We will write 16 bytes to i2cM1Data at a time
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [0x80 + ((len(data)+2) << 2), 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
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
        print("Writing")
        self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

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

        #print("Reading register ", hex(register))
        regH, regL = u16_to_bytes(register)
        # We will write 2 bytes to the data lpGBT
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [0b10001000, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        # Write 2 byte register address
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [regL, regH, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xc], ICEC_CHANNEL=ICEC_CHANNEL)
        # We will read 14 bytes from the data lpGBT
        writeToLpGBT(lpgbtI2CAddr, 0x0f9, [0x80 + (nBytes << 2), 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd,  [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL) 
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0xd], ICEC_CHANNEL=ICEC_CHANNEL)
        # readFromLpGBT(lpgbtI2CAddr, 0x179, 16, ICEC_CHANNEL=ICEC_CHANNEL)
        
        # Check to see if the i2c Bus Transaction is finished before proceeding
        print("Reading")
        self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        ReverseReadback = readFromLpGBT(lpgbtI2CAddr, 0x189 - nBytes, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
        #print("Read: ", [hex(val) for val in ReverseReadback[::-1]])
        return ReverseReadback[::-1]

    def writeToLAUROC(self, lauroc, register, data):
        """ Writes data to LAUROC one register at a time """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)

        if self.chips[lauroc].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[lauroc].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToLAUROC)")
            return

        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)

        # Check to see if the i2c Bus Transaction is finished before proceeding
        print("Checking Write")
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

    def readFromLAUROC(self, lauroc, register):
        """ Reads from LAUROC one register at a time """
        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)

        if self.chips[lauroc].lpgbtMaster == '12': 
            ICEC_CHANNEL = 0
        elif self.chips[lauroc].lpgbtMaster == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (writeToLAUROC)")
            return

        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), 0x00, 0x00, 0x00], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0fd, [0x3], ICEC_CHANNEL = ICEC_CHANNEL)

        # Check to see if the i2c Bus Transaction is finished before proceeding
        print("Checking Read")
        self.i2cTransactionCheck(lpgbtI2CAddr, ICEC_CHANNEL)

        readback = readFromLpGBT(lpgbtI2CAddr, 0x178, 1, ICEC_CHANNEL = ICEC_CHANNEL)
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
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)

        readbackSuccess = True
        for word in dataBits64:
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            #print("0x0f9:", [hex(x) for x in [0b00100000, 0x00, 0x00, 0x00, 0x0]])
            #print("0x0f9:", [hex(x) for x in [*dataBits8[4:][::-1], 0x8]])
            #print("0x0f9:", [hex(x) for x in [*dataBits8[:4][::-1], 0x9]])
            #print("0x0f7:", [hex(x) for x in [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe]])
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
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
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)

        readBackBits = '01' + word[-14:]
        readBackBits = readBackBits.zfill(64)
        readBackBits8 = [int(readBackBits[8*i:8*(i+1)], 2) for i in range(len(readBackBits)//8)]
        writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
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
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        dataBitsGlobal = self.colutaI2CWriteControl(coluta, "global")
        dataBitsGlobal64 = [dataBitsGlobal[64*i:64*(i+1)] for i in range(len(dataBitsGlobal)//64)]       
       
        counter = 1
        full_write = []
        for word in dataBitsGlobal64[::-1]:
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            for x in dataBits8:
                full_write.append(x)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
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
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)

        counter = 1
        full_readback = []
        for _ in range(2):
            addrModification = counter*8
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
 
        #if input("Configure all colutas?(y/n)\n") != 'y':
        #    print("Exiting config all")
        #    return
        for coluta in colutas:
            print("Configuring", coluta)
            self.sendFullCOLUTAConfig(coluta)
            time.sleep(0.5) 

        #if input("Configure all laurocs?(y/n)\n") != 'y':
        #    print("Exiting config all")
        #    return 
        for lauroc in laurocs:
            print("Configuring", lauroc)
            self.sendFullLAUROCConfigs(lauroc)
            time.sleep(0.5)

        print("Done Configuring")
        print("Configuration results")
        for chip in self.configResults :
          print(chip,"",self.configResults[chip])

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
            if readback[0] != data: readbackSuccess = False
            if self.READBACK:
                print("Writing", lauroc, hex(startReg), ":", hex(data))
                print("Reading", lauroc, hex(startReg), ":", hex(readback[0]))
                if readback[0] == data:
                    print("Successfully readback what was written!")
                else:
                    print("Readback does not agree with what was written")
        self.configResults[lauroc] = readbackSuccess
        print("Done configuring", lauroc, ", success =", readbackSuccess)

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

        channels = ["ch"+str(i) for i in range(1,9)]
        readbackSuccess = True
        for ch in channels:
            print("Configuring ", ch, coluta)
            readbackChSucess = self.writeToCOLUTAChannel(coluta, ch, self.READBACK)
            readbackSuccess = readbackSuccess & readbackChSucess

        globalSuccess = self.writeToCOLUTAGlobal(coluta)
        readbackSuccess = readbackSuccess & globalSuccess
        self.configResults[coluta] = readbackSuccess
        print("Done configuring", coluta, ", success =", readbackSuccess)

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
                    self.writeToControlLPGBT(chipName, addr, data)
            elif chipName in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
                dataToSend = self.sortUpdates(updates, 14)
                for (addr, data) in dataToSend.items():
                    self.writeToDataLPGBT(chipName, addr, data)
            elif chipName.find('lauroc') == 0:
                for (addr, data) in updates.items():
                    self.writeToLAUROC(chipName, addr, data[1])
            elif chipName.find('coluta') == 0:
                for (addr, data) in updates.items():
                    if data[0] == 'global':
                        self.writeToCOLUTAGlobal(chipName)
                    else:
                        self.writeToCOLUTAChannel(chipName, data[0])
            else:
                print('ChipName Not recognized: ', chipName)
        print("Done Updating")


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
            self.incrementRunNumber()
            self.opened = False  
        outputDirectory = '../Runs'
        outputFile = "run"+str(self.runNumber).zfill(4)+".dat"
        stampedOutputFile = "run"+str(self.runNumber).zfill(4)+"-1.dat"
        outputPath = outputDirectory+"/"+outputFile
        outputPathStamped = outputDirectory+"/"+stampedOutputFile

        takeManagerData(outputDirectory, outputFile, self.daqMode, int(self.daqADCSelect))
        #subprocess.call("python takeTriggerData.py -o "+outputPath+" -t "+self.daqMode+" -a "+self.daqADCSelect, shell=True)
        #takeDataMod.takeData(outputPath, self.daqMode, self.daqADCSelect)
        time.sleep(5)
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


## Helper functions
def u16_to_bytes(val):
    byte1 = (val >> 8) & 0xff
    byte0 = (val >> 0) & 0xff
    return byte1, byte0

def makeI2CSubData(dataBits,wrFlag,readBackMux,subAddress,adcSelect):
    '''Combines the control bits and adds them to the internal address'''
    # {{dataBitsSubset}, {wrFlag,readBackMux,subAddress}, {adcSelect}}, pad with zeros
    return (dataBits+wrFlag+readBackMux+subAddress+adcSelect).zfill(64)

