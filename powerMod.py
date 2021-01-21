from flxMod import icWriteToLpGBT as writeToLpGBT
from flxMod import icReadLpGBT as readFromLpGBT
from datetime import datetime
from vref import vref as vREF
import time
import numpy as np

#vref = 0.9
IDAC = 106

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
    displayADCBox = getattr(GUI, 'displayADCCountsVoltBox')
    for volt in GUI.voltageSettings.keys():
        ## Check if voltage is selected
        selectBoxName = volt+"SelectBox"
        try:
            selectBox = getattr(GUI, selectBoxName)
        except AttributeError:
            print('Bad select box name powerMod/checkAllVoltages')
            continue
        if not selectBox.isChecked():
            continue
        ## Find correct lpGBT and ADC pin
        print(volt)
        lpgbt = GUI.voltageSettings[volt][0]
        adc = GUI.voltageSettings[volt][1]
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        ## Read Voltages
        #voltage = int(adc)
        ADC_INP_INN = (int(adc)<<4)+int('1111',2)
        adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, ADC_INP_INN,False)
        #print(adcH, adcL)
        #print(int(bin(adcH)[7:9],2)<<8, adcL)
        ## Convert ADC counts to decimal
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        #print(adcCounts)
        ## Apply scale factors
        ## old voltage calc
        #voltage = adcCounts*(vref*0.5/512)
        ## new voltage calc
        vref = vREF[lpgbt][int(adc)]
        voltage = (vref/1024)*adcCounts
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
        
        ## Update GUI
        boxName = volt+'Box'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print('Bad box name powerMod/checkAllVoltages')
            continue
        if displayADCBox.isChecked():
            box.document().setPlainText(f'{scaledVoltage:.2f} ({adcCounts})')
        else:
            box.document().setPlainText(f'{scaledVoltage:.2f}')


def checkAllTemps(GUI):
    #temperatures = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'B1', 'B2', 'B3', 'B4', 'VTRx3', 'VTRx4', 'VTRx5', 'VTRx6']
    #vref = 0.95
    #IDAC = 200
    resistorDividerMainPS24V = 40.322
    resistorDividerMainPS48V = 81.508
    IDACCalibration = 0.272
    displayADCBox = getattr(GUI, 'displayADCCountsTempBox')
    for temp in GUI.temperatureSettings.keys():
        ## Check if voltage is selected
        selectBoxName = temp+"TempSelectBox"
        try:
            selectBox = getattr(GUI, selectBoxName)
        except AttributeError:
            print('Bad select box name powerMod/checkAllTemps')
            continue
        if not selectBox.isChecked():
            continue
        ## Find correct lpGBT and ADC pin
        lpgbt = GUI.temperatureSettings[temp][0]
        adc = GUI.temperatureSettings[temp][1]
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        ## Read Temperature
        #tempVal = int(adc)
        print(temp)
        ADC_INP_INN = (int(adc)<<4)+int('1111',2)
        if temp in ['VTRx3', 'VTRRx4', 'VTRx5', 'VTRx6']:
            IDACCur = 10
        else:
            IDACCur = IDAC
        adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, ADC_INP_INN, True, 0, IDACCur)
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        ## Convert ADC counts to temp
        #tempVal = (adcCounts - 486.2)/2.105
        vref = vREF[lpgbt][int(adc)]
        voltage = adcCounts*(vref/1024)
        resistivity = IDACCalibration*voltage/(IDAC*1E-6)
        tempVal = computeTemp(resistivity)
        #print("ADC Counts: ", adcCounts)
        #print("voltage: ", voltage)
        #print("resistivity: ", resistivity)
        #print("temp: ", tempVal)
        #continue
        #tempVal = (resistivity - 1000)/3.79
        ## Update GUI
        boxName = 'temperature'+temp+'Box'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print("Bad boxname powerMod/ checkAllTemps")
            continue
        #box.document().setPlainText(f'{tempVal:.1f}')
        if displayADCBox.isChecked():
            box.document().setPlainText(f'{tempVal:.2f} ({adcCounts})')
        else:
            box.document().setPlainText(f'{tempVal:.2f}')
    #return
    # write 14 to ADCInPSelect[3:0] - internal lpgbt temp
    lpgbts = ['lpgbt'+str(x) for x in range(9,17)]
    for lpgbt in lpgbts:
        ## Check if voltage is selected
        selectBoxName = lpgbt+"TempSelectBox"
        try:
            selectBox = getattr(GUI, selectBoxName)
        except AttributeError:
            print('Bad select box name powerMod/checkAllTemps')
            continue
        if not selectBox.isChecked():
            continue
        ## Read temps
        print(lpgbt)
        if lpgbt in ['lpgbt9', 'lpgbt10', 'lpgbt11']:
            GUI.lpgbtReset("lpgbt12")
        elif lpgbt in ['lpgbt14', 'lpgbt15', 'lpgbt16']:
            GUI.lpgbtReset("lpgbt13")
        adc = '14'
        ADC_INP_INN = (int(adc)<<4)+int('1111',2)
        adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, ADC_INP_INN, False)
        adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
        tempVal = (adcCounts - 486.2)/2.105
        #tempVal = lpgbt
        boxName = lpgbt+'InternalTempBox'
        try:
            box = getattr(GUI, boxName)
        except AttributeError:
            print("Bad boxname powerMod/ checkAllTemps")
            continue
        if displayADCBox.isChecked():
            box.document().setPlainText(f'{tempVal:.2f} ({adcCounts})')
        else:
            box.document().setPlainText(f'{tempVal:.2f}')


