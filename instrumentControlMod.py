"""
Module for instrument control 

name: instrumentControl.py
author: D.Panchal
email: dpanchal@utexas.edu
date: October 18, 2018
"""

# pyVISA library to set up connection with the instruments
#try:
import pyvisa as visa
#except:
#    pass
import numpy
from PyQt5 import QtWidgets
import configparser
import time,os

class InstrumentControl():

    def __init__(self,coluta,configFile):
        """
        Initialize the variables needed for instrument control
        """
        self.coluta = coluta

        self.resourceManager = visa.ResourceManager('@py')
        self.devices = {}
        self.configFile = configFile
        self.setupDeviceConfiguration()

    def setupDeviceConfiguration(self):
        config = configparser.ConfigParser()
        config.optionxform=str

        if not os.path.isfile(self.configFile):
            self.coluta.showError('INSTRUMENT CONTROL: Configuration file found')

        config.read(self.configFile)
        if not config.sections():
            self.coluta.showError('INSTRUMENT CONTROL: Configuration file has no sections')

        config.read(self.configFile)
        devices = dict(config.items('Devices'))

        for deviceType,deviceName in devices.items():
            if not config.has_section(deviceType):
                self.coluta.showError('INTRUMENT CONTROL: No settings found for the device: {0}'.format(deviceType))
                continue

            configItems = config.items(deviceType)
            deviceInstance = globals()[deviceName](self.coluta,self.resourceManager,configItems)
            setattr(self,deviceType,deviceInstance)
            #setattr(self,deviceName,Device(self.coluta,self.resourceManager,configItems))
            self.updateGUIText(self.coluta,getattr(self,deviceType))


    def updateGUIText(self,coluta,device):
        # print(hasattr(devic)
        for setting,value in getattr(device,'settings').items():
            settingName = setting
            boxName = settingName+'Box'
            boxType = type(getattr(coluta,boxName))
            if boxType == QtWidgets.QPlainTextEdit:
                configuration = str(value)
                getattr(coluta,boxName).document().setPlainText(configuration)
            elif boxType == QtWidgets.QComboBox:
                setIndex = colutaMod.binaryStringToDecimal(value)
                getattr(coluta,boxName).SetCurrentIndex(setIndex)
            elif boxType == QtWidgets.QCheckBox:
                if value == '1': 
                    getattr(coluta,boxName).SetChecked(True)
                elif value == '0': 
                    getattr(coluta,boxName).SetChecked(False)
                else: 
                    coluta.showError('INSTRUMENT CONTROL: Error updating GUI')
            elif boxType == QtWidgets.QLabel:
                pass
            else:
                print('Could not find setting box {0}'.format(boxName))

    def getCurrentConfig(self,device):
        txt = getattr(self,device).getCurrentConfig()
        getattr(self.coluta,'textDisplayBox').document().setPlainText(txt)

class Setting:
    def __init__(self,configItems):
        self.names = []
        self.values = []

        for item in configItems:
            self.names.append(item[0])
            v = item[1].split(',')
            #v = item[1]
            #self.values.append(v)
            if len(v) == 1:
                self.values.append(v[0])
            else:
                self.values.append(v)

        self.updated = True
        self.settings = dict(zip(self.names,self.values))

    def getSetting(self,settingName):
        try:
            value = self.settings[settingName]
        except KeyError:
            print('Key Error: The device does not have the setting ' +settingName)

        return value

    def setSetting(self,settingName,settingValue):
        try:
            #print(settingValue)
            self.settings[settingName] = settingValue
            self.updated = True
        except KeyError:
            print('Cannot update setting')

class Device(Setting):
    def __init__(self,coluta,resourceManager,configItems):
        Setting.__init__(self,configItems)
        self.resourceManager = resourceManager
        self.coluta = coluta
        # self.device = self.connect()

    def connect(self):
        ipAddress = self.getSetting('ipAddress')
        print(ipAddress)
        try:
            device = self.resourceManager.open_resource("TCPIP::"+ipAddress)
            print(device.query("*IDN?"))
        except VisaIOError:
            self.coluta.showError('INSTRUMENT CONTROL: Cannot connect to IP address: {0}'.format(ipAddress))
        return device
    def disconnect(self):
        try:
            self.device.query("*IDN?")
            self.device.close()
        except VisaIOError:
            self.coluta.showError('INSTRUMENT CONTROL: Device is already closed')

    def clearStatus(self,device):
        self.device.write("*CLS")

    def updateSetting(self,settingName):
        try:
            boxName = settingName+'Box'
            value = getattr(self.coluta,boxName).document().toPlainText()
            #print('value: ',value)
            self.setSetting(settingName,value)
        except KeyError:
            self.coluta.showError('INSTRUMENT CONTROL: Invalid setting to update')

