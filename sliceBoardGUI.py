
from PyQt5 import uic, QtWidgets
import os
import sys
import time
import configparser
import numpy as np
import chipConfiguration as CC
import sliceMod
import dataParser
import clockMod
import serialMod
import powerMod
import status
from functools import partial
import configureLpGBT1213
from collections import OrderedDict, defaultdict
from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from flxMod import ecReadLpGBT as ecReadFromLpGBT
from flxMod import icWriteToLpGBT, ecWriteToLpGBT
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
        self.nSamples = 200  # default number of samples to parse from standard readout
        self.discarded = 0  # first N samples of readout are discarded by software (MSB end)
        self.dataWords = 32  # number of bytes for each data FPGA coutner increment
        self.controlWords = 8 # number of bytes for each control FPGA counter increment

        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        self.status36 = status.Status(self, "36")
        self.status45 = status.Status(self, "45")

        # USB-ISS port setup
        #i2cPortFound = None
        #self.i2cPort = None
        #if not self.pArgs.no_connect:
        #    i2cPortFound = configureLpGBT1213.findPort()
        #    self.i2cPort = configureLpGBT1213.setupSerial(i2cPortFound)

        # Instance of dataParser class
        dataParserConfig = "./config/dataConfig.cfg"
        self.ODP = dataParser.dataParser(self, dataParserConfig)

        # dict that will be filled with settings, like self.chips[chip][section][setting]
        self.chips = {}
        self.powerSettings = {}
        self.chipsConfig = os.path.join(os.path.abspath("."), "config", "chips.cfg")
        self.powerConfig = os.path.join(os.path.abspath("."), "config", "power.cfg")

        # Fill internal dictionaries with configurations from .cfg files
        self.setupConfigurations()

        # Establish link between GUI buttons and internal configuration dictionaries
        self.connectButtons()
        self.connectPowerButtons()

        #self.testButton.clicked.connect(self.test)
        self.test3Button.clicked.connect(lambda: powerMod.checkAllTemps(self))
        self.test2Button.clicked.connect(clockMod.scanClocks)

        self.initializeUSBButton.clicked.connect(self.initializeUSBISSModule)
        self.disableParityButton.clicked.connect(self.disableParity)
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
        #self.configureControlLpGBTButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.laurocConfigureButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.powerConfigureButton.clicked.connect(self.sendPowerUpdates)

        copyConfig = lambda w,x,y,z : lambda : self.copyConfigurations(w,sourceSectionName=x,targetChipNames=y,targetSectionNames=z)
        allLAUROCs = [f"lauroc{num}" for num in range(13, 21)]
        allCOLUTAs = [f"coluta{num}" for num in range(13, 21)]
        allDREChannels = ["ch1", "ch2", "ch3", "ch4"]
        allMDACChannels = ["ch5", "ch6", "ch7", "ch8"]
        allDataLpGBTs = ["lpgbt9", "lpgbt10", "lpgbt11", "lpgbt14", "lpgbt15", "lpgbt16"]
        allControlLpGBTs = ["lpgbt12", "lpgbt13"]

        self.LAUROC13CopyAllButton.clicked.connect(copyConfig("lauroc13", None, allLAUROCs, None))

        self.COLUTA13CopyGlobalButton.clicked.connect(copyConfig("coluta13", "global", allCOLUTAs, ["global"]))

        self.COLUTA13CopyDRETo13Button.clicked.connect(copyConfig("coluta13", "ch1", ["coluta13"], allDREChannels))
        self.COLUTA13CopyCh1ToAllButton.clicked.connect(copyConfig("coluta13", "ch1", allCOLUTAs, ["ch1"]))
        self.COLUTA13CopyDREToAllButton.clicked.connect(copyConfig("coluta13", "ch1", allCOLUTAs, allDREChannels))

        self.COLUTA13CopyMDACTo13Button.clicked.connect(copyConfig("coluta13", "ch5", ["coluta13"], allMDACChannels))
        self.COLUTA13CopyCh5ToAllButton.clicked.connect(copyConfig("coluta13", "ch5", allCOLUTAs, ["ch5"]))
        self.COLUTA13CopyMDACToAllButton.clicked.connect(copyConfig("coluta13", "ch5", allCOLUTAs, allMDACChannels))

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

        # Plotting
        #self.takeSamplesButton.clicked.connect(lambda: self.takeSamples())
        self.nSamplesBox.textChanged.connect(self.updateNSamples)
        self.dataDisplay = MPLCanvas(self.dataDisplayWidget,x=np.arange(2),style='r.',
                                                ylim=[0,65536],ylabel='ADC Counts')
        self.dataGridLayout.addWidget(self.dataDisplay,0,0)
        #self.displayGridLayout.addWidget(self.dataDisplay,0,0)

        self.isConnected = True
        #self.startup()
        #self.lpgbt_i2c_read()
        # self.sendConfigurationsFromLpGBT()


    ########################## Basic read/write control for all chips ##########################

    def writeToLPGBT(self, lpgbt, register, dataBits):
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            self.writeToControlLPGBT(lpgbt,register,dataBits)
        elif lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            self.writeToDataLpgbt(lpgbt,register,dataBits)
        else:
            print("Bad LPGBT value in writeToLPGBT")

    def readFromLPGBT(self, lpgbt, register, nBytes):
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            readback = self.readFromControlLPGBT(lpgbt, register, nBytes)
        elif lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            readback = self.readFromDataLPGBT(lpgbt, register, nBytes)
        else:
            print("Bad LPGBT value in readFromLPGBT")
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
            print("Error: trying to send more than 16 dataBits in writeToControlLPGBT")

        if lpgbt in ['lpgbt11', 'lpgbt14']:
            readback = ecReadFromLpGBT(int(chip.i2cAddress, 2), register, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
        elif lpgbt in ['lpgbt12', 'lpgbt13']:
            readback = readFromLpGBT(int(chip.i2cAddress, 2), register, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
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

        print("Writing", [hex(byte) for byte in data], "to register ", hex(register))
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
        # i2cTransactionFinished = False
        # counter = 0
        # while not i2cTransactionFinished:
        #     bit = readFromLpGBT(lpgbtI2CAddr, 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
        #     print("bit: ", bit)
        #     if bit[0] == 4:
        #         i2cTransactionFinished = True
        #     time.sleep(0.1)
        #     if counter == 10:
        #         print("I2C Transaction Failed after 1s")
        #         break
        #     counter += 1

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

        print("Reading register ", hex(register))
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
        ReverseReadback = readFromLpGBT(lpgbtI2CAddr, 0x189 - nBytes, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
        print("Read: ", [hex(val) for val in ReverseReadback[::-1]])
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

        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC_CHANNEL)

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

        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), register, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC_CHANNEL)
        writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), 0x00, 0x00, 0x00, 0x00, 0x3], ICEC_CHANNEL = ICEC_CHANNEL)
        readFromLpGBT(lpgbtI2CAddr, 0x178, 1, ICEC_CHANNEL = ICEC_CHANNEL)

    def writeToCOLUTAChannel(self, coluta, channel, readback = False):
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
            if readback:
                self.readFromCOLUTAChannel(coluta, word)

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
        readFromLpGBT(int(lpgbtI2CAddr, 2), 0x179, 16, ICEC_CHANNEL=ICEC_CHANNEL) 

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
        for word in dataBitsGlobal64[::-1]:
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]

            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
            counter += 1

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
        for _ in range(2):
            addrModification = counter*8
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x179, 16, ICEC_CHANNEL=ICEC_CHANNEL)
            counter += 1   

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
        print("lpgbt Master addr is ", lpgbtI2CAddr )
        dataI2CAddr = int(chip.i2cAddress,2)

        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:   
            i = 0
            while i < repeat:
                if (repeat - i) < 4:
                    data =  [value for _ in range(repeat - i)]
                else:
                    data = [value, value, value, value]
                self.writeToControlLPGBT(lpgbt, reg_addr + i, data)
                i += len(data)
        else:
            i = 0
            while i < repeat:
                if (repeat - i) < 14:
                    data = [value for _ in range(repeat - i)]
                else:
                    data = [value for _ in range(0,14)]
                self.writeToDataLPGBT(lpgbt, reg_addr+i, data)
                i += len(data)

    def readLPBGTRegisters(self):
        """ Reads value from user specified register in user specified lpgbt
            The repeat paramters determines how many consecutive registers are read """
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        chip = self.chips[lpgbt]

        registerBox = getattr(self, 'lpgbtregisterBox')
        valueBox = getattr(self, 'lpgbtReadLengthBox')

        try:
            reg_addr = int(registerBox.toPlainText(),16)
        except:
            print("Invalid register address")
            return
        try:
            value = int(valueBox.toPlainText(),10)
        except:
            print("Invalid value - must be decimal")
            return

        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
            dataI2CAddr = int(chip.i2cAddress,2)
            i=0
            while i < value:
                if value - i < 4:
                    count = value - i
                else:
                    count = 4
                print("Reading ", count, " registers from ", hex(reg_addr + i), " in lpgbt ", lpgbt)
                self.readFromDataLPGBT(lpgbt, reg_addr + i, count)
                i += count          

        elif lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            i=0
            while i < value:
                if value - i < 4:
                    count = value -i
                else:
                    count = 4
                print("Reading ", count," registers from ", hex(reg_addr + i), " in lpgbt ", lpgbt)
                self.readFromControlLPGBT(lpgbt, reg_addr + i, count)
                i += count


    ########################## Functions to Send Full Configurations ##########################
    def configureAll(self):
        """ Configures LPGBT9-16, COLUTA16/17/20 and LAUROC16/20 """
        print("Configuring lpgbt12")
        self.sendFullControlLPGBTConfigs("lpgbt12")
        time.sleep(0.5)
        print("Configuring lpgbt11")
        self.sendFullControlLPGBTConfigs("lpgbt11")
        time.sleep(0.5)
        print("Configuring lpgbt13")
        self.sendFullControlLPGBTConfigs("lpgbt13")
        time.sleep(0.5)
        print("Configuring lpgbt14")
        self.sendFullControlLPGBTConfigs("lpgbt14")
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
       
        print("Configuring COLUTA16")
        self.sendFullCOLUTAConfig("coluta16")
        time.sleep(0.5) 
        print("Configuring COLUTA17")
        self.sendFullCOLUTAConfig("coluta17")
        time.sleep(0.5) 
        print("Configuring COLUTA20")
        self.sendFullCOLUTAConfig("coluta20")
        time.sleep(0.5) 

        print("Configuring LAUROC16")
        self.sendFullLAUROCConfigs("lauroc16")
        time.sleep(0.5)
        print("Configuring LAUROC20")
        self.sendFullLAUROCConfigs("lauroc20")
        time.sleep(0.5)
        

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

        for (register, dataBits) in sectionChunks.items():
            self.writeToControlLPGBT(lpgbt, register, dataBits)
            # readback = self.readFromControlLPGBT(lpgbt, register, len(dataBits))
            # if readback == dataBits:
            #     print("Successfully readback what was written!")
            # else:
            #     print("Readback does not agree with what was written")     

    def sendFullDataLPGBTConfigs(self, lpgbt):
        """ Sends all current configurations for given data lpgbt"""
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[lpgbt].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        #Collect configuration in groups of 14 registers
        chip = self.chips[lpgbt]
        chipList = list(chip.values())
        dataBits14 = defaultdict(list)
        for iSection in range(0, len(chip), 14):
            startReg = int(chipList[iSection].address, 0)
            for i in range(14):
                try:
                    bits = int(chipList[iSection+i].bits, 2)
                except IndexError:
                    bits = 0
                dataBits14[startReg].append(bits)
       
        for (register, dataBits) in dataBits14.items():
            self.writeToDataLPGBT(lpgbt, register, dataBits)
            #readback = self.readFromDataLPGBT(lpgbt, register, len(dataBits))
            #if readback == dataBits:
            #    print("Successfully readback what was written!")
            #else:
            #    print("Readback does not agree with what was written")

    def sendFullLAUROCConfigs(self, laurocName):
        """ Sends all current configurations for given lauroc """
        if laurocName == 'box':
            lauroc = getattr(self, 'laurocConfigureBox').currentText()
        else:
            lauroc = laurocName
        print("Resetting lpgbt master control")
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

        for iSection in range(0, len(chip)):
            startReg = int(chipList[iSection].address, 0)
            data = sectionChunks[startReg]
            print("writing", hex(data), "to", hex(startReg))
            self.writeToLAUROC(lauroc, startReg, data)
            #print("reading back")
            #self.readFromLAUROC(lauroc, startReg)

    def sendFullCOLUTAConfig(self, colutaName):
        """ Configure all coluta channels and global bits """
        #colutaName = "coluta20"
        if colutaName == 'box':
            coluta = getattr(self, 'colutaConfigureBox').currentText()
        else:
            coluta = colutaName
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[coluta].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        channels = ["ch"+str(i) for i in range(1,9)]
        for ch in channels:
            self.writeToCOLUTAChannel(coluta, ch, readback = False)

        self.writeToCOLUTAGlobal(coluta)
        self.readFromCOLUTAGlobal(coluta)

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
            self.powerSettings[voltageSetting] = [lpgbt, pin]
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
        badLAUROCS = ['lauroc13', 'lauroc14', 'lauroc15', 'lauroc17', 'lauroc18', 'lauroc19']
        badCOLUTAs = ['coluta13', 'coluta14', 'coluta15', 'coluta18', 'coluta19']
        badChips = badCOLUTAs+badLAUROCS
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
        readFromLpGBT(int(chip.i2cAddress, 2), 0x03c, 1, ICEC_CHANNEL=0)


    def showError(self, message):
        """Error message method. Called by numerous dependencies."""
        errorDialog = QtWidgets.QErrorMessage(self)
        errorDialog.showMessage(message)
        errorDialog.setWindowTitle("Error")


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

