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
from functools import partial
from collections import OrderedDict

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
        self.nSamples = 2  # default number of samples to parse from standard readout
        self.discarded = 0  # first N samples of readout are discarded by software (MSB end)
        self.dataWords = 32  # number of bytes for each data FPGA coutner increment
        self.controlWords = 8 # number of bytes for each control FPGA counter increment

        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        # self.status36 = status.Status(self, "36")
        self.status45 = status.Status(self, "45")

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

        # self.testButton.clicked.connect(self.test)
        # self.testButton.clicked.connect(lambda: self.isLinkReady("45"))
        self.testButton.clicked.connect(self.lpgbt45readBack)
        self.test2Button.clicked.connect(self.configure_clocks_test)
        self.test3Button.clicked.connect(self.write_uplink_test)
        #self.test2Button.clicked.connect(self.lpgbt_test)

        self.laurocConfigsButton.clicked.connect(self.collectLaurocConfigs)
        self.dataLpGBTConfigsButton.clicked.connect(self.collectDataLpgbtConfigs)
        self.controlLpGBTConfigsButton.clicked.connect(self.sendUpdatedConfigurations)
        self.colutaConfigsButton.clicked.connect(self.coluta_config_test)

        #Configuration Buttons
        self.configureControlLpGBTButton.clicked.connect(self.sendUpdatedConfigurations)
        self.laurocConfigureButton.clicked.connect(self.sendUpdatedConfigurations)
        #self.powerConfigureButton.clickec.connect(self.sendPowerUpdates)

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
        serialMod.flushBuffer(self, "45")
        self.status45.readbackStatus()
        time.sleep(0.1)
        serialMod.readFromChip(self, "45", 6)
        self.status45.send()


    def lpgbt_test(self):
        i2cAddr = f'{0xE0:08b}'
        first_reg = f'{0x0E0:012b}'
        #first_reg = f'{0x052:012b}'
        dataBitsToSend = f'001{first_reg[:5]}'
        dataBitsToSend += f'{first_reg[5:]}0'

        piodirl = '00010100'
        piooutl = '00010100'
        piodrivestrengthl = '00010100'

        data = ''.join([f'{i:08b}' for i in range(1,4)])
        #data = ''.join(['00001000', piodirl, '00001000', piooutl, '00000000', '00000000', '00000000', '00000000', '00001000', piodrivestrengthl])
        #data = '00000010'
        #data += '00000011'
        #data += '00000100'
        wordCount = len(data)//8

        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'
        dataBitsToSend += data

        #data4 = ''.join(['00000000', '00010000', '00000000', '00010000', '00000000', '00000000', '00000000', '00000000', '00000000', '00010000'])
        #data11 = ''.join(['00001000', '00000000', '00001000', '00000000', '00000000', '00000000', '00000000', '00000000', '00001000', '00000000'])

        self.LpGBT_IC_write(i2cAddr, dataBitsToSend)

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

            self.LpGBT_IC_write(i2cAddr, dataBitsToSend)

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
        dummy = f'{0XE0:08b}'

        first_reg = f'{0x118:012b}'
        dataBitsToSend = f'000{first_reg[:5]}'
        dataBitsToSend += f'{first_reg[5:]}0'  

        #data = ''.join(['00000000', '00000000', '00000000', '00000000', '00000000', '00000000', '00000001', '00000010', '00000011', '00000100'])
        dataValues = [0x0c, 0x24, 0x24, 0x24, 0x04, 0xff]
        data = ''.join([f'{val:08b}' for val in dataValues])
        #data = '00000111'
        #data = f'{}
        #data += '00000000'
        wordCount = len(data)//8
        #wordCount = len(data)//8

        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'
        dataBitsToSend += data  

        self.LpGBT_IC_write(dummy, dataBitsToSend)        

        # sec_reg = f'{0x121:012b}'
        # dataBitsToSend2 = f'000{sec_reg[:5]}'
        # dataBitsToSend2 += f'{sec_reg[5:]}0'  

        # data2 = '00000001'

        # wordCount2 = len(data2)
        # wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount2)
        # dataBitsToSend2 += f'{wordCountByte1:08b}'
        # dataBitsToSend2 += f'{wordCountByte2:08b}'
        # dataBitsToSend2 += data2  

    def colutaI2CWriteControl(self, chipName,tabName,broadcast=False):
        """Same as fifoAWriteControl(), except for I2C."""
        #category = chipConfig[tabName]
        category = self.chips[chipName][tabName]
        address = category.address # FPGA address, '0' for I2C
        if broadcast:
            if int(tabName[-1]) <= 4:
                i2cAddress = 15<<0  #  15 = 00001111
            else:
                i2cAddress = 15<<4  # 240 = 11110000
        else:
            i2cAddress = 8 #int(category.i2cAddress) # I2C address, '8' for global
        controlBits = category.bits

        # Based on the I2C configurations split the data byte into chunks
        # For the global configuration bits, the subaddress are 8,16
        # For the channel configuration bits,
        # the subaddresses are 0,3,6,9,12,15,18,21,24,27,30,31
        if tabName=='global':
            split = 64
            subAddressList = [8*(i+1) for i in range( int( np.floor(len(controlBits)/split) ) )]
            overlapLSBIndex = 64

        elif tabName=='readonly__':
            return

        elif tabName.startswith('ch'):
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
        if tabName=='global':
            # For global bits, sub address is the I2C address
            for dataBits,subAddress in zip(dataBitsList,subAddressList):
                allBits += dataBits
                #if coluta.pOptions.checkACK:
                    ### DP: Need to add check for main thread to show this error, otherwise we will have reentrancy issues
                    #if not i2cCheckACK(coluta): coluta.showError(f'COLUTAMOD: No ACK received writing {tabName} bits')

        elif tabName.startswith('ch'):
            for dataBits,subAddress in zip(dataBitsList,subAddressList):
                subAddrStr = '{0:06b}'.format(subAddress)
                dataBits = makeI2CSubData(dataBits,'1','0',subAddrStr,f'{i2cAddress:08b}')
                allBits += dataBits
                #serialResult = attemptWrite(chipName, dataBits, 0, address)
                #if coluta.pOptions.checkACK:
                    ### DP: Need to add check for main thread to show this error, otherwise we will have reentrancy issues
                    #if not i2cCheckACK(coluta): coluta.showError(f'COLUTAMOD: No ACK received writing {tabName} bits')

        #else:
            #coluta.showError('COLUTAMOD: Unknown configuration bits.')
            #serialResult = False

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

        self.LpGBT_IC_write(i2cAddr, dataBitsToSend)

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

        self.LpGBT_IC_write(None, dataBitsToSend)

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

    def sendControlLpgbtConfigs(self, chipName, wordCount, registerAddr, dataBits):

        chipConfig = self.chips[chipName]
        if chipName.find('lpgbt') == -1:
            return
        #if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
        #    return
        chipType = f'{int(chipConfig.chipType):02b}'
        controlLpGBT = chipConfig.lpgbtMaster
        #try:
        #    i2cM = f'{int(chipConfig.i2cMaster):02b}'
        #except:
        #    i2cM = 'EC'
        controlLpGBTbit = '0'
        if (controlLpGBT == '13'):
            controlLpGBTbit = '1'

        dataBitsToSend = f'{chipType}{controlLpGBTbit}{registerAddr[:5]}'
        #print("header 1: ", dataBitsToSend)
        dataBitsToSend += f'{registerAddr[5:]}0'
        print("header:", dataBitsToSend)

        #wordCount += 2
        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}{wordCountByte2:08b}'

        #addr2, addr1 = u16_to_bytes(registerAddr)
        #dataBitsToSend += f'{addr1:08b}{addr2:08b}'

        dataBitsToSend += dataBits

        print("sending:")
        for word in [dataBitsToSend[i:i+8] for i in range(0,len(dataBitsToSend),8)]:
            print(word)

        self.LpGBT_IC_write(None, dataBitsToSend)

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
        sectionNames =  ['piodirh', 'piodirl', 'pioouth', 'piooutl', 'piopullenah', 'piopullenal', 'pioupdownh', 'pioupdownl', 'piodrivestrengthh', 'piodrivestrengthl']
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
            if chipName != 'lpgbt12':
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
                if 'lpgbt12' == chipName: #or 'lpgbt13' == chipName:
                    self.sendControlLpgbtConfigs(chipName, wordCount, firstAddr, dataToSend)
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
        #dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)])
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
        
        print(dataStringChunks829)


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

    def LpGBT_IC_write(self, primaryLpGBTAddress, data):

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

