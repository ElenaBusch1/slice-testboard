from PyQt5 import uic, QtWidgets
import os
import time
import configparser
import chipConfiguration as CC
import serialMod
import sliceMod
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

        copyConfig = lambda w,x,y,z : lambda : self.copyConfigurations(w,sourceSectionName=x,targetChipNames=y,targetSectionNames=z)
        # self.testButton.clicked.connect(copyConfig("lauroc13",None,["lauroc14"],None))
        # self.testButton.clicked.connect(copyConfig("coluta13","ch1",["coluta13","coluta14"],["ch1","ch2"]))

        self.isConnected = False
        self.startup()


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
