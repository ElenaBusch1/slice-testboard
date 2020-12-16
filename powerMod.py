from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from datetime import datetime
import time

def enableDCDCConverter():
    chip = self.chips["lpgbt12"]

    piodirl = '00010100'
    piooutl = '00010100'
    piodrivestrengthl = '00010100'

    #data = ''.join([f'{0Xaa:08b}' for i in range(1,96)])
    data = ['00001000', piodirl, '00001000', piooutl, '00000000', '00000000', '00000000', '00000000', '00001000', piodrivestrengthl]
    dataToSend = [int(val,2) for val in data]

    writeToLpGBT(int(chip.i2cAddress, 2), 0x052, dataToSend, ICEC_CHANNEL = 0)

    chip2 = self.chips['lpgbt13']

    piodirl = '00011100'
    piooutl = '00011100'
    piodrivestrengthl = '00011100'

    data2 = ['00000000', piodirl, '00000000', piooutl, '00000000', '00000000', '00000000', '00000000', '00000000', piodrivestrengthl]
    dataToSend2 = [int(val,2) for val in data2]

    writeToLpGBT(int(chip2.i2cAddress, 2), 0x052, dataToSend2, ICEC_CHANNEL = 1)

def checkVoltages(GUI):
    chip = GUI.chips["lpgbt13"] 
    ICEC_CHANNEL = 1
    adcselect = 0x111
    adcconfig = 0x113 
    vrefcntr = 0x01c
    adcstatusH = 0x1b8
    adcstatusL = 0x1b9
    vref = 0.9
    #FOR TEMP - CURDACChn, CURDACEnable, CURDACSelect[7:0]
    # configure input multiplexers to measure ADC0 in signle ended modePins
    # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
    # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
    writeToLpGBT(int(chip.i2cAddress, 2), adcselect, [int('00111111', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # enable ADC core and set gain of the differential amplifier
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # enable internal voltage reference
    writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('10000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # wait until voltage reference is stable
    time.sleep(0.01)

    # start ADC convertion
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('10000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)
    status = False
    attempt = 0
    while not status and attempt < 10:
        readback = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusH, 1, ICEC_CHANNEL=ICEC_CHANNEL)
        status = readback[0] & 0x40
        attempt += 1
        if attempt == 10:
            print("Failed to read voltage after 10 attemps - giving up")

    adcValueH = readback[0]
    adcValueL = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusL, 1, ICEC_CHANNEL=ICEC_CHANNEL)[0]
    print("ADC Value H", adcValueH, "ADC Value L", adcValueL)

    # clear the convert bit to finish the conversion cycle
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # if the ADC is not longer needed you may power-down the ADC core and the reference voltage generator
    writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('00000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

def checkAllTemps():
    adc5H, adc5L = checkTemp(5, 'lpgbt12')
    
    checkTemp()

def checkTemp(adc, lpgbt):

    chip = self.chips[lpgbt]
    adcselect = 0x111
    adcconfig = 0x113 
    vrefcntr = 0x01c
    adcstatusH = 0x1b8
    adcstatusL = 0x1b9
    vref = 0.9
    #FOR TEMP - CURDACChn, CURDACEnable, CURDACSelect[7:0]
    # configure input multiplexers to measure ADC0 in single ended modePins
    # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
    # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
    writeToLpGBT(int(chip.i2cAddress, 2), adcselect, [int('11101111', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # enable ADC core and set gain of the differential amplifier
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # enable internal voltage reference
    writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('10000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # wait until voltage reference is stable
    time.sleep(0.01)

    # start ADC convertion
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('10000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)
    status = False
    attempt = 0
    while not status and attempt < 10:
        readback = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusH, 1, ICEC_CHANNEL=ICEC_CHANNEL)
        status = readback[0] & 0x40
        attempt += 1
        if attempt == 10:
            print("Failed to read voltage after 10 attemps - giving up")

    adcValueH = readback[0]
    adcValueL = readFromLpGBT(int(chip.i2cAddress, 2), adcstatusL, 1, ICEC_CHANNEL=ICEC_CHANNEL)[0]
    print("ADC Value H", adcValueH, "ADC Value L", adcValueL)

    # clear the convert bit to finish the conversion cycle
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000100', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    # if the ADC is not longer needed you may power-down the ADC core and the reference voltage generator
    writeToLpGBT(int(chip.i2cAddress, 2), vrefcntr, [int('00000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)
    writeToLpGBT(int(chip.i2cAddress, 2), adcconfig, [int('00000000', 2)], ICEC_CHANNEL=ICEC_CHANNEL)

    return adcValueH, adcValueL
