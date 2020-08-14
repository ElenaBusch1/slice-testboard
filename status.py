"""Module for storing, reading, and writing status bits

name: status.py
author: C.D. Burton
email: burton@utexas.edu
date: 8 September 2018
"""
import serialMod
import time


class Status:
    """Status class definition."""

    def __init__(self, GUI, io):
        self.GUI = GUI
        # general bits
        self.softwareReset = 0
        self.colutaReset = 0
        self.pulseCommand = 0
        self.resetTrigger = 0
        self.readStatus = 0
        # fifo A bits
        self.fifoAOperation = 0
        self.fifoACounter = 0
        self.chipAddress = 0
        # start bits
        self.startFifoAOperation = 0
        self.startControlOperation = 0
        self.startMeasurement = 0

        # Which VTRx+ this instance of Status will be communicating with
        self.io = io

    def read(self):
        # Status words. status1 -> status6
        return [254,
                (self.colutaReset << 5) + (self.chipAddress << 2) + (self.fifoAOperation << 0),
                self.fifoACounter & 255,
                self.fifoACounter >> 8,
                (self.readStatus << 7) +
                 (self.startFifoAOperation << 6) +
                 (self.softwareReset << 5) +
                 (self.resetTrigger << 3) +
                 (self.startMeasurement << 2) +
                 (self.pulseCommand << 1) +
                 (self.startControlOperation << 0),
                255]

    def send(self):
        integerStatus = self.read()
        serialMod.writeToChip(self.GUI, self.io, integerStatus)

    # Ray Xu Feb 23, 2018: perform coluta reset
    # This is done by bringing status byte 2, bit 5 to high state then back to low state
    # Hard-coded for the time being (radn run)
    def sendColutaReset(self):
        print('Hard reset ... ')
        # coluta.logger.addEntry('ERROR','HARD RESET')
        self.colutaReset = 1
        self.send()
        time.sleep(0.1)
        self.colutaReset = 0
        self.send()

    # Operation functions. Operations are triggered on the rising edge, so one
    # needs to reset the flag after sending the command
    def sendFifoAOperation(self, operation, counter, address=0):
        # set the bits and flags
        self.fifoAOperation = operation
        self.fifoACounter = counter
        self.startFifoAOperation = 1
        self.chipAddress = address
        # send to the chip
        self.send()
        # reset the bits and flags
        self.fifoAOperation = 0
        self.fifoACounter = 0
        self.startFifoAOperation = 0
        self.chipAddress = 0

    def sendStartControlOperation(self, operation=0, address=0):
        self.fifoAOperation = operation
        self.chipAddress = address
        self.startControlOperation = 1
        self.send()
        self.fifoAOperation = 0
        self.chipAddress = 0
        self.startControlOperation = 0

    def sendStartMeasurement(self):
        self.startMeasurement = 1
        self.send()
        self.startMeasurement = 0

    def sendSoftwareReset(self):
        self.softwareReset = 1
        self.send()
        self.softwareReset = 0

    def sendI2Ccommand(self):
        self.startControlOperation = 1
        self.fifoAOperation = 1
        self.send()
        self.startControlOperation = 0
        self.fifoAOperation = 0

    def updatePulseDelay(self):
        self.resetTrigger = 1 if self.GUI.triggerResetTriggerDelayBox.isChecked() else 0
        self.pulseCommand = 1 if self.GUI.triggerDecrementDelayCounterBox.isChecked() else 0
        self.startMeasurement = 1
        self.send()
        self.startMeasurement = 0
        self.resetTrigger = 0
        self.pulseCommand = 0

    def initializeUSB(self):
        integerStatus = [255, 255, 255, 255, 255, 255]
        serialMod.writeToChip(self.GUI, self.io, integerStatus)

    def readbackStatus(self):
        self.readStatus = 1
        self.send()
        self.readStatus = 0

    def sendCalibrationPulse(self):
        self.send()
        self.resetTrigger = 1
        self.startMeasurement = 1
        self.send()
        self.resetTrigger = 0
        self.startMeasurement = 0
    # end Status
