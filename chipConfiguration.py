import os
import configparser
import sliceMod

class Configuration(dict):
    """Handles, holds, and manipulates configuration bits and settings."""

    def __init__(self, GUI, cfgFileName, specFileName, chipType, lpgbtMaster, i2cMaster, i2cAddress):
        super(Configuration, self).__init__()
        self.GUI = GUI
        self.defaultCfgFile = os.path.join(os.path.abspath("."), "config", cfgFileName)
        self.specialCfgFile = os.path.join(os.path.abspath("."), "config", specFileName)
        self.lpgbtMaster = lpgbtMaster
        self.i2cMaster = i2cMaster
        self.i2cAddress = i2cAddress
        self.chipType = chipType

        self.readCfgFile()
        # self.updated = True


    def __eq__(self, other):
        return self.items() == other.items()


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
            return self.__getitem__(section)[setting]
        except KeyError:
            self.GUI.showError(f"Configuration setting {setting} in {section} requested, but not found.")
            return ''


    def setConfiguration(self, section, setting, value):
        """Sets a specific setting value in the list. Regenerates bits attribute."""
        try:
            self.__getitem__(section)[setting] = value
        except KeyError:
            self.GUI.showError(f"Configuration setting {setting} in {section} requested, but not found. Nothing has been changed")
        self.updateConfigurationBits()


    def getConfiguration(self, section, setting):
        """Returns the value of given named setting."""
        try:
            return self.__getitem__(section)[setting]
        except KeyError:
            self.GUI.showError(f"Configuration setting value {setting} in {section} requested, but not found.")
            return ''


    def updateConfigurationBits(self, fileName = ''):
        """Updates the bits attribute"""
        if not self.items():
            if not fileName:
                self.GUI.showError('No configuration settings loaded and no file specified.')
            else:
                self.readCfgFile(fileName)
        for section in self.keys():
            self.__getitem__(section).bits = "".join([setting for setting in self.__getitem__(section).values()]).zfill(self.__getitem__(section).total)


    def sendUpdatedConfiguration(self):
        """Sends updated bits to chip."""
        for section in self.values():
            if not section.updated: continue
            sliceMod.i2cWrite(self, section)
            section.updated = False


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
            self.update({section: Section(config, template, internalAddr)})



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
        self.updated = True

    def __setitem__(self, key, value):
        """Override setitem to show section has been updated"""
        self.__dict__[key] = value
        self.updated = True


# class Setting:
#     def __init__(self, config, value):
#         pass