class keithley3321A(Device):
    def __init__(self,coluta,resourceManager,configItems):
        self.coluta = coluta
        Device.__init__(self,coluta,resourceManager,configItems)
        self.device = self.connect()
        self.voltageUnit = self.getSetting('voltageUnit')


    def applySin(self,address,channel):

        frequency = self.getSetting('signalFrequency').split(',')
        amplitude = self.getSetting('amplitude').split(',')
        #print(amplitude)
        #for amp,freq in zip(amplitude,frequency):
        for freq in frequency:
            for amp in amplitude:
                self.device.write("APPL:SIN "+str(freq)+"MHZ, "+str(amp)+"V")
                time.sleep(1)
                if self.coluta.pOptions.debug:
                    print('INSTRUMENT -> Frequency: {0}, Amplitude: {1}'.format(freq,amp))
                # print(amp,freq)
                # self.coluta.taEkeSamples(address,channel,voltage=amp,frequency=freq)
                self.coluta.takeDual(voltage=amp+' '+self.voltageUnit,frequency=freq+' MHz')
                time.sleep(1)

    def setVoltageUnitRMS(self):
        self.device.write("VOLT:UNIT Vrms")

    def getCurrentConfig(self):
        return self.device.query("APPL?")

    def getCurrentVolt(self):
        return float(self.device.query("VOLT?"))

    def getCurrentFreq(self):
        return float(self.device.query("FREQ?"))

    def setVoltageUnit(self):
        unit = getattr(self.coluta,'voltageUnitBox').document().toPlainText()
        self.voltageUnit = unit
        self.setSetting('voltageUnit',unit)
        self.device.write("VOLT:UNIT "+unit)

def initializeInstrumentation(coluta):
    '''Import libraries and define relevant attributes for ColutaGUI.'''
    # Try to import VISA. If it fails, show warning and exit.
    try:
        import visa
    except:
        coluta.showError('INSTRUMENT: VISA not available. Unable to initialize.')
        return

    # Setup instance of InstrumentControl class
    coluta.IC = InstrumentControl(coluta,'./config/instrumentConfig.cfg')
    coluta.function_generator = coluta.IC.function_generator

    # define the buttons on the Instrumentation tab
    coluta.ipAddressBox.textChanged.connect(lambda:coluta.updateIpAddress('function_generator'))
    coluta.connectInstrumentButton.clicked.connect(lambda:coluta.function_generator.connect())
    coluta.takeSamplesColutaButton_2.clicked.connect(lambda:coluta.function_generator.applySin(6,'coluta'))
    coluta.takeSamplesAD9650Button_2.clicked.connect(lambda:coluta.function_generator.applySin(1,'ad9650'))
    coluta.signalFrequencyBox.textChanged.connect(lambda:coluta.function_generator.updateSetting('signalFrequency'))
    coluta.rampFrequencyBox.textChanged.connect(lambda:coluta.function_generator.updateSetting('rampFrequency'))
    coluta.amplitudeBox.textChanged.connect(lambda:coluta.function_generator.updateSetting('amplitude'))
    coluta.offsetBox.textChanged.connect(lambda:coluta.function_generator.updateSetting('offset'))
    coluta.getCurrentConfigButton.clicked.connect(lambda:coluta.IC.getCurrentConfig('function_generator'))
    coluta.setVoltageUnitButton.clicked.connect(lambda:coluta.function_generator.setVoltageUnit())

def updateIpAddress(colutaGUI,device):
    try:
        colutaGUI.IC.IPaddress = colutaGUI.ipAddressBox.toPlainText()
    except Exception:
        colutaGUI.IC.IPaddress = '192.168.1.212'
    colutaGUI.IC.updateSetting(device,'ipAddress')
