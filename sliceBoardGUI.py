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

qtCreatorFile = os.path.join(os.path.abspath("."), "sliceboard.ui")
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


class sliceBoardGUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, qApp, pArgs):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        # General GUI options and signals
        self.pArgs = pArgs
        self.qApp = qApp
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
        self.nSamples = 4000  # default number of samples to parse from standard readout
        self.discarded = 0  # first N samples of readout are discarded by software (MSB end)
        self.dataWords = 32  # number of bytes for each data FPGA coutner increment
        self.controlWords = 8 # number of bytes for each control FPGA counter increment

        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        # self.status36 = status.Status(self, "36")
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
        self.testButton.clicked.connect(lambda: self.i2cLauroc("lauroc20"))
        #self.testButton.clicked.connect(self.test_lpgbt9config_loop)
        #self.test2Button.clicked.connect(self.configure_clocks_test)
        #self.test2Button.clicked.connect(self.i2cCOLUTA)
        #self.test2Button.clicked.connect(self.i2cControlLpGBT)
        # self.test2Button.clicked.connect(self.configure_clocks_test)
        # self.test2Button.clicked.connect(lambda: self.isLinkReady("45"))
        self.test3Button.clicked.connect(self.write_uplink_test)
        self.test2Button.clicked.connect(self.colutaRegWriteTest)
        #self.test2Button.clicked.connect(self.lpgbt_test)

        self.initializeUSBButton.clicked.connect(self.initializeUSBISSModule)
        self.disableParityButton.clicked.connect(self.disableParity)
        self.dcdcConverterButton.clicked.connect(self.enableDCDCConverter)
        self.lpgbt12ResetButton.clicked.connect(self.lpgbt12Reset)
        self.lpgbt13ResetButton.clicked.connect(self.lpgbt13Reset)

        self.lpgbtI2CWriteButton.clicked.connect(self.lpgbt_i2c_write)
        self.lpgbtI2CReadButton.clicked.connect(self.lpgbt_i2c_read)
        self.lpgbtICWriteButton.clicked.connect(self.lpgbt_ic_write)

        self.configureClocksButton.clicked.connect(self.configure_clocks_test)
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
        self.laurocConfigureButton.clicked.connect(self.sendUpdatedConfigurations)
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

        self.isConnected = False
        self.startup()

        # self.sendConfigurationsFromLpGBT()

    def silly_reg_test(self):
        lpgbtI2CAddr = int(self.chips["lpgbt12"].i2cAddress,2)
        dataI2CAddr = int(self.chips["lpgbt10"].i2cAddress,2)
        register = 0x062
        data = [21]
        self.i2cDataLpgbtWriteOneReg(lpgbtI2CAddr, dataI2CAddr, register, data)
        #self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, register, data)
        register = 0x082
        data = [22]
        self.i2cDataLpgbtWriteOneReg(lpgbtI2CAddr, dataI2CAddr, register, data)
        #self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, register, data)
        register = 0x062
        self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, register, 4)

        print("READ STATUS REGS")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x174, 4)
        print("SINGLE READ REG")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x178, 1)
        print("MULTI READ REG")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x179, 16)

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


    def test_lpgbt9config_loop(self):
        print("START lpGBT14 config loop")
        while True:
            self.i2cControlLpGBT("lpgbt14")
            #self.i2cDataLpGBT("lpgbt9")

    def test(self):
        """General purpose test function"""
        # with open("tmp.txt", 'a') as f:
        #     for (chipName, chipConfig) in self.chips.items():
        #         f.write(chipName + "\n")
        #         for (sectionName, section) in chipConfig.items():
        #             f.write(f"{sectionName}: {section.bits}\n")
        #             for (settingName, setting) in section.items():
        #                 f.write(f"{settingName}: {setting}\n")
        #             f.write("\n")
        #         f.write("\n")

        #erialMod.flushBuffer(self, "45")
        #elf.status45.readbackStatus()
        #ime.sleep(0.1)
        #erialMod.readFromChip(self, "45", 6)
        #elf.status45.send()

        #dataBlock = 'F0EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0DFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0BFBEBDBCBBBAB9B8B7B6B5B4B3B2B1B0AFAEADACABAAA9A8A7A6A5A4A3A2A1A09F9E9D9C9B9A999897969594939291908F8E8D8C8B8A898887868584838281807F7E7D7C7B7A797877767574737271706F6E6D6C6B6A696867666564636261605F5E5D5C5B5A595857565554535251504F4E4D4C4B4A494847464544434241403F3E3D3C3B3A393837363534333231302F2E2D2C2B2A292827262524232221201F1E1D1C1B1A191817161514131211110F0E0D0C0B0A09080706050403020100F00000'
        dataBlock = 'F0EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0DFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0BFBEBDBCBBBAB9B8B7B6B5B4B3B2B1B0AFAEADACABAAA9A8A7A6A5A4A3A2A1A09F9E9D9C9B9A999897969594939291908F8E8D8C8B8A898887868584838281807F7E7D7C7B7A797877767574737271706F6E6D6C6B6A696867666564636261600090C000'
        dataBitsToSend = ''
        for word in [dataBlock[i:i+2] for i in range(0, len(dataBlock), 2)]:
            val = int(word,16)
            #if val < 96:
            #    continue
            print(word,val)
            dataBitsToSend += f'{val:08b}'

        self.LpGBT_IC_write(None, dataBitsToSend)

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


    def lpgbt12Reset(self):
        chip = self.chips["lpgbt12"]
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x07])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])

    def lpgbt13Reset(self):
        chip = self.chips["lpgbt13"]
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x07])
        writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x12c, [0x00])

    def lpgbt_test(self):

        chip = self.chips["lpgbt14"]

        i2cAddr = f'{0xE0:08b}'
        first_reg = f'{0x5D:012b}'
        #first_reg = f'{0x052:012b}'
        dataBitsToSend = f'000{first_reg[:5]}'
        dataBitsToSend += f'{first_reg[5:]}0'

        data = ''.join([f'{0Xaa:08b}' for i in range(1,96)])
        #data = '00000010'
        #data += '00000011'
        #data += '00000100'
        wordCount = len(data)

        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'
        dataBitsToSend += data

        #data4 = ''.join(['00000000', '00010000', '00000000', '00010000', '00000000', '00000000', '00000000', '00000000', '00000000', '00010000'])
        #data11 = ''.join(['00001000', '00000000', '00001000', '00000000', '00000000', '00000000', '00000000', '00000000', '00001000', '00000000'])

        while True:
             #readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x062, 1)
             writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x062, [0x21])
        #    writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x0fd, [0x02])

        #self.LpGBT_IC_write(dataBitsToSend)

        #dataBitsToSend4 = f'000{first_reg[:5]}' + f'{first_reg[5:]}0' + f'{wordCountByte1:08b}' + f'{wordCountByte2:08b}' + data4
        #dataBitsToSend11 = f'000{first_reg[:5]}' + f'{first_reg[5:]}0' + f'{wordCountByte1:08b}' + f'{wordCountByte2:08b}' + data11

        #self.LpGBT_IC_write(i2cAddr, dataBitsToSend4)
        #self.LpGBT_IC_write(i2cAddr, dataBitsToSend11)

    def configure_clocks_test(self):
        i2cAddr = f'{0XE0:08b}'
        #i2cAddr =

        #regAddrs = [0x06c, 0x06d, 0x07c, 0x07d, ]

        regAddr  = [0x06c, 0x07c, 0x080, 0x084, 0x088, 0x08c, 0x090, 0x094, 0x09c, 0x0ec]
        regDataA = [0x19,  0x19,  0x19,  0x00,  0x19,  0x19,  0x19,  0x19,  0x19,  0x00]
        regDataB = [0x73,  0x73,  0x73,  0x00,  0x73,  0x73,  0x73,  0x73,  0x73,  0x00]
        regDataC = [0x00,  0x19,  0x00,  0x19,  0x19,  0x19,  0x00,  0x00,  0x00,  0x00]
        regDataD = [0x00,  0x73,  0x00,  0x73,  0x73,  0x73,  0x00,  0x00,  0x00,  0x07]

        #regDataA = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataB = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataC = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataD = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]


        for i in range(len(regAddr)):
            addr = regAddr[i]
            first_reg = f'{addr:012b}'
            dataBitsToSend = f'000{first_reg[:5]}'
            dataBitsToSend += f'{first_reg[5:]}0'

            data = ''.join([f'{regDataA[i]:08b}', f'{regDataB[i]:08b}', f'{regDataC[i]:08b}', f'{regDataD[i]:08b}'])

            wordCount = len(data)//8

            wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
            dataBitsToSend += f'{wordCountByte1:08b}'
            dataBitsToSend += f'{wordCountByte2:08b}'
            dataBitsToSend += data

            self.LpGBT_IC_write(dataBitsToSend)

        #while True:
        #    self.LpGBT_IC_write(i2cAddr, dataBitsToSend)

    def coluta_config_test(self):

        i2cAddr = f'{0xE0:08b}'

        wordCount = 16
        data =  '11111010' +\
                '11011000' +\
                '10001010' +\
                '11010111' +\
                '01110110' +\
                '10111001' +\
                '10000100' +\
                '00000100' +\
                '00000000' +\
                '00011111' +\
                '11000010' +\
                '10100000' +\
                '00000100' +\
                '01000000' +\
                '01000001' +\
                '00010100'

        self.sendCOLUTAConfigs('coluta13', wordCount, data)

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


    def collectColutaConfigs(self):

        with open("coluta_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('coluta') == -1:
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                i2cM = f'{int(chipConfig.i2cMaster):02b}'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                #i2cAddr = f'{int(chipConfig.i2cAddress,0):010b}'
                i2cAddr = '0'+chipConfig.i2cAddress
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_{i2cAddr[:3]}  #chip_controlLpGBT_i2cMaster_i2cAddr[9:7]\n')
                f.write(f'{i2cAddr[3:11]}_0 #i2cAddr[6:0]_r/w\n')

                wordCount = 0;
                dataBits = ''
                for (sectionName, section) in chipConfig.items():
                    # data = self.chips[chipname][sectionname].bits
                    data = self.colutaI2CWriteControl(chipName, sectionName)
                    datawords = [data[8*i:8*(i+1)] for i in range(len(data)//8)]
                    localWordCount = len(datawords)
                    dataBits += (chipName + ", " + sectionName + ": " + str(localWordCount) + " words\n")
                    for word in datawords:
                        dataBits += f'{word}\n'
                        wordCount += 1
                    dataBits += '\n'



                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords {wordCount}\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')

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

    def collectLaurocConfigs(self):

        with open("lauroc_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('lauroc') == -1:
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                i2cM = f'{int(chipConfig.i2cMaster):02b}'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                #i2cAddr = f'{int(chipConfig.i2cAddress,0):010b}'
                i2cAddr = '000'+ chipConfig.i2cAddress
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_{i2cAddr[:3]}  #chip_controlLpGBT_i2cMaster_i2cAddr[9:7]\n')
                f.write(f'{i2cAddr[3:]}_0 #i2cAddr[6:0]_r/w\n')

                dataBits = ''
                wordCount = 1
                for (sectionName, section) in chipConfig.items():
                    data = self.chips[chipName][sectionName].bits
                    addr = int(self.chips[chipName][sectionName].address,0)
                    dataBits += f'{data}\n'
                    if wordCount == 1:
                        registerAddr = addr
                    wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords {wordCount}\n')
                f.write(f'{registerAddr:08b}  #first address\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')


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

    def collectDataLpgbtConfigs(self):

        with open("data_lpgbt_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('lpgbt') == -1:
                    continue
                if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                try:
                    i2cM = f'{int(chipConfig.i2cMaster):02b}'
                except:
                    i2cM = 'EC'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_000  #chipType_controlLpGBT_i2CMaster_000\n')
                f.write(f'{chipConfig.i2cAddress}_0 #i2cAddr_r/w\n')

                dataBits = ''
                wordCount = 2
                for (sectionName, section) in chipConfig.items():
                    data = self.chips[chipName][sectionName].bits
                    addr = int(self.chips[chipName][sectionName].address,0)
                    dataBits += f'{data}\n'
                    if wordCount == 2:
                        registerAddr = addr
                    wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords[7:0] {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords[15:8] {wordCount}\n')

                addr2, addr1 = u16_to_bytes(registerAddr)
                f.write(f'{addr1:08b}  #first address [7:0]\n')
                f.write(f'{addr2:08b}  #first address [15:8]\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')


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

    def collectControlLpgbtConfigs(self):

        with open("control_lpgbt_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if (chipName != 'lpgbt12' and chipName != 'lpgbt13'):
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'

                dataBits = ''
                wordCount = 0
                for (sectionName, section) in chipConfig.items():
                    if section.updated:
                        data = self.chips[chipName][sectionName].bits
                        addr = int(self.chips[chipName][sectionName].address,0)
                        dataBits += f'{data}\n'
                        if wordCount == 0:
                            #registerAddr = addr
                            registerAddr = 0x1ce
                        wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                full_addr = f'{registerAddr:012b}'

                f.write(f'{chipType}_{controlLpGBTbit}_{full_addr[:5]}  #chipType_controlLpGBT_1stReg[11:7]\n')
                f.write(f'{full_addr[5:]}_0 #1stReg[6:0]_r/w\n')

                f.write(f'{wordCountByte1:08b}  #datawords[7:0] {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords[15:8] {wordCount}\n')
                #if chipName.find('lpgbt') != -1:

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
        colutaName = "coluta20"
        dataBits = self.colutaI2CWriteControl(colutaName, "ch1", broadcast=True)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch2", broadcast=False)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch3", broadcast=False)
        #dataBits += self.colutaI2CWriteControl(colutaName, "ch4", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch5", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch6", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch7", broadcast=False)
        dataBits += self.colutaI2CWriteControl(colutaName, "ch8", broadcast=False)
        dataBits64 = [dataBits[64*i:64*(i+1)] for i in range(len(dataBits)//64)]
        lpgbtI2CAddr = self.chips["lpgbt"+self.chips[colutaName].lpgbtMaster].i2cAddress
        colutaI2CAddr = self.chips[colutaName].i2cAddress
        colutaI2CAddr = int("".join(colutaI2CAddr.split("_")[1:2]), 2)
        colutaI2CAddrH = colutaI2CAddr >> 1
        colutaI2CAddrL = colutaI2CAddr << 7
        dataBitsGlobal = self.colutaI2CWriteControl(colutaName, "global")
        dataBitsGlobal64 = [dataBitsGlobal[64*i:64*(i+1)] for i in range(len(dataBitsGlobal)//64)]
        for word in dataBits64:
            #word = dataBits64[-1]
            #print(word)
            #while True:
            #dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            print("0x0f9:", [hex(x) for x in [0b00100000, 0x00, 0x00, 0x00, 0x0]])
            print("0x0f9:", [hex(x) for x in [*dataBits8[4:][::-1], 0x8]])
            print("0x0f9:", [hex(x) for x in [*dataBits8[:4][::-1], 0x9]])
            print("0x0f7:", [hex(x) for x in [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0xe]])

            # print("0x0f9:", [hex(x) for x in [0b00100000, 0x00, 0x00, 0x00, 0x0]])
            # print("0x0f9:", [hex(x) for x in [0xff, 0x80, 0x00, 0x00, 0x8]])
            # print("0x0f9:", [hex(x) for x in [0x00, 0x00, 0x00, 0x00, 0x9]])
            # print("0x0f7:", [hex(x) for x in [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0xe]])

            # We will write 8 bytes to i2cM1Data at a time
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0xa0])
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0fd, [0x00])

            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0x01,0x02,0x03,0x04,0x08])
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0x05,0x06,0x07,0x08,0x09])

            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f8, [0x00]) i2cAddr[6:0]
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x04]) i2cAddr[9:7]
            #writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0fd, [0x0E])
            
            #harcoded ADC sel testi
            """
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b00100000, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0xff, 0x80, 0x01, 0x21, 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0x43, 0x00, 0x00, 0x00, 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0xe])
            """
            #note b0 is LSB byte, b1 is 2nd LSB etc
            #within the LSB byte b0 the LSB is to the rightmost
            """
            adcSel = 0xf0
            rw = 0x80
            b0 = 0xc0
            b1 = 0x18
            b2 = 0x05
            b3 = 0x82
            b4 = 0x01
            b5 = 0x01
            """
            # adcSel = 0xf0
            # rw = 0x80
            # b0 = 0x31
            # b1 = 0xf7
            # b2 = 0x00
            # b3 = 0x00
            # b4 = 0x00
            # b5 = 0x21
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b00100000, 0x00, 0x00, 0x00, 0x0])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [ adcSel, rw, b0, b1, 0x8])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [ b2, b3, b4, b5, 0x9])
            # # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0xe])

            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b00100000, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0xe])

        counter = 1
        for word in dataBitsGlobal64:
            # print("global bits", counter)
            print(word)
            print(len(word))
            #while True:
            #addrModification = 8
            addrModification = counter*8
            dataBits8 = [i for i in range(1,9)]
            dataBits8 = [int(word[8*i:8*(i+1)], 2) for i in range(len(word)//8)]
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [0b00100000, 0x00, 0x00, 0x00, 0x0])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[4:][::-1], 0x8])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f9, [*dataBits8[:4][::-1], 0x9])
            # writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [colutaI2CAddrH, colutaI2CAddrL, 0x00, 0x00, 0x00, 0x00, 0xe])
            writeToLpGBT(self.i2cPort, int(lpgbtI2CAddr, 2), 0x0f7, [0x02, 0x00 + addrModification, 0x00, 0x00, 0x00, 0x00, 0xe])
            counter += 1


    def i2cDataLpGBT(self, lpgbt):
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

    def i2cLauroc(self, lauroc):
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
            print("Writing register ", hex(register))
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


    def takeSamples(self):
        """Read and store output from VTRx+ 3 or 6"""
        if not self.isConnected and not self.pArgs.no_connect:
            self.showError("Board is not connected")
            return

        print("Reading data")
        dataByteArray = self.fifoAReadData("36")

        if self.pArgs.no_connect: return

        dataString = sliceMod.byteArrayToString(dataByteArray)
        dataStringChunks32 = "\n".join([dataString[i:i+32] for i in range(0, len(dataString), 32)])
        dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)])
        if self.pArgs.debug: print(dataStringChunks16)

        self.ODP.parseData(self.nSamples, dataString)
        self.ODP.writeDataToFile()

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

