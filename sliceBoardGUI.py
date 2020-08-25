from PyQt5 import uic, QtWidgets
import os
import time
import configparser
import chipConfiguration as CC
import serialMod
import status
from functools import partial

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

        # Instance of the Status class. Communicates with FIFO B / FPGA status registers
        self.status36 = status.Status(self, "36")
        self.status45 = status.Status(self, "45")

        self.chips = {}
        self.chipsConfig = os.path.join(os.path.abspath("."), "config", "chips.cfg")

        # Fill internal dictionaries with configurations from .cfg files
        self.setupConfigurations()

        # Establish link between GUI buttons and internal configuration dictionaries
        self.connectButtons()

        self.testButton.clicked.connect(self.test)
        self.test2Button.clicked.connect(self.test2)

        self.isConnected = False
        self.startup()
        
        # self.sendConfigurationsFromLpGBT()


    def test(self):
        """General purpose test function"""
        with open("tmp.txt", 'a') as f:
            for (chipName, chipConfig) in self.chips.items():
                f.write(chipName + "\n")
                for (sectionName, section) in chipConfig.items():
                    f.write(f"{sectionName}: {section.bits}\n")
                    for (settingName, setting) in section.items():
                        f.write(f"{settingName}: {setting}\n")
                    f.write("\n")
                f.write("\n")


    def test2(self):

        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.chipsConfig)

        with open("data_write_test.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('lauroc') == -1:
                    continue
                f.write(chipName + "\n")
                cfgFile, specFile, lpgbtMaster, i2cMaster, i2cAddr = [x.strip() for x in config["Chips"][chipName].split(',')]
                chipType = '10'
                controlLpGBT = '12'
                i2cM = '01'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_000  #header\n')
                f.write(f'{i2cAddr}_0 #i2c\n')

                dataBits = ''
                wordCount = 1
                for (sectionName, section) in chipConfig.items():
                    data = self.chips[chipName][sectionName].bits
                    addr = int(self.chips[chipName][sectionName].address)
                    dataBits += f'{data}\n'
                    if wordCount == 1:
                        registerAddr = addr
                    wordCount += 1

                wordCountByte1 = f'{wordCount:08b}'
                wordCountByte2 = '00000000'
                f.write(f'{wordCountByte1}  #datawords {wordCount}\n')
                f.write(f'{wordCountByte2}  #datawords {wordCount}\n')
                f.write(f'{registerAddr:08b}   #first address\n')
                f.write(dataBits)
                f.write('\n')


    def startup(self):
        """Runs the standard board startup / connection routine"""
        if self.pArgs.no_connect:
            pass
        else:
            # Real startup routine when board is connected
            # Find the ports and store the names
            portDict = serialMod.findPorts(self)
            self.port36, self.port45 = portDict['AB46BJOXA'], portDict['AB470WYIA']
            # Set up the serial connection to each port, pause, and test
            self.serial36, self.serial45 = serialMod.setupSerials(self)
            time.sleep(0.01)
            self.handshake()
            # Reset the status bits to zero, then reset FPGAs
            self.status36.initializeUSB()
            self.status36.send()
            self.status36.sendSoftwareReset()
            self.status45.initializeUSB()
            self.status45.send()
            self.status45.sendSoftwareReset()


    def handshake(self):
        """Checks the serial connections. Gives green status to valid ones"""
        A, B = serialMod.checkSerials(self)
        if A:
            self.fifo36StatusBox.setStyleSheet("background-color: rgb(0, 255, 0);")
            self.fifo36StatusBox.setText("Connected")
        if B:
            self.fifo45StatusBox.setStyleSheet("background-color: rgb(0, 255, 0);")
            self.fifo45StatusBox.setText("Connected")
        if A and B:
            self.isConnected = True


    def setupConfigurations(self):
        """Sets up a Configuration object for each chip listed in self.chipsConfig"""
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.chipsConfig)

        for chip in config["Chips"]:
            cfgFile, specFile, lpgbtMaster, i2cMaster, i2cAddr = [x.strip() for x in config["Chips"][chip].split(',')]
            self.chips[chip] = CC.Configuration(self, cfgFile, specFile, lpgbtMaster, i2cMaster, i2cAddr)

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
                        box.textChanged.connect(partial(self.updateConfigurations, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QComboBox):
                        # noinspection PyUnresolvedReferences
                        box.currentIndexChanged.connect(partial(self.updateConfigurations, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QCheckBox):
                        # noinspection PyUnresolvedReferences
                        box.stateChanged.connect(partial(self.updateConfigurations, chipName, sectionName, settingName))
                    elif isinstance(box, QtWidgets.QLabel):
                        pass
                    else:
                        print(f"Could not find setting box {boxName}")


    def updateConfigurations(self, chipName, sectionName, settingName):
        previousValue = self.chips[chipName][sectionName][settingName]
        length = len(previousValue)
        name = chipName + sectionName + settingName
        boxName = name + "Box"
        try:
            box = getattr(self, boxName)
        except AttributeError:
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


    def showError(self, message):
        """Error message method. Called by numerous dependencies."""
        errorDialog = QtWidgets.QErrorMessage(self)
        errorDialog.showMessage(message)
        errorDialog.setWindowTitle("Error")

    def u16_to_bytes(self, val):
        byte1 = (val >> 8) & 0xff
        byte0 = (val >> 0) & 0xff
        return byte1, byte0

    def LpGBT_IC_Write(self, primaryLpGBTAddress, nwords, data, memoryAddress):
        # write to I2C, then reads back

        self.status.send(self)

        dpWriteAddress = '000000000001' #12
        wordCount = f'{88:08b}' #8
        downlinkSignalOperation = '11' #2
        playOutFlag = '1' #1
        playCount = '00001' #5
        #overhead = 28
        wordA = f'{0x7E:08b}' # frame delimter
        rwBit = '0'
        wordB = primaryLpGBTAddress+rwBit # I2C address of LpGBT12/13 (7 bits), rw
        wordC = f'{0x00:08b}' # command
        wordD1, wordD2 = u16_to_bytes(nwords) 
        wordE1, wordE2 = u16_to_bytes(memoryAddress) # I2CM0Data0 memory address [15:8]
        datawords = [data[8*i:8*(i+1)] for i in range(nwords)]

        #Parity check
        bitsToCheck = [wordC, wordD1, wordD2, wordE1, wordE2]
        bitsToCheck[5:5] = datawords
        parity = self.parity_gen(bitsToCheck)
        print("parity: ")
        print(parity)
        wordG = f'{parity:08b}' #parity

        wordAA = f'{0x7E:08b}' # frame delimiter

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

