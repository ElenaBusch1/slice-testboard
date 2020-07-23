import os
from PyQt5 import QtWidgets

class Configuration:
    """Handles, holds, and manipulates configuration bits and settings."""

    def __init__(self, GUI, fileName, tabName, sectionName, channelName, channelAddress, i2c = ''):
        self.GUI = GUI
        self.fileName = fileName
        self.tabName =  tabName
        self.sectionName = sectionName
        self.channelName = channelName
        self.address = int(channelAddress)
        self.isI2C = bool(i2c)

        self.settings = None # filled with a dict in readCfgFile
        self.total = None # filled with int in readCfgFile
        self.bits = None # filled with string in updateConfigurationBits

        self.readCfgFile()
        self.updated = True


    def __eq__(self, other):
        return self.settings == other.settings


    def __ne__(self, other):
        return not self.__eq__(other)


    def __deepcopy__(self):
        """
        Class implementation of deepcopy
        Reference: https://stackoverflow.com/questions/6279305/typeerror-cannot-deepcopy-this-pattern-object
        """
        return Configuration(self.GUI,self.fileName,self.tabName,self.sectionName,self.channelName,self.isI2C)


    def clone(self):
        return self.__deepcopy__()


    def getSetting(self, name):
        """Searches for setting based on name. Returns if found."""
        try:
            return self.settings[name]
        except KeyError:
            self.GUI.showError(f"Configuration setting {name} requested, but not found.")
            return ''


    def setConfiguration(self, name, value):
        """Sets a specific setting value in the list. Regenerates bits attribute."""
        try:
            self.settings[name] = value
        except KeyError:
            self.GUI.showError(f"Configuration setting {name} requested, but not found. Nothing has been changed")
        self.updateConfigurationBits()


    def getConfiguration(self, name):
        """Returns the value of given named setting."""
        try:
            return self.settings[name].value
        except KeyError:
            self.GUI.showError(f"Configuration setting {name} requested, but not found. Nothing has been changed")
            return ''


    def updateConfigurationBits(self, fileName = ''):
        """Updates the bits attribute"""
        if not self.settings:
            if not fileName:
                self.GUI.showError('No configuration settings loaded and no file specified.')
            else:
                self.readCfgFile()
        self.bits = "".join([setting.value for setting in self.settings.values()]).zfill(self.total)


    def sendUpdatedConfiguration(self, isI2C = False):
        """Sends updated bits to chip."""
        pass


    def readCfgFile(self):
        pass



class Settings:
    def __init__(self):
        pass

