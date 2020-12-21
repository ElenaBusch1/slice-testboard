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

def checkAllVoltages(GUI):
    """ Loops through all voltages to fill GUI """
    checkVoltages(GUI, 3, 'lpgbt13')

def checkVoltages(GUI, adc, lpgbt, tempEnable=False):
    """ Checks voltage on given ADC """
    chip = GUI.chips[lpgbt] 
    ICEC_CHANNEL = 1
    adcselect = 0x111
    adcconfig = 0x113 
    vrefcntr = 0x01c
    adcstatusH = 0x1b8
    adcstatusL = 0x1b9
    vref = 0.9
    CURDACChn = 0x6b
    CURDACSelect = 0x6a
    DACConfigH = 0x68
    
    #FOR TEMP - CURDACChn, CURDACEnable, CURDACSelect[7:0]
    if tempEnable == True:
        # set current value
        GUI.writeToLPGBT(lpgbt, CURDACSelect, [int('00001000', 2)])

        # enable DAC current
        GUI.writeToLPGBT(lpgbt, DACConfigH, [int('01000000',2)])

        # connect to ADC
        GUI.writeToLPGBT(lpgbt, CURDACChn, [1<<adc])

    # configure input multiplexers to measure ADC0 in signle ended modePins
    # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
    # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
    GUI.writeToLPGBT(lpgbt, adcselect, [adc<<4+int('1111', 2)])

    # enable ADC core and set gain of the differential amplifier
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000100', 2)])

    # enable internal voltage reference
    GUI.writeToLPGBT(lpgbt, vrefcntr, [int('10000000', 2)])

    # wait until voltage reference is stable
    time.sleep(0.01)

    # start ADC convertion
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('10000100', 2)])
    status = False
    attempt = 0
    while not status and attempt < 10:
        readback = GUI.readFromLPGBT(lpgbt, adcstatusH, 1)
        status = readback[0] & 0x40
        attempt += 1
        if attempt == 10:
            print("Failed to read voltage after 10 attemps - giving up")

    adcValueH = readback[0]
    adcValueL = GUI.readFromLPGBT(lpgbt, adcstatusL, 1)[0]
    print("ADC Value H", adcValueH, "ADC Value L", adcValueL)

    # clear the convert bit to finish the conversion cycle
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000100', 2)])

    if tempEnable == True:
        # disable DAC current
        GUI.writeToLPGBT(lpgbt, DACConfigH, [int('00000000',2)])

    # if the ADC is not longer needed you may power-down the ADC core and the reference voltage generator
    GUI.writeToLPGBT(lpgbt, vrefcntr, [int('00000000', 2)])
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000000', 2)])

def checkVoltagesTest(GUI):
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

def checkAllTemps(GUI):
    temperatures = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'B1', 'B2', 'B3', 'B4', 'VTRx3', 'VTRx4', 'VTRx5', 'VTRx6']
    for temp in temperatures:
        lpgbt = GUI.powerSettings[temp][0]
        adc = GUI.powerSettings[temp][1]
        adcH, adcL = checkVoltages(GIU, adc, lpgbt, True)
        adcCounts = adcH<<8 + adcL
        tempVal = (adcCounts - 486.2)/2.105
        boxName = 'temperature'+temp+'Box'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print('Bad box name powerMod/checkAllTemps')
            return
        if isinstance(box, QtWidgets.QPlainTextEdit):
            decimalString = str(tempVal)
            box.document().setPlainText(decimalString)
        else:
            print('Bad box name powerMod/checkAllTemps')


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
