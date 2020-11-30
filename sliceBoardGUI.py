
from PyQt5 import uic, QtWidgets
import os
import time
import configparser
import numpy as np
import chipConfiguration as CC
import sliceMod
import dataParser
import serialMod
import status
import configureLpGBT1213
from functools import partial
import configureLpGBT1213
from collections import OrderedDict, defaultdict
from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from flxMod import icWriteToLpGBT, ecWriteToLpGBT
from monitoring import MPLCanvas
from datetime import datetime

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
        self.testButton.clicked.connect(self.lpgbt_14_test)
        self.test3Button.clicked.connect(self.checkVoltages)
        self.test2Button.clicked.connect(self.scanClocks)

        self.initializeUSBButton.clicked.connect(self.initializeUSBISSModule)
        self.disableParityButton.clicked.connect(self.disableParity)
        self.dcdcConverterButton.clicked.connect(self.enableDCDCConverter)
        self.lpgbt12ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt12"))
        self.lpgbt13ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt13"))

        self.lpgbtI2CWriteButton.clicked.connect(self.lpgbt_manual_write)
        self.lpgbtI2CReadButton.clicked.connect(self.lpgbt_manual_read)
        self.lpgbtICWriteButton.clicked.connect(self.lpgbt_ic_write)

        #self.configureClocksButton.clicked.connect(self.configure_clocks_test)
        self.configurelpgbt12icButton.clicked.connect(self.sendUpdatedConfigurations)
        # self.lpgbt11ConfigureButton.clicked.connect(self.i2cDataLpGBT)
        self.coluta16ConfigureButton.clicked.connect(self.i2cCOLUTA)
        self.lpgbtConfigureButton.clicked.connect(self.i2cLpGBT)
       # self.laurocConfigsButton.clicked.connect(self.collectLaurocConfigs)
        #self.dataLpGBTConfigsButton.clicked.connect(self.collectDataLpgbtConfigs)
        #self.controlLpGBTConfigsButton.clicked.connect(self.collectControlLpgbtConfigs)
        #self.colutaConfigsButton.clicked.connect(self.collectColutaConfigs)

        #Configuration Buttons
        self.configureControlLpGBTButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.laurocConfigureButton.clicked.connect(self.sendUpdatedConfigurations)
        self.laurocControlConfigureButton.clicked.connect(self.i2cLauroc)
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

        # Plotting
        self.takeSamplesButton.clicked.connect(lambda: self.takeSamples())
        self.nSamplesBox.textChanged.connect(self.updateNSamples)
        self.dataDisplay = MPLCanvas(self.dataDisplayWidget,x=np.arange(2),style='r.',
                                                ylim=[0,65536],ylabel='ADC Counts')
        self.dataGridLayout.addWidget(self.dataDisplay,0,0)
        #self.displayGridLayout.addWidget(self.dataDisplay,0,0)

        self.isConnected = True
        #self.startup()
        #self.lpgbt_i2c_read()
        # self.sendConfigurationsFromLpGBT()

    def lpgbt_14_test(self):
        chip = self.chips['lpgbt14']
        reg_addr = 0xc4
        data = [0x55]
        lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(chip.i2cAddress,2)
        # while True:
            #self.sendDataLpgbtConfigs(chipName, wordCount, reg_addr, data)
            #self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, reg_addr, data)
            # writeToLpGBT(dataI2CAddr, reg_addr, data)
        writeToLpGBT(dataI2CAddr, reg_addr, data)


    def lpgbt_manual_write(self):
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        print(lpgbt)
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

        if lpgbt in ['lpgbt12', 'lpgbt13']:
            if lpgbt == 'lpgbt12':
                IC_EC = 0
            else:
                IC_EC = 1    
            if repeat == 1:
                print("Writing", int(chip.i2cAddress, 2), reg_addr, [value])
                writeToLpGBT(int(chip.i2cAddress, 2), reg_addr, [value], ICEC_CHANNEL=IC_EC )
            else:
                i = 0
                while i < repeat:
                    if (repeat - i) < 4:
                        data =  [value for i in range(repeat-i)]
                    else:
                        data = [value, value, value, value]

                    writeToLpGBT(int(chip.i2cAddress, 2), reg_addr+i, data, ICEC_CHANNEL=IC_EC)
                    i += len(data)
        elif lpgbt in ['lpgbt11', 'lpgbt14']:
            if lpgbt == 'lpgbt11':
                IC_EC = 0
            else:
                IC_EC = 1    
            i = 0
            while i < repeat:
                if (repeat - i) < 4:
                    data =  [value for i in range(repeat-i)]
                else:
                    data = [value, value, value, value]
                print("Len: ", len(data))
                ecWriteToLpGBT(int(chip.i2cAddress, 2), reg_addr+i, data, ICEC_CHANNEL=IC_EC)
                i += len(data)
        else:
            i = 0
            while i < repeat:
                if (repeat - i) < 14:
                    data =  [value for k in range(repeat-k)]
                else:
                    data = [value for j in range(0,14)]
                self.DataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, reg_addr+i, data)
                i += len(data)



    def lpgbt_i2c_read(self):
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        #lpgbt = 'lpgbt13'
        chip = self.chips[lpgbt]
        #lpgbt11Box = getattr(self, 'lpgbt11Box')
        #lpgbt12Box = getattr(self, 'lpgbt12Box')
        #lpgbt13Box = getattr(self, 'lpgbt13Box')
        #lpgbt9Box = getattr(self, 'lpgbt9Box')
        #lpgbt10Box = getattr(self, 'lpgbt10Box')

        #print(int(lpgbt11Box.isChecked()))
        #print(int(lpgbt12Box.isChecked()))

        registerBox = getattr(self, 'lpgbtregisterBox')
        valueBox = getattr(self, 'lpgbtReadLengthBox')
        #reg_addr = int(0xd7,16)
        #value = 1

        try:
            reg_addr = int(registerBox.toPlainText(),16)
            #reg_addr = int(0xd7,16)
        except:
            print("Invalid register address")
            return
        try:
            value = int(valueBox.toPlainText(),10)
            #value = 1
        except:
            print("Invalid value - must be decimal")
            return

        # if int(lpgbt12Box.isChecked()) == 1:
        #     chip = self.chips["lpgbt12"]
        # elif int(lpgbt13Box.isChecked()) == 1:
        #     chip = self.chips["lpgbt13"]
        # elif int(lpgbt11Box.isChecked()) == 1:
        #    chip = self.chips["lpgbt11"]
        # elif int(lpgbt9Box.isChecked()) == 1:
        #     chip = self.chips["lpgbt9"]
        # elif int(lpgbt10Box.isChecked()) == 1:
        #     chip = self.chips["lpgbt10"]
        # else:
        #     print("please select lpgbt 12 or 11")
        #     return

        #if (int(lpgbt9Box.isChecked()) == 1) or (int(lpgbt10Box.isChecked()) ==1):
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt15', 'lpgbt16']:
            lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
            #print("lpgbt Master is ", chip.lpgbtMaster )
            dataI2CAddr = int(chip.i2cAddress,2)
            if value >4:
                i=0
                while i < value:
                    if value - i < 4:
                        count = value -i
                    else:
                        count = 4
                    print("reading ", hex(reg_addr + i))
                    self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, reg_addr +i, count)
                    i += count
            else:
                self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, reg_addr, value)
            return            

        elif lpgbt in ['lpgbt12', 'lpgbt13']:
            if lpgbt == 'lpgbt12':
                IC_EC = 0
            else:
                IC_EC = 1
            if value > 4:
                i=0
                while i < value:
                    print("reading ", hex(reg_addr + i))
                    readFromLpGBT(int(chip.i2cAddress, 2), reg_addr + i, 4, ICEC_CHANNEL=IC_EC )
                    i += 4
            else:
                readFromLpGBT(int(chip.i2cAddress, 2), reg_addr, value, ICEC_CHANNEL=IC_EC)


    def enableDCDCConverter(self):
        chip = self.chips["lpgbt12"]

        piodirl = '00010100'
        piooutl = '00010100'
        piodrivestrengthl = '00010100'

        #data = ''.join([f'{0Xaa:08b}' for i in range(1,96)])
        data = ['00001000', piodirl, '00001000', piooutl, '00000000', '00000000', '00000000', '00000000', '00001000', piodrivestrengthl]
        dataToSend = [int(val,2) for val in data]

        writeToLpGBT(int(chip.i2cAddress, 2), 0x052, dataToSend)

        chip2 = self.chips['lpgbt13']

        piodirl = '00011100'
        piooutl = '00011100'
        piodrivestrengthl = '00011100'

        data2 = ['00000000', piodirl, '00000000', piooutl, '00000000', '00000000', '00000000', '00000000', '00000000', piodrivestrengthl]
        dataToSend2 = [int(val,2) for val in data2]

        writeToLpGBT(int(chip2.i2cAddress, 2), 0x052, dataToSend2)


    def lpgbtReset(self, lpgbt):
        chip = self.chips[lpgbt]
        if lpgbt == 'lpgbt12':
            ICEC = 0
        else:
            ICEC = 1
        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x00], ICEC_CHANNEL = ICEC)
        #time.sleep(0.2)
        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x07], ICEC_CHANNEL = ICEC)
        writeToLpGBT(int(chip.i2cAddress, 2), 0x12c, [0x00], ICEC_CHANNEL = ICEC)


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

        self.updateGUIText()


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
        writeToLpGBT(int(chip.i2cAddress, 2), 0x03c, [0x01])
        readFromLpGBT(int(chip.i2cAddress, 2), 0x03c, 1)    

    def i2cLpGBT(self):
        lpgbt = getattr(self, 'lpgbtConfigureBox').currentText()
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            self.i2cControlLpGBT(lpgbt)
        else:
            self.i2cDataLpGBT(lpgbt)

    def ControlLpGBTConfigs(self, lpgbt):
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

        self.i2cControlLpgbt(self lpgbt, sectionChunks)

    def i2cControlLpgbt(self, lpgbt, sectionChunks):
        chip = self.chips[lpgbt]
        if lpgbt[-2:] == '11' or lpgbt[-2:] == '12': 
            ICEC_CHANNEL = 0
        elif lpgbt[-2:] == '13' or lpgbt[-2:] == '14': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpGBT specified (i2cControlLpGBT)")
        print(lpgbt, ICEC_CHANNEL)

        if lpgbt in ['lpgbt11', 'lpgbt14']:
            for (register, dataBits) in sectionChunks.items():
                ecWriteToLpGBT(int(chip.i2cAddress, 2), register, dataBits, ICEC_CHANNEL=ICEC_CHANNEL)
        else:
            for (register, dataBits) in sectionChunks.items():
                writeToLpGBT(int(chip.i2cAddress, 2), register, dataBits, ICEC_CHANNEL=ICEC_CHANNEL)


    def i2cCOLUTA(self):
        #colutaName = "coluta20"
        colutaName = getattr(self, 'colutaConfigureBox').currentText()
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[colutaName].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)
        if lpgbtMaster[-2:] == '12': 
            ICEC_CHANNEL = 0
        elif lpgbtMaster[-2:] == '13': 
            ICEC_CHANNEL = 1
        else: 
            print("Invalid lpgbtMaster specified (i2cCOLUTA)")

        dataBits = self.colutaI2CWriteControl(colutaName, "ch1", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch2", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch3", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch4", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch5", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch6", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch7", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch8", broadcast=False)
        dataBits64 = [dataBits[64*i:64*(i+1)] for i in range(len(dataBits)//64)]
        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[colutaName].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[colutaName].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        print("i2cAddr", colutaI2CAddr)
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)
        print("i2cH",hex(colutaI2CAddrH))
        print("u2cL", hex(colutaI2CAddrL))
        dataBitsGlobal = self.colutaI2CWriteControl(colutaName, "global")
        dataBitsGlobal64 = [dataBitsGlobal[64*i:64*(i+1)] for i in range(len(dataBitsGlobal)//64)]
        for word in dataBits64:
            #continue

            #word = dataBits64[-1]
            #print(word)
            #while True:
            #dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            print("0x0f9:", [hex(x) for x in [0b00100000, 0x00, 0x00, 0x00, 0x0]])
            print("0x0f9:", [hex(x) for x in [*dataBits8[4:][::-1], 0x8]])
            print("0x0f9:", [hex(x) for x in [*dataBits8[:4][::-1], 0x9]])
            print("0x0f7:", [hex(x) for x in [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe]])

            # We will write 8 bytes to i2cM1Data at a time
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0xa0])
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0fd, [0x00])

            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0x01,0x02,0x03,0x04,0x08])
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0x05,0x06,0x07,0x08,0x09])

            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f8, [0x00]) i2cAddr[6:0]
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x04]) i2cAddr[9:7]
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0fd, [0x0E])
            
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
		


        for word in dataBits64:
            continue
            print("Reading back")
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

        print("Beginning writing global bits")
        counter = 1
        #word = dataBitsGlobal64[0]
        #bytesList = ['00000000', '00000000', '00000000', '00000000', '00000000',  '00000000', '00111011','00000000']
        #word = ''.join(bytesList)
        #while True:
        for word in dataBitsGlobal64[::-1]:
            # continue
            print("global bits", counter)
            print(word)
            print(len(word))
            print(hex(int(word,2)))
            #while True:
            #addrModification = 8
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]

            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            print("wrote ", [0b10100001, 0x00, 0x00, 0x00])
            #time.sleep(1)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, 4, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x0], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            print("wrote ", [*dataBits8[4:][::-1]])
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, 4, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x8], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1]], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            print("wrote", [*dataBits8[:4][::-1]])
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0f9, 4, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0x9], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            print("wrote", [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00])
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, 4, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xe], ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            #time.sleep(1)
            counter += 1

        print("Beginning reading global bits")
        counter = 1
        for _ in dataBitsGlobal64:
        #while True:
            addrModification = counter*8
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00], ICEC_CHANNEL=ICEC_CHANNEL)
            writeToLpGBT(int(lpgbtI2CAddr, 2), 0x0fd, [0xf], ICEC_CHANNEL=ICEC_CHANNEL)
            readFromLpGBT(int(lpgbtI2CAddr, 2), 0x179, 16, ICEC_CHANNEL=ICEC_CHANNEL)
            counter += 1

    def i2cDataLpGBT(self, lpgbt):
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

        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lpgbt].lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(self.chips[lpgbt].i2cAddress,2)
        print(lpgbtI2CAddr,"\t",dataI2CAddr)
       
        for (register, dataBits) in dataBits14.items():
            self.DataLpgbtWrite(int(lpgbtI2CAddr), dataI2CAddr, register, dataBits)

            #readback = self.i2cDataLpgbtRead(int(lpgbtI2CAddr), dataI2CAddr, register, len(dataBits))
            #if readback == dataBits:
            #    print("Successfully readback what was written!")
            #else:
            #    print("Readback does not agree with what was written")

    def i2cLauroc(self):
        lauroc = getattr(self, 'laurocConfigureBox').currentText()
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[lauroc].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)
        if lpgbtMaster == "lpgbt12":
            ICEC = 0
        else:
            ICEC = 1

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

        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)
        for iSection in range(0, len(chip)):
            startReg = int(chipList[iSection].address, 0)
            data = sectionChunks[startReg]
            print("writing", hex(data), "to", hex(startReg))
            #writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0b10000001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), startReg, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC)
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC)
            writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC)
            # print("reading back")
            # writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), startReg, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC)
            # writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2], ICEC_CHANNEL = ICEC)
            # writeToLpGBT(lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), 0x00, 0x00, 0x00, 0x00, 0x3], ICEC_CHANNEL = ICEC)
            # readFromLpGBT(lpgbtI2CAddr, 0x178, 1, ICEC_CHANNEL = ICEC)

    def i2cDataLpgbtWrite(self, lpgbtI2CAddr, dataI2CAddr, register, data):
            if lpgbtI2CAddr == 0x72: 
                ICEC_CHANNEL = 0
            elif lpgbtI2CAddr == 0x73: 
                ICEC_CHANNEL = 1
                # self.configureLpGBT(int(chip.i2cAddress, 2), register, dataBits)
                # writeToLpGBT(int(chip.i2cAddress, 2), register, dataBits)
                # writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), register, dataBits)
                #readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), register, len(dataBits))
            else: 
                print("Invalid lpgbtMaster specified (i2cDataLpgbtWrite)")
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
            readFromLpGBT(lpgbtI2CAddr, 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
            i2cTransactionFinished = False
            counter = 0
            while not i2cTransactionFinished:
                bit = readFromLpGBT(lpgbtI2CAddr, 0x176, 1, ICEC_CHANNEL=ICEC_CHANNEL)
                print("bit: ", bit)
                if bit[0] == 4:
                    i2cTransactionFinished = True
                time.sleep(0.1)
                if counter == 10:
                    print("I2C Transaction Failed after 1s")
                    break
                counter += 1

    def i2cDataLpgbtRead(self, lpgbtI2CAddr, dataI2CAddr, register, nBytes):
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
            # readFromLpGBT(lpgbtI2CAddr, 0x179, 16)
            #print("Read here:")
            ReverseReadback = readFromLpGBT(lpgbtI2CAddr, 0x189 - nBytes, nBytes, ICEC_CHANNEL=ICEC_CHANNEL)
            print("Read: ", [hex(val) for val in ReverseReadback[::-1]])
            return ReverseReadback[::-1]


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
        for (chipName, chipConfig) in self.chips.items():
            updates = {}
            for (sectionName, section) in chipConfig.items():
                #for (settingName, setting) in section.items():
                #category = configurations[categoryName]
                #if sectionName not in ['piodirh','piodirl']:
                #    continue
                if section.updated:
                    addr = int(self.chips[chipName][sectionName].address,0)
                    data =  self.chips[chipName][sectionName].bits
                    updates[addr] = [sectionName,data]
                    print('Updating',chipName,sectionName,sep=' ')
                    section.updated = False
                #if True:

            #Sort into groups of addresses with no more than 14 registers inbetween
            orderedUpdates = OrderedDict(sorted(updates.items(), key = lambda t:t[0]))
            addrs = orderedUpdates.keys()
            addrGroups, last = [[]], None
            for addr in addrs:
                if last is None or abs(last - addr) <= 14:
                    addrGroups[-1].append(addr)
                else:
                    addrGroups.append([addr])
                last = addr
            # print(addrGroups)
            for addrGroup in addrGroups:
                firstAddr = f'{addrGroup[0]:012b}'
                currentAddr = addrGroup[0]
                finalAddr = addrGroup[-1]
                dataToSend = ''
                wordCount = 0
                while currentAddr <= finalAddr:
                    try:
                        dataToSend += orderedUpdates[currentAddr][1]
                    except KeyError:
                        dataToSend += "00000000"
                    currentAddr += 1
                    wordCount += 1
                #print('sending: ', chipName, firstAddr, dataToSend)
                if 'lpgbt13' == chipName: #or 'lpgbt13' == chipName:
                    self.sendControlLpgbtConfigs(chipName, wordCount, firstAddr, dataToSend)
                    #self.sendControlLpgbtConfigsTest(chipName, wordCount, firstAddr, dataToSend)
                #elif 'lpgbt' in chipName:
                #    self.sendDataLpGBTConfigs(chipName, wordCount, firstAddr, dataToSend)
                #elif 'lauroc' in chipName:
                #    self.sendLAUROCConfigs(chipName, wordCount, firstAddr, dataToSend)
                #elif 'coluta' in chipName:
                #    self.sendCOLUTAConfigs(chipName, wordCount, dataToSend)
                else:
                    print('ChipName Not recognized: ', chipName)

                    # # if self.debug:
                    # print('Updating',chipName,sectionName,sep=' ')
                    # if 'lauroc' in chipName:
                    #     #self.configureLAUROC()
                    #     print(self.chips[chipName][sectionName].bits)
                    #     #category.updated = False
                    # elif 'coluta' in chipName:
                    #     #self.configureCOLUTA()
                    #     #category.sendUpdatedConfiguration(category.isI2C)
                    #     #category.updated = False
                    #     print(self.chips[chipName][sectionName].bits)
                    # elif 'lpgbt13' == chipName or 'lpgbt12' == chipName:
                    #     #self.configureControllpGBT()
                    #     print(self.chips[chipName][sectionName].bits)
                    #     #category.updated = False
                    # elif 'lpgbt' in chipName:
                    #     #self.configureDatalpGBT()
                    #     print(self.chips[chipName][sectionName].bits)
                    #     #category.updated = False
                    # else:
                    #     # should send LAUROC configurations
                    #     print(f'Chip name not found : {chipName}')
                    #     continue
                    #     # category.sendUpdatedConfiguration(category.isI2C)
                    # section.updated = False


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


    def takeSamplesSimple(self):
        """Read and store output from VTRx+ 3 or 6"""
        if not self.isConnected and not self.pArgs.no_connect:
            self.showError("Board is not connected")
            return

        print("Reading data")
        dataByteArray = self.fifoAReadData("45")

        if self.pArgs.no_connect: return

        dataString = sliceMod.byteArrayToString(dataByteArray)
        dataStringChunks32 = "\n".join([dataString[i:i+32] for i in range(0, len(dataString), 32)])
        dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)])
        #print(dataStringChunks16)
        if self.pArgs.debug: print(dataStringChunks16)

        return dataString
        #self.ODP.parseData(self.nSamples, dataString)
        #self.ODP.writeDataToFile()

    def takeSamples(self,doDraw=True):
        """Read and store output data from LpGBT buffer"""

        doFFT = self.doFFTBox.isChecked()
        #saveHDF5 = self.saveHDF5Box.isChecked()
        csv = self.saveCSVBox.isChecked()
        # Take data and read from the FPGA
        if not self.isConnected: #and not self.pOptions.no_connect:
            self.showError('Chip is not connected.')
            return
        #self.updateStatusBar('Taking data')
        self.measurementTime = datetime.now().strftime("%y_%m_%d_%H_%M_%S.%f")
        
        # Read the data
        print("Reading data")
        dataByteArray = self.fifoAReadData("45")

        #if self.pOptions.no_connect: return
        #self.updateStatusBar('Writing data')
        # Display the data on the GUI window in groups of 32 bits and in groups on 16 bits on the 
        # terminal window for Jaro
        dataString = sliceMod.byteArrayToString(dataByteArray)
        dataStringByteChunks = "\n".join([dataString[i:i+32] for i in range(0,len(dataString),32)])
        dataStringByteChunks16 = "\n".join([dataString[i:i+16] for i in range(0,len(dataString),16)])
        #if self.debug: print(dataStringByteChunks16)
        #sectionLen = len(dataString)//self.nSamples
        sectionLen = 256
        print(len(dataString))
        print(sectionLen*self.nSamples)
        #print(sectionLen)
        repeats = [dataString[i:i+sectionLen] for i in range (0, len(dataString), sectionLen)]
        #print(repeats)
        dataStringCh78 = "\n".join([chunk[192:224] for chunk in repeats])
        #for chunk in repeats:
        #  print(chunk[192:224])

        with open("ch78_4000_samples.txt", "w") as f:
            f.write(dataStringCh78)
        #self.controlTextBox.setPlainText(dataStringCh78)
        self.controlTextBox.setPlainText(dataStringByteChunks)

        #self.ODP.parseData('coluta', self.nSamples,dataString)
        self.ODP.parseData(self.nSamples,dataString)
        #self.ODP.writeDataToFile(writeHDF5File=saveHDF5,writeCSVFile=csv)

        plotChip = self.plotChipBox.currentText().lower()
        plotChannel = self.plotChannelBox.currentText()
        channelsRead = getattr(self.ODP,plotChip).getSetting('data_channels')
        print("channels", channelsRead)
        # channelsRead = ['channel2','channel1']

        self.dataDisplay.resetData()
        #self.fftDisplay.resetData()

        if doDraw and plotChannel in channelsRead:
            print("Drawing")
            decimalDict = getattr(self.ODP,plotChip+'DecimalDict')
            adcData = decimalDict[plotChannel]
            self.dataDisplay.updateFigure(adcData,np.arange(len(adcData)))
            if doFFT:
                freq,psd,QA = colutaMod.doFFT(self,adcData)
                QAList = [plotChannel.upper(),
                          'ENOB: {:2f}'.format(QA['ENOB']),
                          'SNR: {:2f} dB'.format(QA['SNR']),
                          'SFDR: {:2f} dB'.format(QA['SFDR']),
                          'SINAD: {:2f} dB'.format(QA['SINAD'])]
                QAStr = '\n'.join(QAList)
                self.controlTextBox.setPlainText(QAStr)
                #self.fftDisplay.updateFigure(psd,freq)

        #self.updateStatusBar()

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

    def checkVoltages(self):
        chip = self.chips["lpgbt13"]
        adcselect = 0x111
        adcconfig = 0x113 
        vrefcntr = 0x01c
        adcstatusH = 0x1b8
        adcstatusL = 0x1b9
        vref = 0.9
        #FOR TEMP - CURDACChn, CURDACEnable, CURDACSelect[7:0]
        # configure input multiplexers to measure ADC0 in signle ended modePins
        # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
        # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
        writeToLpGBT(int(chip.i2cAddress, 2), adcselect, [int('00111111', 2)])

        # enable ADC core and set gain of the differential amplifier
        writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)])

        # enable internal voltage reference
        writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('10000000', 2)])

        # wait until voltage reference is stable
        time.sleep(0.01)

        # start ADC convertion
        writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('10000100', 2)])
        status = False
        attempt = 0
        while not status and attempt < 10:
            readback = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusH, 1)
            status = readback[0] & 0x40
            attempt += 1
            if attempt == 10:
                print("Failed to read voltage after 10 attemps - giving up")

        adcValueH = readback[0]
        adcValueL = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusL, 1)[0]
        print("ADC Value H", adcValueH, "ADC Value L", adcValueL)

        # clear the convert bit to finish the conversion cycle
        writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)])

        # if the ADC is not longer needed you may power-down the ADC core and the reference voltage generator
        writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('00000000', 2)])
        writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000000', 2)])


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


