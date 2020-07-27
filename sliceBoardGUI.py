from PyQt5 import uic, QtWidgets, QtGui
import os
import configparser
import chipConfiguration as CC

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

        self.chips = {}
        self.chipsConfig = os.path.join(os.path.abspath("."), "config", "chips.cfg")

        self.testButton.clicked.connect(self.test)

        self.startup()


    def test(self):
        with open("tmp.txt",'a') as f:
            for (chipName, chipConfig) in self.chips.items():
                f.write(chipName + "\n")
                for (sectionName, section) in chipConfig.items():
                    f.write(f"{sectionName}: {section.bits}\n")
                    for (settingName, setting) in section.items():
                        f.write(f"{settingName}: {setting}\n")
                    f.write("\n")
                f.write("\n")


    def startup(self):
        self.setupConfigurations()
        self.connectButtons()

        if self.pArgs.debug:
            with open("tmp.txt",'a') as f:
                for (chipName, chipConfig) in self.chips.items():
                    f.write(chipName + "\n")
                    for (sectionName, section) in chipConfig.items():
                        f.write(f"{sectionName}: {section.bits}\n")
                        for (settingName, setting) in section.items():
                            f.write(f"{settingName}: {setting}\n")
                        f.write("\n")
                    f.write("\n")


    def setupConfigurations(self):
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
                    if "Fill" in name or name[-2] == "__": continue
                    boxName = name + "Box"
                    try:
                        boxType = type(getattr(self, boxName))
                    except AttributeError:
                        continue
                    if boxType == QtWidgets.QPlainTextEdit:
                        decimalString = str(int(setting, 2))
                        getattr(self, boxName).document().setPlainText(decimalString)
                    elif boxType == QtWidgets.QComboBox:
                        setIndex = int(setting, 2)
                        getattr(self, boxName).setCurrentIndex(setIndex)
                    elif boxType == QtWidgets.QCheckBox:
                        getattr(self, boxName).setChecked(bool(int(setting)))
                    elif boxType == QtWidgets.QLabel:
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
                        boxType = type(getattr(self, boxName))
                    except AttributeError:
                        continue
                    # Define a lambda function "update" to pass arguments to connect signal
                    # In python you need outer lambda to pass arguments to inner lambda
                    update = lambda x, y, z : lambda : self.updateConfigurations(x, y, z)
                    # Call the appropriate method for each type of input box
                    if boxType == QtWidgets.QPlainTextEdit:
                        getattr(self, boxName).textChanged.connect(update(chipName, sectionName, settingName))
                    elif boxType == QtWidgets.QComboBox:
                        getattr(self, boxName).currentIndexChanged.connect(update(chipName, sectionName, settingName))
                    elif boxType == QtWidgets.QCheckBox:
                        getattr(self, boxName).stateChanged.connect(update(chipName, sectionName, settingName))
                    elif boxType == QtWidgets.QLabel:
                        pass
                    else:
                        print(f"Could not find setting box {boxName}")


    def updateConfigurations(self, chipName, sectionName, settingName):
        previousValue = self.chips[chipName][sectionName][settingName]
        length = len(previousValue)
        name = chipName + sectionName + settingName
        boxName = name + "Box"
        try:
            boxType = type(getattr(self, boxName))
        except AttributeError:
            return
        if boxType == QtWidgets.QPlainTextEdit:
            plainText = getattr(self, boxName).toPlainText()
            try:
                decimal = int(plainText)
            except ValueError:
                decimal = 0
            binary = f"{decimal:b}".zfill(length)
            if len(binary) > length:
                print("Setting overflow! Configuration not changed.")
                try:
                    previousDecimalStr = str(int(previousValue, 2))
                    getattr(self, boxName).document().setPlainText(previousDecimalStr)
                except ValueError:
                    print("Invalid input! Cannot convert to binary.")
                return
        elif boxType == QtWidgets.QComboBox:
            index = getattr(self, boxName).currentIndex()
            binary = f"{index:b}".zfill(length)
        elif boxType == QtWidgets.QCheckBox:
            binary = str(int(getattr(self, boxName).isChecked()))
        else:
            binary = ""
            print(f"Could not find setting box {boxName}")
        self.chips[chipName].setConfiguration(sectionName, settingName, binary)
        print(f"Updated {chipName} {sectionName}, {settingName}: {binary}")