def checkVoltages(GUI, adc, lpgbt, ADC_INP_INN, tempEnable=False, vrefTune = 0, IDACCur = 106):
    """ Checks voltage on given ADC """
    chip = GUI.chips[lpgbt] 
    ICEC_CHANNEL = 1
    adcselect = 0x111
    adcMON = 0x112
    adcconfig = 0x113 
    vrefcntr = 0x01c
    adcstatusH = 0x1b8
    adcstatusL = 0x1b9
    #vref = 0.9
    CURDACChn = 0x6b
    CURDACSelect = 0x6a
    DACConfigH = 0x68
    #FOR TEMP - CURDACChn, CURDACEnable, CURDACSelect[7:0]
    if tempEnable == True:
        # set current value - 200 or less, in microamps 
        GUI.writeToLPGBT(lpgbt, CURDACSelect, [IDACCur], disp=GUI.READBACK)

        # enable DAC current
        GUI.writeToLPGBT(lpgbt, DACConfigH, [int('01000000',2)], disp=GUI.READBACK)

        # connect to ADC
        GUI.writeToLPGBT(lpgbt, CURDACChn, [1<<adc], disp=GUI.READBACK)
    # return
    # configure input multiplexers to measure ADC0 in signle ended modePins
    # ADCInPSelect = ADCCHN_EXT0 ; (4'd0)
    # ADCInNSelect = ADCCHN_VREF2 ; (4'd15)
    ## Normal Input
    GUI.writeToLPGBT(lpgbt, adcselect, [ADC_INP_INN], disp=GUI.READBACK)
    ## vrefScan (method #1)
    #GUI.writeToLPGBT(lpgbt, adcselect, [int('11001111', 2)])
    ## vrefCalibrate (method #2)
    #GUI.writeToLPGBT(lpgbt, adcselect, [int('11111111', 2)])

    # enable ADC core and set gain of the differential amplifier
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000100', 2)], disp=GUI.READBACK)

    # enable internal voltage reference
    GUI.writeToLPGBT(lpgbt, vrefcntr, [(int('10',2)<<6)+vrefTune], disp=GUI.READBACK)

    # enable resistive divider for VDD probing.
    GUI.writeToLPGBT(lpgbt, adcMON, [int('00010000', 2)], disp=GUI.READBACK)

    # wait until voltage reference is stable
    time.sleep(0.01)

    # start ADC convertion
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('10000100', 2)], disp=GUI.READBACK)
    status = False
    attempt = 0
    while not status and attempt < 10:
        readback = GUI.readFromLPGBT(lpgbt, adcstatusH, 1, disp=GUI.READBACK)
        status = readback[0] & 0x40
        attempt += 1
        if attempt == 10:
            print("Failed to read voltage after 10 attemps - giving up")

    adcValueH = readback[0]
    adcValueL = GUI.readFromLPGBT(lpgbt, adcstatusL, 1, disp=GUI.READBACK)[0]
    #print("ADC Value H", adcValueH, "ADC Value L", adcValueL)

    # clear the convert bit to finish the conversion cycle
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000100', 2)], disp=GUI.READBACK)

    if tempEnable == True:
        # disable DAC current
        GUI.writeToLPGBT(lpgbt, DACConfigH, [int('00000000',2)], disp=GUI.READBACK)

    # if the ADC is not longer needed you may power-down the ADC core and the reference voltage generator
    GUI.writeToLPGBT(lpgbt, vrefcntr, [int('00000000', 2)], disp=GUI.READBACK)
    GUI.writeToLPGBT(lpgbt, adcconfig, [int('00000000', 2)], disp=GUI.READBACK)
    return adcValueH, adcValueL

