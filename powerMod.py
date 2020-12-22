from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from datetime import datetime
import time

vref = 0.9

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
    #vref = 0.9
    resistorDivider1p2 = 2
    resistorDivider2p5 = 3.01
    resistorDividerRSSI = 3.21
    resistorDividerMainPS24V = 40.322
    points1p2Volts = ["VDD", "1p2"]
    points2p5Volts = ["2p5"]
    for volt in GUI.voltageSettings.keys():
        print(volt)
        lpgbt = GUI.voltageSettings[volt][0]
        adc = GUI.voltageSettings[volt][1]
        #if lpgbt != 'lpgbt12' and lpgbt != 'lpgbt13' and lpgbt != 'lpgbt14' and lpgbt != 'lpgbt11':
        #    continue
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        #voltage = int(adc)
        adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, False)
        print(adcH, adcL)
        print(int(bin(adcH)[7:9],2)<<8, adcL)
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        print(adcCounts)
        voltage = adcCounts*(vref*0.5/512)
        if (volt.find("2p5") > -1):
            scaledVoltage = voltage*resistorDivider2p5
        elif (volt.find("1p2") > -1) or (volt.find("VDD") > -1):
            scaledVoltage = voltage*resistorDivider1p2
        elif (volt.find("RSSI") > -1):
            scaledVoltage = voltage*resistorDividerRSSI
        elif (volt.find("MAIN") > -1):
            scaledVoltage = voltage*resistorDividerMainPS24V
        else:
            scaledVoltage = voltage
        boxName = volt+'Box'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print('Bad box name powerMod/checkAllVoltages')
            continue
        box.document().setPlainText(f'{scaledVoltage:.3f}')


def checkAllTemps(GUI):
    #temperatures = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'B1', 'B2', 'B3', 'B4', 'VTRx3', 'VTRx4', 'VTRx5', 'VTRx6']
    #vref = 0.95
    IDAC = 200
    resistorDividerMainPS24V = 40.322
    resistorDividerMainPS48V = 81.508
    for temp in GUI.temperatureSettings.keys():
        #if temp != "T1":
        #    continue
        lpgbt = GUI.temperatureSettings[temp][0]
        adc = GUI.temperatureSettings[temp][1]
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        #tempVal = int(adc)
        print(adc, lpgbt)
        adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, True)
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        #tempVal = (adcCounts - 486.2)/2.105
        voltage = adcCounts*(vref*0.5/512)
        resistivity = voltage/(IDAC*1E-6)
        tempVal = (resistivity - 1000)/3.79
        boxName = 'temperature'+temp+'Box'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print("Bad boxname powerMod/ checkAllTemps")
            continue
        #box.document().setPlainText(f'{tempVal:.1f}')
        box.document().setPlainText(f'{tempVal:.1f} {voltage:.3f} {adcCounts}')
    
    #return
    # write 14 to ADCInPSelect[3:0] - internal lpgbt temp
    lpgbts = ['lpgbt'+str(x) for x in range(9,17)]
    for lpgbt in lpgbts:
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        adcH, adcL = checkVoltages(GUI, 14, lpgbt, False)
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        tempVal = (adcCounts - 486.2)/2.105
        #tempVal = lpgbt
        boxName = lpgbt+'InternalTempBox'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print("Bad boxname powerMod/ checkAllTemps")
            continue
        box.document().setPlainText(f'{tempVal:.1f}')


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
        # set current value - 200 or less, in microamps 
        GUI.writeToLPGBT(lpgbt, CURDACSelect, [53])

        # enable DAC current
        GUI.writeToLPGBT(lpgbt, DACConfigH, [int('01000000',2)])

        # connect to ADC
        GUI.writeToLPGBT(lpgbt, CURDACChn, [1<<adc])
    # return
    # configure input multiplexers to measure ADC0 in signle ended modePins
    # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
    # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
    GUI.writeToLPGBT(lpgbt, adcselect, [(adc<<4)+int('1111', 2)])

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
    return adcValueH, adcValueL

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

