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

        self.startup()


    def startup(self):
        self.setupConfigurations()

        if self.pArgs.debug:
            with open("tmp.txt",'a') as f:
                for (chipName, chipConfig) in self.chips.items():
                    f.write(chipName + "\n")
                    for (sectionName, section) in chipConfig.sections.items():
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