def selectAllVoltages(GUI, value):
    for volt in GUI.voltageSettings.keys():
        boxName = volt+"SelectBox"
        GUI.updateBox(boxName,value)

def selectAllTemps(GUI, value):
    for temp in GUI.temperatureSettings.keys():
        boxName = temp+"TempSelectBox"
        GUI.updateBox(boxName,value)
    lpgbts = ['lpgbt'+str(x) for x in range(9,17)]
    for lpgbt in lpgbts:
        boxName = lpgbt+"TempSelectBox"
        GUI.updateBox(boxName,value)    

def vrefTest(GUI):
    lpgbts = ['lpgbt'+str(x) for x in range(9,17)]
    adcs = [str(x) for x in range(0,8)]
    tables = {}
    headers = ["Channel", "Counts", "VREF"]
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    for lpgbt in lpgbts:
        vref = [[] for i in range(0,8)]
        for adc in adcs:
            adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, int('11001111',2), False)
            adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
            voltage = (1.2*0.42)/(adcCounts/1024)
            #print(lpgbt,adc,adcCounts,voltage)
            vref[int(adc)].append(adc)
            vref[int(adc)].append(adcCounts)
            vref[int(adc)].append(voltage)
        table = tabulate(vref, headers, showindex = "always", tablefmt="psql") 
        print(lpgbt)
        print(table)
        tables[lpgbt] = table

    with open("vrefScan.txt", "w") as f:
        for lpgbt in lpgbts:
            table = tables[lpgbt]
            f.write(lpgbt+"\n")
            f.write(table)
            f.write("\n \n")
    #with open("vref.py", "w") as p:
    #    for lpgbt in lpgbts:
    #        string = 
            
def vrefCalibrate(GUI):
    lpgbts = ['lpgbt'+str(x) for x in range(14,17)]
    adcs = [str(x) for x in range(0,8)]
    tables = {}
    headers = ["Channel", "vrefTune", "Counts", "VREF"]
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    vrefTune_log = open("vrefTune_log.txt", "w")
    for lpgbt in lpgbts:
        vref = [[] for i in range(0,8)]
        vrefTune_log.write("lpGBT, Channel, vrefTune, adcCounts, voltage \n")
        for adc in adcs:
            vrefTune = 0
            while vrefTune < 64:
                adcH, adcL = checkVoltages(GUI, int(adc), lpgbt, int('11111111',2), False, vrefTune)
                adcCounts = (int(bin(adcH)[7:9],2)<<8) + adcL
                voltage = (1.2*0.42)/(adcCounts/1024)
                print(lpgbt,adc,vrefTune,adcCounts,voltage)
                vrefTune_log.write(lpgbt+"  "+adc+"  "+str(vrefTune)+"  "+str(adcCounts)+"  "+str(voltage)+"\n")
                if adcCounts == 511 or adcCounts == 512 or adcCounts == 513:
                    break
                vrefTune += 1
            vref[int(adc)].append(adc)
            vref[int(adc)].append(vrefTune)
            vref[int(adc)].append(adcCounts)
            vref[int(adc)].append(voltage)
        table = tabulate(vref, headers, showindex = "always", tablefmt="psql") 
        print(lpgbt)
        print(table)
        tables[lpgbt] = table
        vrefTune_log.write("\n \n")

    vrefTune_log.close()
    with open("vrefCalibrate14-15-16.txt", "w") as f:
        for lpgbt in lpgbts:
            table = tables[lpgbt]
            f.write(lpgbt+"\n")
            f.write(table)
            f.write("\n \n")

def computeTemp(R):
    # R = R0(1+At+Bt^2) solve for t
    # Find A/B/R0 values and equation in de_datasheet_pt1000 (ask Jaro)
    R0 = 1000
    A = 3.9083E-3
    B = -5.775E-7
    a = R0*B
    b = R0*A
    c = R0-R
    dis = b**2-4*a*c
    ans1 = (-b - np.sqrt(dis))/(2*a)
    ans2 = (-b + np.sqrt(dis))/(2*a)
    return ans2
