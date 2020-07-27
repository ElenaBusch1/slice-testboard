import os
from PyQt5 import QtWidgets
import configparser

class Configuration:
    """Handles, holds, and manipulates configuration bits and settings."""

    def __init__(self, GUI, cfgFileName, specFileName, lpgbtMaster, i2cMaster, i2cAddress):
        self.GUI = GUI
        self.defaultCfgFile = os.path.join(os.path.abspath("."), "config", cfgFileName)
        self.specialCfgFile = os.path.join(os.path.abspath("."), "config", specFileName)
        self.lpgbtMaster = lpgbtMaster
        self.i2cMaster = i2cMaster
        self.i2cAddress = i2cAddress

        self.sections = {} # filled with a dict in readCfgFile

        self.readCfgFile()
        # self.updated = True


    def __eq__(self, other):
        return self.sections == other.sections


    def __ne__(self, other):
        return not self.__eq__(other)


    def __deepcopy__(self):
        """
        Class implementation of deepcopy
        Reference: https://stackoverflow.com/questions/6279305/typeerror-cannot-deepcopy-this-pattern-object
        """
        return Configuration(self.GUI, self.defaultCfgFile, self.specialCfgFile, self.lpgbtMaster, self.i2cMaster, self.i2cAddress)


    def clone(self):
        return self.__deepcopy__()


    def getSetting(self, section, setting):
        """Searches for setting based on name. Returns if found."""
        try:
            return self.sections[section][setting]
        except KeyError:
            self.GUI.showError(f"Configuration setting {setting} in {section} requested, but not found.")
            return ''


    def setConfiguration(self, section, setting, value):
        """Sets a specific setting value in the list. Regenerates bits attribute."""
        try:
            self.sections[setting][setting] = value
        except KeyError:
            self.GUI.showError(f"Configuration setting {setting} in {section} requested, but not found. Nothing has been changed")
        self.updateConfigurationBits()


    def getConfiguration(self, section, setting):
        """Returns the value of given named setting."""
        try:
            return self.sections[section][setting].value
        except KeyError:
            self.GUI.showError(f"Configuration setting value {setting} in {section} requested, but not found.")
            return ''


    def updateConfigurationBits(self, fileName = ''):
        """Updates the bits attribute"""
        if not self.sections:
            if not fileName:
                self.GUI.showError('No configuration settings loaded and no file specified.')
            else:
                self.readCfgFile(fileName)
        for section in self.sections:
            self.sections[section].bits = "".join([setting.value for setting in self.sections[section].values()]).zfill(self.sections[section].total)


    def sendUpdatedConfiguration(self):
        """Sends updated bits to chip."""
        pass


    def readCfgFile(self, fileName = ''):
        """Reads default and special config files, then populates the sections dict with section objects"""
        config = configparser.ConfigParser()
        config.optionxform = str
        if fileName:
            config.read([self.defaultCfgFile, fileName])
        else:
            config.read([self.defaultCfgFile, self.specialCfgFile])

        for section in config["Categories"]:
            template, internalAddr, *_ = [x.strip() for x in config["Categories"][section].split(',')]
            self.sections[section] = Section(config, template, internalAddr)



class Section(dict):
    """Dictionary-like class that stores name:value pairs for every setting in a section
       Also stores total number of bits in a section, the bits as one string, and the internal address"""
    def __init__(self, config, templates, internalAddr):
        super(Section, self).__init__()
        self.total = 0
        try:
            for template in templates.split("+"):
                for (key, value) in config[template].items():
                    if key == "Total":
                        self.total += int(value)
                    else:
                        self.update({key: value})
        except KeyError:
            ### lpGBT has many settings we don't care about, so fill them with 0's
            self.total += 8
            self.update({"Fill": "00000000"})
        self.bits = "".join([setting for setting in self.values()]).zfill(self.total)
        self.address = internalAddr



# class Setting:
#     def __init__(self, config, value):
#         pass

