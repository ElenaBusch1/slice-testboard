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
from configureLpGBT1213 import writeToLpGBT, readFromLpGBT
from functools import partial
import configureLpGBT1213
from collections import OrderedDict, defaultdict
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
        self.description = 'SLICEBOARDAB'

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
        i2cPortFound = configureLpGBT1213.findPort()
        self.i2cPort = configureLpGBT1213.setupSerial(i2cPortFound)

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
        #self.lpgbtICWriteButton.clicked.connect(self.lpgbt_write)
        #self.testButton.clicked.connect(self.silly_reg_test)
        # self.testButton.clicked.connect(lambda: self.isLinkReady("45"))
        #self.testButton.clicked.connect(self.lpgbt45readBack)
        #self.testButton.clicked.connect(lambda: self.i2cLauroc("lauroc20"))
        self.testButton.clicked.connect(lambda: self.i2cLauroc())
        #self.testButton.clicked.connect(self.test_lpgbt9config_loop)
        #self.test2Button.clicked.connect(self.configure_clocks_test)
        #self.test2Button.clicked.connect(self.i2cCOLUTA)
        #self.test2Button.clicked.connect(self.i2cControlLpGBT)
        # self.test2Button.clicked.connect(self.configure_clocks_test)
        # self.test2Button.clicked.connect(lambda: self.isLinkReady("45"))
        self.test3Button.clicked.connect(self.write_uplink_test)
        self.test2Button.clicked.connect(self.scanClocks)
        #self.test2Button.clicked.connect(self.lpgbt_test)

        self.initializeUSBButton.clicked.connect(self.initializeUSBISSModule)
        self.disableParityButton.clicked.connect(self.disableParity)
        self.dcdcConverterButton.clicked.connect(self.enableDCDCConverter)
        self.lpgbt12ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt12"))
        self.lpgbt13ResetButton.clicked.connect(lambda: self.lpgbtReset("lpgbt13"))

        self.lpgbtI2CWriteButton.clicked.connect(self.lpgbt_i2c_write)
        self.lpgbtI2CReadButton.clicked.connect(self.lpgbt_i2c_read)
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

        self.isConnected = False
        self.startup()

        # self.sendConfigurationsFromLpGBT()


    def lpgbt_ic_write(self):
        chipName = getattr(self, 'lpgbtSelectBox').currentText()
        
        registerBox = getattr(self, 'lpgbtregisterBox')
        valueBox = getattr(self, 'lpgbtvalueBox')
        repeatBox = getattr(self, 'lpgbtReadLengthBox')

        try:
            reg_addr_hex = int(registerBox.toPlainText(),16)
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
        
        reg_addr = f'{reg_addr_hex:012b}'      
        reg_val = f'{value:08b}'
        if chipName == 'lpgbt13':
            controlLpGBTbit = 1
        else:
            controlLpGBTbit = 0
        
        data = ''.join([reg_val for i in range(0,repeat)])

        #dataBitsToSend = f'00{controlLpGBTbit}{reg_addr[:5]}'
        #dataBitsToSend += f'{reg_addr[5:]}0'
        wordCount = len(data)//8
        #wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        #dataBitsToSend += f'{wordCountByte1:08b}' + f'{wordCountByte2:08b}'
        #dataBitsToSend += data

        #for word in [dataBitsToSend[i:i+8] for i in range(0,len(dataBitsToSend),8)]:
        #    print(word)
        if chipName in ['lpgbt12', 'lpgbt13']:
            self.sendControlLpgbtConfigs(chipName, wordCount, reg_addr, data)
        else:
            self.sendDataLpgbtConfigs(chipName, wordCount, reg_addr_hex, data)
        #self.LpGBT_IC_write(dataBitsToSend)
        #except:
        #    print("IC write to lpGBT failed")
        #    return


    def lpgbt_i2c_write(self):
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
        print(lpgbt)
        #lpgbt9Box = getattr(self, 'lpgbt9Box')
        #lpgbt10Box = getattr(self, 'lpgbt10Box')        
        #lpgbt11Box = getattr(self, 'lpgbt11Box')
        #lpgbt12Box = getattr(self, 'lpgbt12Box')
        chip = self.chips[lpgbt]

        registerBox = getattr(self, 'lpgbtregisterBox')
        valueBox = getattr(self, 'lpgbtvalueBox')
        repeatBox = getattr(self, 'lpgbtReadLengthBox')

        try:
            reg_addr_hex = int(registerBox.toPlainText(),16)
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


        #if lpgbt12Box.isChecked():
        #    chip = self.chips["lpgbt12"]
        #elif lpgbt11Box.isChecked():
        #    chip = self.chips["lpgbt11"]
        #elif lpgbt10Box.isChecked():
        #    chip = self.chips["lpgbt10"]
        #elif lpgbt9Box.isChecked():
        #    chip = self.chips["lpgbt9"]
        #else:
        #    print("please select an lpgbt")
        #    return 

        lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
        print("lpgbt Master is ", chip.lpgbtMaster )
        dataI2CAddr = int(chip.i2cAddress,2)

        if lpgbt in ['lpgbt12', 'lpgbt13', 'lpgbt14', 'lpgbt11']:    
            if repeat == 1:
                writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), reg_addr_hex, [value])
            else:
                i = 0
                while i < repeat:
                    if (repeat - i) < 4:
                        data =  [value for i in range(repeat-i)]
                    else:
                        data = [value, value, value, value]

                    writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), reg_addr_hex+i, data)
                    i += len(data)
        else:
            if repeat == 1:
                self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, reg_addr_hex, [value])
            else:
                i = 0
                while i < repeat:
                    if (repeat - i) < 14:
                        data =  [value for k in range(repeat-k)]
                    else:
                        data = [value for j in range(0,14)]
                    self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, reg_addr_hex, data)
                    i += len(data)



    def lpgbt_i2c_read(self):
        lpgbt = getattr(self, 'lpgbtSelectBox').currentText()
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

        try:
            reg_addr_hex = int(registerBox.toPlainText(),16)
        except:
            print("Invalid register address")
            return
        try:
            value = int(valueBox.toPlainText(),10)
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
            if value >16:
                i=0
                while i < value:
                    if value - i < 16:
                        count = value -i
                    else:
                        count = 16
                    print("reading ", hex(reg_addr_hex + i))
                    self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, reg_addr_hex +i, count)
                    i += count
            else:
                self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, reg_addr_hex, value)
            return            

        else:
            if value > 16:
                i=0
                while i < value:
                    print("reading ", hex(reg_addr_hex + i))
                    readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), reg_addr_hex + i, 16)
                    i += 16
            else:
                readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), reg_addr_hex, value)


    def enableDCDCConverter(self):
        chip = self.chips["lpgbt12"]

        piodirl = '00010100'
        piooutl = '00010100'
        piodrivestrengthl = '00010100'

        #data = ''.join([f'{0Xaa:08b}' for i in range(1,96)])
        data = ['00001000', piodirl, '00001000', piooutl, '00000000', '00000000', '00000000', '00000000', '00001000', piodrivestrengthl]
        dataToSend = [int(val,2) for val in data]

        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x052, dataToSend)

        chip2 = self.chips['lpgbt13']

        piodirl = '00011100'
        piooutl = '00011100'
        piodrivestrengthl = '00011100'

        data2 = ['00000000', piodirl, '00000000', piooutl, '00000000', '00000000', '00000000', '00000000', '00000000', piodrivestrengthl]
        dataToSend2 = [int(val,2) for val in data2]

        writeToLpGBT(self.i2cPort, int(chip2.i2cAddress, 2), 0x052, dataToSend2)


    def lpgbtReset(self, lpgbt):
        chip = self.chips[lpgbt]
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x07])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])


    def write_uplink_test(self):

        chip = self.chips['lpgbt14']
        configureLpGBT1213.uplinkDataTest(self.i2cPort, int(chip.i2cAddress, 2))


        # dummy = f'{0XE0:08b}'

        # first_reg = f'{0x118:012b}'
        # dataBitsToSend = f'000{first_reg[:5]}'
        # dataBitsToSend += f'{first_reg[5:]}0'  

        # #data = ''.join(['00000000', '00000000', '00000000', '00000000', '00000000', '00000000', '00000001', '00000010', '00000011', '00000100'])
        # dataValues = [0x0c, 0x24, 0x24, 0x24, 0x04, 0xff]
        # data = ''.join([f'{val:08b}' for val in dataValues])
        # #data = '00000111'
        # #data = f'{}
        # #data += '00000000'
        # wordCount = len(data)//8
        # #wordCount = len(data)//8

        # wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        # dataBitsToSend += f'{wordCountByte1:08b}'
        # dataBitsToSend += f'{wordCountByte2:08b}'
        # dataBitsToSend += data  

        # self.LpGBT_IC_write(dataBitsToSend)        

        # sec_reg = f'{0x121:012b}'
        # dataBitsToSend2 = f'000{sec_reg[:5]}'
        # dataBitsToSend2 += f'{sec_reg[5:]}0'  

        # data2 = '00000001'

        # wordCount2 = len(data2)
        # wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount2)
        # dataBitsToSend2 += f'{wordCountByte1:08b}'
        # dataBitsToSend2 += f'{wordCountByte2:08b}'
        # dataBitsToSend2 += data2  

    def colutaRegWriteTest(self) :

        chip = self.chips["lpgbt13"]
        configureLpGBT1213.colutaRegWriteTest(self.i2cPort, int(chip.i2cAddress, 2))
        #while True:
        #    self.i2cCOLUTA()

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


    def sendCOLUTAConfigs(self, chipName, wordCount, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('coluta') == -1:
            return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        i2cM = f'{int(chipConfig.i2cMaster):02b}'
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'
        i2cAddr = '0'+chipConfig.i2cAddress
        #header
        dataBitsToSend = f'{chipType}{controlLpGBTbit}{i2cM}{i2cAddr[:3]}'
        dataBitsToSend += f'{i2cAddr[3:11]}0'
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'

        ## This is not correct!! need
        dataBitsToSend += dataBits
        print('Sending:')
        for word in [dataBitsToSend[8*i:8*(i+1)] for i in range(len(dataBitsToSend)//8)]:
            print(word)
        #self.LpGBT_IC_write(i2cAddr, dataBitsToSend)



    def sendLAUROCConfigs(self, chipName, wordCount, registerAddr, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('lauroc') == -1:
            return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        i2cM = f'{int(chipConfig.i2cMaster):02b}'
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'
        i2cAddr = '000'+ chipConfig.i2cAddress
        dataBitsToSend = ''
        dataBitsToSend += f'{chipType}{controlLpGBTbit}{i2cM}{i2cAddr[:3]}'
        dataBitsToSend += f'{i2cAddr[3:]}0'

        wordCount += 1
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)

        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'
        dataBitsToSend += f'{registerAddr:08b}'
        dataBitsToSend += dataBits

        self.LpGBT_IC_write(dataBitsToSend)



    def sendDataLpgbtConfigs(self, chipName, wordCount, registerAddr, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('lpgbt') == -1:
            return
        if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
            return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        try:
            i2cM = f'{int(chipConfig.i2cMaster):02b}'
        except:
            i2cM = 'EC'
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'

        dataBitsToSend = f'{chipType}{controlLpGBTbit}{i2cM}000'
        dataBitsToSend += f'{chipConfig.i2cAddress}0'

        wordCount += 2
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}{wordCountByte2:08b}'

        addr2, addr1 = u16_to_bytes(registerAddr)
        dataBitsToSend += f'{addr1:08b}{addr2:08b}'

        dataBitsToSend += dataBits

        for word in [dataBitsToSend[i:i+8] for i in range(0,len(dataBitsToSend), 8)]:
            print(word, hex(int(word,2)))

        self.LpGBT_IC_write(dataBitsToSend)


    def sendControlLpgbtConfigs(self, chipName, totalWordCount, first_reg_addr, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('lpgbt') == -1:
            return
        #if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
        #    return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'

        #dataBitsNoBE = dataBits[:992] 
        registerAddr = first_reg_addr
        #print(hex(int(registerAddr)))
        #subDataBits = dataBlocks[i]
        wordCount = len(dataBits)//8

        dataBitsToSend = f'{chipType}{controlLpGBTbit}{registerAddr[:5]}'
        #print("header 1: ", dataBitsToSend)
        dataBitsToSend += f'{registerAddr[5:]}0'
        print("address: ", hex(int(first_reg_addr, 2)))

        #wordCount += 2
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}{wordCountByte2:08b}'

        dataBitsToSend += dataBits

        print("sending:")
        j = 0
        for word in [dataBitsToSend[i:i+8] for i in range(0,len(dataBitsToSend),8)]:
            print(hex(int(registerAddr,2)+(j-4)), hex(int(word, 2)))
            j += 1

        self.LpGBT_IC_write(dataBitsToSend)


    def sendControlLpgbtConfigsTest(self, chipName, totalWordCount, regAddr, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('lpgbt') == -1:
            return
        #if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
        #    return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'

        first_reg = 0x00 
        last_reg = 0x7d
        dataBitsSection = dataBits[first_reg*8:last_reg*8] 
        registerAddr = regAddr
        if (first_reg != int(regAddr, 2)):
            first_reg = int(regAddr,2)
            dataBitsSection = dataBits

        #print(hex(int(registerAddr)))
        #subDataBits = dataBlocks[i]
        wordCount = len(dataBitsSection)//8

        dataBitsToSend = f'{chipType}{controlLpGBTbit}{registerAddr[:5]}'
        #print("header 1: ", dataBitsToSend)
        dataBitsToSend += f'{registerAddr[5:]}0'
        print("Writing to reg", hex(first_reg), "through", hex(last_reg))

        #wordCount += 2
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}{wordCountByte2:08b}'

        dataBitsToSend += dataBitsSection

        print("sending:")
        j = 0
        for word in [dataBitsToSend[i:i+8] for i in range(0,len(dataBitsToSend),8)]:
            print(hex(int(registerAddr,2)+(j-4)), hex(int(word, 2)), word)
            j += 1

        self.LpGBT_IC_write(dataBitsToSend)


    def startup(self):
        """Runs the standard board startup / connection routine"""
        if self.pArgs.no_connect:
            pass
        else:
            # Real startup routine when board is connected
            # Find the ports and store the names
            portDict = serialMod.findPorts(self)
            # self.port36, self.port45 = portDict['AB46BJOXA'], portDict['AB470WYIA']
            self.port45 = portDict['AB46BJOXA']
            # Set up the serial connection to each port, pause, and test
            # self.serial36, self.serial45 = serialMod.setupSerials(self)
            self.serial45 = serialMod.setupSerials(self)
            time.sleep(0.01)
            self.handshake()
            # Reset the status bits to zero, then reset FPGAs
            # self.status36.initializeUSB()
            # self.status36.send()
            # self.status36.sendSoftwareReset()
            self.status45.initializeUSB()
            self.status45.send()
            self.status45.sendSoftwareReset()


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
            #if chip == 'lpgbt12' or chip == 'lpgbt13' or chip == 'lpgbt9' or chip == 'lpgbt15':
            if isinstance(box, QtWidgets.QCheckBox):
                if int(pin) < 8:
                    for sectionName in sectionNamesL:
                        settingName = sectionName[:-1] + pin
                        #sectionName = 'piodirl'
                        #settingName = 'piodir' + pin
                        #print('updating ' + settingName)
                        box.stateChanged.connect(partial(self.updateConfigurations, boxName, chip, sectionName, settingName))
                else:
                    for sectionName in sectionNamesH:
                        settingName = sectionName[:-1] + pin
                        #sectionName = 'piodirl'
                        #settingName = 'piodir' + pin
                        #print('updating ' + settingName)
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
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x03c, [0x01])
        readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x03c, 1)    

    def i2cLpGBT(self):
        lpgbt = getattr(self, 'lpgbtConfigureBox').currentText()
        if lpgbt in ['lpgbt11', 'lpgbt12', 'lpgbt13', 'lpgbt14']:
            self.i2cControlLpGBT(lpgbt)
        else:
            self.i2cDataLpGBT(lpgbt)

    def i2cControlLpGBT(self, lpgbt):
        chip = self.chips[lpgbt]
        chipList = list(chip.values())
        sectionChunks = defaultdict(list)
        for iSection in range(0, len(chip), 13):
            startReg = int(chipList[iSection].address, 0)
            for i in range(13):
                try:
                    bits = int(chipList[iSection+i].bits, 2)
                except IndexError:
                    bits = 0
                sectionChunks[startReg].append(bits)

        # Initialize USB-ISS Module
        # writeMessage = [0x5a, 0x01]
        # configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        # configureLpGBT1213.readFromUSBISS(self.i2cPort)

        # writeMessage = [0x5a, 0x03]
        # configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        # configureLpGBT1213.readFromUSBISS(self.i2cPort)

        # writeMessage = [0x5a, 0x02, 0x40, 0x01, 0x37]
        # configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        # configureLpGBT1213.readFromUSBISS(self.i2cPort)

        # # Check for existence of device with giben i2c address
        # writeMessage = [0x58, int(chip.i2cAddress, 2) << 1]
        # # # writeMessage = [0x58, 0xd0]
        # configureLpGBT1213.writeToUSBISS(self.i2cPort, writeMessage)
        # configureLpGBT1213.readFromUSBISS(self.i2cPort)

        for (register, dataBits) in sectionChunks.items():
            # dataBitsStrings = [f"{dataBit:02x}" for dataBit in dataBits]
            # print(f"{register:03x}:", dataBitsStrings)
            configureLpGBT1213.configureLpGBT(self.i2cPort, int(chip.i2cAddress, 2), register, dataBits)
            # writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), register, dataBits)
            #readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), register, len(dataBits))


    def i2cCOLUTA(self):
        #colutaName = "coluta20"
        colutaName = getattr(self, 'colutaConfigureBox').currentText()
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[colutaName].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

        #dataBits = self.colutaI2CWriteControl(colutaName, "ch1", broadcast=True)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch2", broadcast=True)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch3", broadcast=False)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch4", broadcast=False)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch5", broadcast=True)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch6", broadcast=True)
        dataBits = self.colutaI2CWriteControl(colutaName, "ch7", broadcast=False)
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
            

            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])

        for word in dataBits64:
            continue
            print("Reading back")
            readBackBits = '01' + word[-14:]
            readBackBits = readBackBits.zfill(64)
            readBackBits8 = [int(readBackBits[8*i:8*(i+1)], 2) for i in range(len(readBackBits)//8)]
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*readBackBits8[:4][::-1], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
 
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xf])
            readFromLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x179, 16)


        print("Beginning writing global bits")
        counter = 1
        #word = dataBitsGlobal64[0]
        #bytesList = ['00000000', '00000000', '00000000', '00000000', '00000000',  '00000000', '00111011','00000000']
        #word = ''.join(bytesList)
        #while True:
        for word in dataBitsGlobal64[::-1]:
            # continue
            # print("global bits", counter)
            print(word)
            print(len(word))
            #while True:
            #addrModification = 8
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00, 0x00, 0x00, 0xe])
            counter += 1

        print("Beginning reading global bits")
        counter = 1
        for _ in dataBitsGlobal64:
        #while True:
            addrModification = counter*8
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00, 0x00, 0x00, 0xf])
            readFromLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x179, 16)
            counter += 1

    def sendInversionBits(self, clock640, colutaName):
        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[colutaName].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[colutaName].i2cAddress
        colutaI2CAddr = "".join(colutaI2CAddr.split("_")[1:2])
        colutaI2CAddrH = int(f'00000{colutaI2CAddr[:3]}', 2)
        colutaI2CAddrL = int(f'0{colutaI2CAddr[-1]}000000', 2)

        binary = f'{clock640:04b}'
        inv640 = binary[0]
        delay640 = binary[1:] 
        self.chips[colutaName].setConfiguration("global", "INV640", inv640)
        print(f"Updated {colutaName} global, INV640: {inv640}")
        self.chips[colutaName].setConfiguration("global", "DELAY640", delay640)
        print(f"Updated {colutaName} global, DELAY640: {delay640}")

        dataBitsGlobal = self.colutaI2CWriteControl(colutaName, "global")
        dataBitsGlobal64 = [dataBitsGlobal[64*i:64*(i+1)] for i in range(len(dataBitsGlobal)//64)]

        counter = 1
        for word in dataBitsGlobal64[::-1]:
            print(word)
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10100001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1], 0x9])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL + addrModification, 0x00, 0x00, 0x00, 0x00, 0xe])
            counter += 1


    def i2cDataLpGBT(self, lpgbt):
        print("Resetting lpgbt master control")
        lpgbtMaster = "lpgbt"+self.chips[lpgbt].lpgbtMaster
        self.lpgbtReset(lpgbtMaster)

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
       
        # Write the clocks
        #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x062, [dataI2CAddr, 0x21])
        #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x065, [dataI2CAddr, 0x025])
        for (register, dataBits) in dataBits14.items():
            # regH, regL = u16_to_bytes(register)
            # # We will write 16 bytes to i2cM1Data at a time
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b11000001, 0x00, 0x00, 0x00, 0x0])
            # # Write 2 byte register address, then 14 bytes of configuration
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [regL, regH, *dataBits[:2], 0x8])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits[2:6], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits[6:10], 0xa])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits[10:], 0xb])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xc])
            self.i2cDataLpgbtWrite(int(lpgbtI2CAddr), dataI2CAddr, register, dataBits)

            #readback = self.i2cDataLpgbtRead(int(lpgbtI2CAddr), dataI2CAddr, register, len(dataBits))
            #if readback == dataBits:
            #    print("Successfully readback what was written!")
            #else:
            #    print("Readback does not agree with what was written")
            # # We will write 2 bytes to the data lpGBT
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10001000, 0x00, 0x00, 0x00, 0x0])
            # # Write 2 byte register address
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [regL, regH, 0x8])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xc])
            # # We will read 14 bytes from the data lpGBT
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b10001000, 0x00, 0x00, 0x00, 0x0])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xd])
            # readFromLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x17b, 14)

    def i2cLauroc(self):
        lauroc = getattr(self, 'laurocConfigureBox').currentText()
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

        lpgbtI2CAddr = int(self.chips["lpgbt"+self.chips[lauroc].lpgbtMaster].i2cAddress,2)
        laurocI2CAddr = int(self.chips[lauroc].i2cAddress[:4],2)
        for iSection in range(0, len(chip)):
            startReg = int(chipList[iSection].address, 0)
            data = sectionChunks[startReg]
            print("writing", hex(data), "to", hex(startReg))
            #writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0b10000001, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), startReg, 0x00, 0x00, 0x00, 0x2])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), data, 0x00, 0x00, 0x00, 0x2])
            print("reading back")
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}000',2), startReg, 0x00, 0x00, 0x00, 0x2])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}001',2), 0, 0x00, 0x00, 0x00, 0x2])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [int(f'0{laurocI2CAddr:04b}010',2), 0x00, 0x00, 0x00, 0x00, 0x3])
            readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x178, 1)


    def i2cDataLpgbtWrite(self, lpgbtI2CAddr, dataI2CAddr, register, data):
            print("Writing", [hex(byte) for byte in data], "to register ", hex(register))
            #print("Data ", [hex(dataWord) for dataWord in data])
            regH, regL = u16_to_bytes(register)
            # We will write 16 bytes to i2cM1Data at a time
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0x80 + ((len(data)+2) << 2), 0x00, 0x00, 0x00, 0x0])
            # Write 2 byte register address, then 14 bytes of configuration
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [regL, regH, *data[:2]])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0x8])
            if len(data) > 2:
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [*data[2:6]])
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0x9])
            if len(data) > 6:    
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [*data[6:10]])
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0xa])
            if len(data) > 10:
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [*data[10:], 0xb])
                writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0xb])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xc])


    def i2cDataLpgbtRead(self, lpgbtI2CAddr, dataI2CAddr, register, nBytes):
            print("Reading register ", hex(register))
            regH, regL = u16_to_bytes(register)
            # We will write 2 bytes to the data lpGBT
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0b10001000, 0x00, 0x00, 0x00, 0x0])
            # Write 2 byte register address
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [regL, regH, 0x00, 0x00, 0x8])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xc])
            # We will read 14 bytes from the data lpGBT
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0x80 + (nBytes << 2), 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [dataI2CAddr, 0x00, 0x00, 0x00, 0x00, 0xd]) 
            # readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x179, 16)
            #print("Read here:")
            ReverseReadback = readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x189 - nBytes, nBytes)
            print("Read: ", [hex(val) for val in ReverseReadback[::-1]])
            return ReverseReadback[::-1]

    def i2cDataLpgbtWriteOneReg(self, lpgbtI2CAddr, dataI2CAddr, register, data):
            print("Writing register ", hex(register))
            print("Data ", [hex(dataWord) for dataWord in data])
            regH, regL = u16_to_bytes(register)
            # We will write 3 bytes to i2cM1Data at a time
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0x8c])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0x0])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0xf9, [regL])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0xfa, [regH])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0xfb, data)
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0x8])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f8, [dataI2CAddr])
            writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0fd, [0xc])
            # Write 2 byte register address, then 14 bytes of configuration
            # writeToLpGBT(self.i2cPort, lpgbtI2CAddr, 0x0f9, [0x2])


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
            if chipName != 'lpgbt13':
                continue
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
        sectionLen = len(dataString)//self.nSamples
        repeats = [dataString[i:i+sectionLen] for i in range (0, len(dataString), sectionLen)]
        dataStringCh78 = "\n".join([chunk[192:224] for chunk in repeats])

        self.controlTextBox.setPlainText(dataStringCh78)
        #self.controlTextBox.setPlainText(dataStringByteChunks)

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


    def scanClocks(self): 
        upper = 16

        ch1_sertest_true = '1010010000001001'
        ch2_sertest_true = '1010010000101001'
        ch3_sertest_true = '1010010001001001'
        ch4_sertest_true = '1010010001101001'
        ch5_sertest_true = '1010010010001001'
        ch6_sertest_true = '1010010010101001'
        ch7_sertest_true = '1010010011001001'
        ch8_sertest_true = '1010010011101001'

        ch1_sertest_repl = ch1_sertest_true*2
        ch2_sertest_repl = ch2_sertest_true*2
        ch3_sertest_repl = ch3_sertest_true*2
        ch4_sertest_repl = ch4_sertest_true*2
        ch5_sertest_repl = ch5_sertest_true*2
        ch6_sertest_repl = ch6_sertest_true*2
        ch7_sertest_repl = ch7_sertest_true*2
        ch8_sertest_repl = ch8_sertest_true*2
        ch1_sertest_valid = []
        ch2_sertest_valid = []
        ch3_sertest_valid = []
        ch4_sertest_valid = []
        ch5_sertest_valid = []
        ch6_sertest_valid = []
        ch7_sertest_valid = []
        ch8_sertest_valid = []
        LPGBTPhaseCh1_list = [[] for i in range(0,upper)]     # Value of correct lpGBT phase value or NaN if test signal is unstable or incorrect
        LPGBTPhaseCh2_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh3_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh4_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh5_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh6_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh7_list = [[] for i in range(0,upper)]
        LPGBTPhaseCh8_list = [[] for i in range(0,upper)]
        for idx in range(0, 16):
            ch1_sertest_valid.append(ch1_sertest_repl[idx:(16+idx)])
            ch2_sertest_valid.append(ch2_sertest_repl[idx:(16+idx)])
            ch3_sertest_valid.append(ch3_sertest_repl[idx:(16+idx)])
            ch4_sertest_valid.append(ch4_sertest_repl[idx:(16+idx)])
            ch5_sertest_valid.append(ch5_sertest_repl[idx:(16+idx)])
            ch6_sertest_valid.append(ch6_sertest_repl[idx:(16+idx)])
            ch7_sertest_valid.append(ch7_sertest_repl[idx:(16+idx)])
            ch8_sertest_valid.append(ch8_sertest_repl[idx:(16+idx)])

        lpgbt = "lpgbt16"
        coluta = "coluta20"
        chip = self.chips[lpgbt]
        lpgbtI2CAddr = int(self.chips["lpgbt"+chip.lpgbtMaster].i2cAddress,2)
        dataI2CAddr = int(self.chips[lpgbt].i2cAddress,2)

        # [EPRX30 - 0xd8 (ch1), EPRX32 - 0xda (ch2), EPRX40 - 0xdc (ch3), EPRX42 - 0xde (ch4), EPRX50 - 0xe0]
        registers = [0xd8, 0xda, 0xdc, 0xde, 0xe0, 0xe2, 0xe4, 0xe6]
        #registers = [0xe6]
        #channels = [xx,xx,0xe6]
        for delay_idx in range(0,16):
            isStableCh1_list = []      # Is serializer test signal same across all samples?
            isStableCh2_list = []
            isStableCh3_list = []
            isStableCh4_list = []
            isStableCh5_list = []
            isStableCh6_list = []
            isStableCh7_list = []
            isStableCh8_list = []
            isValidCh1_list = []       # Is serializer test signal correct (despite word shift)?
            isValidCh2_list = []
            isValidCh3_list = []
            isValidCh4_list = []
            isValidCh5_list = []
            isValidCh6_list = []
            isValidCh7_list = []
            isValidCh8_list = []

            self.sendInversionBits(delay_idx, coluta)

            for lpgbt_idx in range(0,16):
                value = (lpgbt_idx<<4)+2
                for reg in registers:
                    self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, reg, [value])
                    time.sleep(0.1)
                dataString = self.takeSamplesSimple()
                sectionLen = len(dataString)//self.nSamples
                repeats = [dataString[i:i+sectionLen] for i in range (0, len(dataString), sectionLen)]
                frame_list = [chunk[64:80] for chunk in repeats]
                ch1_binary_list = [chunk[112:128] for chunk in repeats]
                ch2_binary_list = [chunk[96:112] for chunk in repeats]
                ch4_binary_list = [chunk[128:144] for chunk in repeats]
                ch3_binary_list = [chunk[144:160] for chunk in repeats]
                ch6_binary_list = [chunk[160:176] for chunk in repeats]
                ch5_binary_list = [chunk[176:192] for chunk in repeats]
                ch8_binary_list = [chunk[192:208] for chunk in repeats]
                ch7_binary_list = [chunk[208:224] for chunk in repeats]

                ## Test if metastable out of consecutive samples
                isStableCh1 = (len(set(ch1_binary_list)) == 1)
                isStableCh2 = (len(set(ch2_binary_list)) == 1)
                isStableCh3 = (len(set(ch3_binary_list)) == 1)
                isStableCh4 = (len(set(ch4_binary_list)) == 1)
                isStableCh5 = (len(set(ch5_binary_list)) == 1)
                isStableCh6 = (len(set(ch6_binary_list)) == 1)
                isStableCh7 = (len(set(ch7_binary_list)) == 1)
                isStableCh8 = (len(set(ch8_binary_list)) == 1)
                isStableCh1_list.append(isStableCh1)
                isStableCh2_list.append(isStableCh2)
                isStableCh3_list.append(isStableCh3)
                isStableCh4_list.append(isStableCh4)
                isStableCh5_list.append(isStableCh5)
                isStableCh6_list.append(isStableCh6)
                isStableCh7_list.append(isStableCh7)
                isStableCh8_list.append(isStableCh8)
                ## Test if data output is correct
                isValidCh1 = set(ch1_binary_list).issubset(ch1_sertest_valid)
                isValidCh2 = set(ch2_binary_list).issubset(ch2_sertest_valid)
                isValidCh3 = set(ch3_binary_list).issubset(ch3_sertest_valid)
                isValidCh4 = set(ch4_binary_list).issubset(ch4_sertest_valid)
                isValidCh5 = set(ch5_binary_list).issubset(ch5_sertest_valid)
                isValidCh6 = set(ch6_binary_list).issubset(ch6_sertest_valid)
                isValidCh7 = set(ch7_binary_list).issubset(ch7_sertest_valid)
                isValidCh8 = set(ch8_binary_list).issubset(ch8_sertest_valid)
                isValidCh1_list.append(isValidCh1)
                isValidCh2_list.append(isValidCh2)
                isValidCh3_list.append(isValidCh3)
                isValidCh4_list.append(isValidCh4)
                isValidCh5_list.append(isValidCh5)
                isValidCh6_list.append(isValidCh6)
                isValidCh7_list.append(isValidCh7)
                isValidCh8_list.append(isValidCh8)
     
                 # Find correct lpGBT phase. -99 -> invalid and unstable, -88 invalid, -77 unstable
                try:
                    if isStableCh1 and isValidCh1:
                        LPGBTPhaseCh1 = ch1_sertest_valid.index(ch1_binary_list[0])
                    else:
                        LPGBTPhaseCh1 = -99
                        if isStableCh1:
                            LPGBTPhaseCh1 += 11
                        if isValidCh1:
                            LPGBTPhaseCh1 += 22
                    if isStableCh2 and isValidCh2:
                        LPGBTPhaseCh2 = ch2_sertest_valid.index(ch2_binary_list[0])
                    else:
                        LPGBTPhaseCh2 = -99
                        if isStableCh2:
                            LPGBTPhaseCh2 += 11
                        if isValidCh2:
                            LPGBTPhaseCh2 += 22
                    if isStableCh3 and isValidCh3:
                        LPGBTPhaseCh3 = ch3_sertest_valid.index(ch3_binary_list[0])
                    else:
                        LPGBTPhaseCh3 = -99
                        if isStableCh3:
                            LPGBTPhaseCh3 += 11
                        if isValidCh3:
                            LPGBTPhaseCh3 += 22
                    if isStableCh4 and isValidCh4:
                        LPGBTPhaseCh4 = ch4_sertest_valid.index(ch4_binary_list[0])
                    else:
                        LPGBTPhaseCh4 = -99
                        if isStableCh4:
                            LPGBTPhaseCh4 += 11
                        if isValidCh4:
                            LPGBTPhaseCh4 += 22
                    if isStableCh5 and isValidCh5:
                        LPGBTPhaseCh5 = ch5_sertest_valid.index(ch5_binary_list[0])
                    else:
                        LPGBTPhaseCh5 = -99
                        if isStableCh5:
                            LPGBTPhaseCh5 += 11
                        if isValidCh5:
                            LPGBTPhaseCh5 += 22
                    if isStableCh6 and isValidCh6:
                        LPGBTPhaseCh6 = ch6_sertest_valid.index(ch6_binary_list[0])
                    else:
                        LPGBTPhaseCh6 = -99
                        if isStableCh6:
                            LPGBTPhaseCh6 += 11
                        if isValidCh6:
                            LPGBTPhaseCh6 += 22
                    if isStableCh7 and isValidCh7:
                        LPGBTPhaseCh7 = ch7_sertest_valid.index(ch7_binary_list[0])
                    else:
                        LPGBTPhaseCh7 = -99
                        if isStableCh7:
                            LPGBTPhaseCh7 += 11
                        if isValidCh7:
                            LPGBTPhaseCh7 += 22
                    if isStableCh8 and isValidCh8:
                        LPGBTPhaseCh8 = ch8_sertest_valid.index(ch8_binary_list[0])
                    else:
                        LPGBTPhaseCh8 = -99
                        if isStableCh8:
                            LPGBTPhaseCh8 += 11
                        if isValidCh8:
                            LPGBTPhaseCh8 += 22
                except:
                    print('I could not synchronize with the COLUTA.  Please power cycle and restart GUI.')

                LPGBTPhaseCh1_list[delay_idx].append(LPGBTPhaseCh1)
                LPGBTPhaseCh2_list[delay_idx].append(LPGBTPhaseCh2)
                LPGBTPhaseCh3_list[delay_idx].append(LPGBTPhaseCh3)
                LPGBTPhaseCh4_list[delay_idx].append(LPGBTPhaseCh4)
                LPGBTPhaseCh5_list[delay_idx].append(LPGBTPhaseCh5)
                LPGBTPhaseCh6_list[delay_idx].append(LPGBTPhaseCh6)
                LPGBTPhaseCh7_list[delay_idx].append(LPGBTPhaseCh7)
                LPGBTPhaseCh8_list[delay_idx].append(LPGBTPhaseCh8)
        
        headers = [f'{i}\n' for i in range(0,16)]
        headers.insert(0,"xPhaseSelect -> \n INV/DELAY640 ")
        try:
            from tabulate import tabulate
            table8 = tabulate(LPGBTPhaseCh8_list, headers, showindex = "always", tablefmt="psql")
            print(table8)
        except ModuleNotFoundError:
            print('You need the tabulate package...')

        table1 = tabulate(LPGBTPhaseCh1_list, headers, showindex = "always", tablefmt="psql")
        table2 = tabulate(LPGBTPhaseCh2_list, headers, showindex = "always", tablefmt="psql")
        table3 = tabulate(LPGBTPhaseCh3_list, headers, showindex = "always", tablefmt="psql")
        table4 = tabulate(LPGBTPhaseCh4_list, headers, showindex = "always", tablefmt="psql")
        table5 = tabulate(LPGBTPhaseCh5_list, headers, showindex = "always", tablefmt="psql")
        table6 = tabulate(LPGBTPhaseCh6_list, headers, showindex = "always", tablefmt="psql")
        table7 = tabulate(LPGBTPhaseCh7_list, headers, showindex = "always", tablefmt="psql")

        with open("clockScan.txt", "w") as f:
            f.write("Channel 1 \n")
            f.write(table1)
            f.write("\n \n")
            f.write("Channel 2 \n")
            f.write(table2)
            f.write("\n \n")
            f.write("Channel 3 \n")
            f.write(table3)
            f.write("\n \n")
            f.write("Channel 4 \n")
            f.write(table4)
            f.write("\n \n")
            f.write("Channel 5 \n")
            f.write(table5)
            f.write("\n \n")
            f.write("Channel 6 \n")
            f.write(table6)
            f.write("\n \n")
            f.write("Channel 7 \n")
            f.write(table7)
            f.write("\n \n")
            f.write("Channel 8 \n")
            f.write(table8)

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

    def LpGBT_IC_write(self, data):

        # wordBlock = ''
        # for i in range(0,len(data)//8):
        #     word = data[0+i*8:8+i*8][::-1]
        #     wordBlock += word#[::-1]
        wordBlock = ''.join([data[i:i+8] for i in range(0, len(data), 8)][::-1])
        # wordBlock = data

        #address = primary lpGBT address???

        self.status45.sendFifoAOperation(operation=1,counter=(len(data)//8),address=7)
        serialMod.writeToChip(self,'45',wordBlock)
        self.status45.sendStartControlOperation(operation=1,address=7)
        self.status45.send()

"""
    def LpGBT_IC_REGWRRD(self, primaryLpGBTAddress, nwords, data, memoryAddress):
        # write to I2C, then reads back

        self.status.send(self)
        dataBitsToSend = f'{chipType}{controlLpGBTbit}{full_addr[:5]}'

        # dpWriteAddress = '000000000001' #12
        # wordCount = f'{88:08b}' #8
        # downlinkSignalOperation = '11' #2
        # playOutFlag = '1' #1
        # playCount = '00001' #5
        # #overhead = 28
        # wordA = f'{0x7E:08b}' # frame delimter
        # rwBit = '0'
        # wordB = primaryLpGBTAddress+rwBit # I2C address of LpGBT12/13 (7 bits), rw
        # wordC = f'{0x00:08b}' # command
        # wordD1, wordD2 = u16_to_bytes(nwords)
        # wordE1, wordE2 = u16_to_bytes(memoryAddress) # I2CM0Data0 memory address [15:8]
        # datawords = [data[8*i:8*(i+1)] for i in range(nwords)]

        #Parity check
        # bitsToCheck = [wordC, wordD1, wordD2, wordE1, wordE2]
        # bitsToCheck[5:5] = datawords
        # parity = self.parity_gen(bitsToCheck)
        # print("parity: ")
        # print(parity)
        # wordG = f'{parity:08b}' #parity

        # wordAA = f'{0x7E:08b}' # frame delimiter

        #
        wordBlock = wordA[::-1]+\
                    wordB[::-1]+\
                    wordC[::-1]+\
                    wordD1[::-1]+\
                    wordD2[::-1]+\
                    wordE1[::-1]+\
                    wordE2[::-1]

        for word in datawords:
            wordBlock += word[::-1]

        wordBlock += wordG[::-1]+\
                     wordAA[::-1]
        #
        lpgbtControlBits = dpWriteAddress[::-1]+\
                         wordCount[::-1]+\
                         downlinkSignalOperation[::-1]+\
                         playOutFlag[::-1]+\
                         playCount[::-1]+\
                         wordBlock

        dataBitsToSend = lpgbtControlBits.ljust(280,'1')

        #keep this
        #dataBitsToSend = "".join(dataBitsSplit[::-1])
        #dataBitsToSend = dataBitsToSend

        #print(len(dataBitsToSend))
        print(dataBitsToSend)
        new_dataBitsToSend = []
        for num in range(35):
            #dataBitsToSend[0+num*8:8+num*8]  = dataBitsToSend[0+num*8:8+num*8][::-1]
            #print(num,"\t",dataBitsToSend[0+num*8:8+num*8])
            new_dataBitsToSend.append(dataBitsToSend[0+num*8:8+num*8][::-1])
            print(num,"\t",dataBitsToSend[0+num*8:8+num*8][::-1]) #correct
        dataBitsToSend = "".join(new_dataBitsToSend)

        self.status.sendFifoAOperation(self,operation=1,counter=35,address=7)
        serialMod.writeToChip(self,'A',dataBitsToSend)
        self.status.sendStartControlOperation(self,operation=1,address=7)
        self.status.send(self)
"""

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