## Helper functions
def u16_to_bytes(val):
    byte1 = (val >> 8) & 0xff
    byte0 = (val >> 0) & 0xff
    return byte1, byte0

def makeI2CSubData(dataBits,wrFlag,readBackMux,subAddress,adcSelect):
    '''Combines the control bits and adds them to the internal address'''
    # {{dataBitsSubset}, {wrFlag,readBackMux,subAddress}, {adcSelect}}, pad with zeros
    return (dataBits+wrFlag+readBackMux+subAddress+adcSelect).zfill(64)

def makeWishboneCommand(dataBits,i2cWR,STP,counter,tenBitMode,chipIdHi,wrBit,chipIDLo,address):
    '''Arrange bits in the Wishbone standard order.'''
    wbTerminator = '00000000'
    wbByte0 = i2cWR+STP+counter # 5a
    wbByte1 = tenBitMode+chipIdHi+wrBit # f0
    wbByte2 = chipIDLo+address
    bitsToSend = wbTerminator+dataBits+wbByte2+wbByte1+wbByte0
    return bitsToSend

def attemptWrite(coluta,dataBitsToSend,i2cAddress,address):
    nDataBytes = int(len(dataBitsToSend)/8)+2 # should be 10
    nDataBytesStr = '{0:04b}'.format(nDataBytes)
    i2cAddressStr = '{0:06b}'.format(i2cAddress)
    bitsToSend = makeWishboneCommand(dataBitsToSend,'010','1',nDataBytesStr,'11110','00','0','01',i2cAddressStr)
    #nByte = int(len(bitsToSend)/8) # should be 12
    #coluta.status.send(coluta)
    #coluta.status.sendFifoAOperation(coluta,1,nByte,address)
    #serialResult = serialMod.writeToChip(coluta,'A',bitsToSend)
    #coluta.status.sendI2Ccommand(coluta)

    return bitsToSend

