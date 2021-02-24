import h5py
import numpy as np
import pyjson5

def sendInversionBits(GUI, clock640, colutaName):
    binary = f'{clock640:04b}'
    inv640 = binary[0]
    delay640 = binary[1:] 
    GUI.chips[colutaName].setConfiguration("global", "INV640", inv640)
    print(f"Updated {colutaName} global, INV640: {inv640}")
    GUI.chips[colutaName].setConfiguration("global", "DELAY640", delay640)
    print(f"Updated {colutaName} global, DELAY640: {delay640}")

    GUI.writeToCOLUTAGlobal(colutaName)
 
def scanClocks(GUI,coluta): 
    """ Scan all clock parameters """
    with open('config/colutaLpGBTMapping.txt','r') as f:
        mapping = pyjson5.load(f)
        lpgbtRegDict = mapping[coluta]

    colutaChip = GUI.chips[coluta]
    i2cLabel = colutaChip.i2cAddress[6:10]
    print(i2cLabel)
    colutaNum = int(coluta[6:])
    chanNum = colutaNum*4-1
    chanNames = ['channel'+str(chanNum-i).zfill(3) for i in range (0,4)]
    print(chanNames)
    #return

    upper = 16
    ch1_sertest_true = '1010'+i2cLabel+'00001001'
    ch2_sertest_true = '1010'+i2cLabel+'00101001'
    ch3_sertest_true = '1010'+i2cLabel+'01001001'
    ch4_sertest_true = '1010'+i2cLabel+'01101001'
    ch5_sertest_true = '1010'+i2cLabel+'10001001'
    ch6_sertest_true = '1010'+i2cLabel+'10101001'
    ch7_sertest_true = '1010'+i2cLabel+'11001001'
    ch8_sertest_true = '1010'+i2cLabel+'11101001'

    ch1_sertest_repl = ch1_sertest_true*2
    ch2_sertest_repl = ch2_sertest_true*2
    ch3_sertest_repl = ch3_sertest_true*2
    ch4_sertest_repl = ch4_sertest_true*2
    ch5_sertest_repl = ch5_sertest_true*2
    ch6_sertest_repl = ch6_sertest_true*2
    ch7_sertest_repl = ch7_sertest_true*2
    ch8_sertest_repl = ch8_sertest_true*2
    ch1_sertest_valid = []
    ch2_sertest_valid = []
    ch3_sertest_valid = []
    ch4_sertest_valid = []
    ch5_sertest_valid = []
    ch6_sertest_valid = []
    ch7_sertest_valid = []
    ch8_sertest_valid = []
    LPGBTPhaseCh1_list = [[] for i in range(0,upper)]     # Value of correct lpGBT phase value or NaN if test signal is unstable or incorrect
    LPGBTPhaseCh2_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh3_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh4_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh5_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh6_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh7_list = [[] for i in range(0,upper)]
    LPGBTPhaseCh8_list = [[] for i in range(0,upper)]
    for idx in range(0, 16):
        ch1_sertest_valid.append(ch1_sertest_repl[idx:(16+idx)])
        ch2_sertest_valid.append(ch2_sertest_repl[idx:(16+idx)])
        ch3_sertest_valid.append(ch3_sertest_repl[idx:(16+idx)])
        ch4_sertest_valid.append(ch4_sertest_repl[idx:(16+idx)])
        ch5_sertest_valid.append(ch5_sertest_repl[idx:(16+idx)])
        ch6_sertest_valid.append(ch6_sertest_repl[idx:(16+idx)])
        ch7_sertest_valid.append(ch7_sertest_repl[idx:(16+idx)])
        ch8_sertest_valid.append(ch8_sertest_repl[idx:(16+idx)])

    for delay_idx in range(0,16):
        isStableCh1_list = []      # Is serializer test signal same across all samples?
        isStableCh2_list = []
        isStableCh3_list = []
        isStableCh4_list = []
        isStableCh5_list = []
        isStableCh6_list = []
        isStableCh7_list = []
        isStableCh8_list = []
        isValidCh1_list = []       # Is serializer test signal correct (despite word shift)?
        isValidCh2_list = []
        isValidCh3_list = []
        isValidCh4_list = []
        isValidCh5_list = []
        isValidCh6_list = []
        isValidCh7_list = []
        isValidCh8_list = []

        sendInversionBits(GUI, delay_idx, coluta)

        for lpgbt_idx in range(0,16):
            value = (lpgbt_idx<<4)+2
            for lpgbt in lpgbtRegDict.keys():
                registers = lpgbtRegDict[lpgbt]
                print(lpgbt, registers)
                for reg in registers:
                    GUI.writeToLPGBT(lpgbt, reg, [value], True)
            GUI.takeTriggerData('clockScan')
            print("Opening run", str(GUI.runNumber).zfill(4))
            datafile = h5py.File('Runs/run'+str(GUI.runNumber).zfill(4)+'.hdf5','r')
            m = str(len(datafile.keys())-1).zfill(3)
            print(m)
            d = datafile.get('Measurement_'+m)
            ch8 = np.array(d[chanNames[0]]['lo']['samples'])
            ch7 = np.array(d[chanNames[0]]['hi']['samples'])
            ch6 = np.array(d[chanNames[1]]['hi']['samples'])
            ch5 = np.array(d[chanNames[1]]['lo']['samples'])
            ch4 = np.array(d[chanNames[2]]['lo']['samples'])
            ch3 = np.array(d[chanNames[2]]['hi']['samples'])
            ch2 = np.array(d[chanNames[3]]['hi']['samples'])
            ch1 = np.array(d[chanNames[3]]['lo']['samples'])
            datafile.close()
            #frame_list = [chunk[64:80] for chunk in repeats]
            ch1_binary_list = [''.join([str(x) for x in ch1.tolist()[i]]) for i in range(0,ch1.shape[0])]
            ch2_binary_list = [''.join([str(x) for x in ch2.tolist()[i]]) for i in range(0,ch2.shape[0])]   
            ch3_binary_list = [''.join([str(x) for x in ch3.tolist()[i]]) for i in range(0,ch3.shape[0])]
            ch4_binary_list = [''.join([str(x) for x in ch4.tolist()[i]]) for i in range(0,ch4.shape[0])]
            ch5_binary_list = [''.join([str(x) for x in ch5.tolist()[i]]) for i in range(0,ch5.shape[0])]
            ch6_binary_list = [''.join([str(x) for x in ch6.tolist()[i]]) for i in range(0,ch6.shape[0])]
            ch7_binary_list = [''.join([str(x) for x in ch7.tolist()[i]]) for i in range(0,ch7.shape[0])]
            ch8_binary_list = [''.join([str(x) for x in ch8.tolist()[i]]) for i in range(0,ch8.shape[0])]

            ## Test if metastable out of consecutive samples
            isStableCh1 = (len(set(ch1_binary_list)) == 1)
            isStableCh2 = (len(set(ch2_binary_list)) == 1)
            isStableCh3 = (len(set(ch3_binary_list)) == 1)
            isStableCh4 = (len(set(ch4_binary_list)) == 1)
            isStableCh5 = (len(set(ch5_binary_list)) == 1)
            isStableCh6 = (len(set(ch6_binary_list)) == 1)
            isStableCh7 = (len(set(ch7_binary_list)) == 1)
            isStableCh8 = (len(set(ch8_binary_list)) == 1)
            isStableCh1_list.append(isStableCh1)
            isStableCh2_list.append(isStableCh2)
            isStableCh3_list.append(isStableCh3)
            isStableCh4_list.append(isStableCh4)
            isStableCh5_list.append(isStableCh5)
            isStableCh6_list.append(isStableCh6)
            isStableCh7_list.append(isStableCh7)
            isStableCh8_list.append(isStableCh8)
            ## Test if data output is correct
            isValidCh1 = set(ch1_binary_list).issubset(ch1_sertest_valid)
            isValidCh2 = set(ch2_binary_list).issubset(ch2_sertest_valid)
            isValidCh3 = set(ch3_binary_list).issubset(ch3_sertest_valid)
            isValidCh4 = set(ch4_binary_list).issubset(ch4_sertest_valid)
            isValidCh5 = set(ch5_binary_list).issubset(ch5_sertest_valid)
            isValidCh6 = set(ch6_binary_list).issubset(ch6_sertest_valid)
            isValidCh7 = set(ch7_binary_list).issubset(ch7_sertest_valid)
            isValidCh8 = set(ch8_binary_list).issubset(ch8_sertest_valid)
            isValidCh1_list.append(isValidCh1)
            isValidCh2_list.append(isValidCh2)
            isValidCh3_list.append(isValidCh3)
            isValidCh4_list.append(isValidCh4)
            isValidCh5_list.append(isValidCh5)
            isValidCh6_list.append(isValidCh6)
            isValidCh7_list.append(isValidCh7)
            isValidCh8_list.append(isValidCh8)
 
             # Find correct lpGBT phase. -99 -> invalid and unstable, -88 invalid, -77 unstable
            try:
                if isStableCh1 and isValidCh1:
                    LPGBTPhaseCh1 = ch1_sertest_valid.index(ch1_binary_list[0])
                else:
                    LPGBTPhaseCh1 = hex(int(ch1_binary_list[0],2))
                    #LPGBTPhaseCh1 = -99
                    #if isStableCh1:
                    #    LPGBTPhaseCh1 += 11
                    #if isValidCh1:
                    #    LPGBTPhaseCh1 += 22
                if isStableCh2 and isValidCh2:
                    LPGBTPhaseCh2 = ch2_sertest_valid.index(ch2_binary_list[0])
                else:
                    LPGBTPhaseCh2 = hex(int(ch2_binary_list[0],2))
                    #LPGBTPhaseCh2 = -99
                    #if isStableCh2:
                    #    LPGBTPhaseCh2 += '11'
                    #if isValidCh2:
                    #    LPGBTPhaseCh2 += '22'
                if isStableCh3 and isValidCh3:
                    LPGBTPhaseCh3 = ch3_sertest_valid.index(ch3_binary_list[0])
                else:
                    LPGBTPhaseCh3 = -99
                    if isStableCh3:
                        LPGBTPhaseCh3 += 11
                    if isValidCh3:
                        LPGBTPhaseCh3 += 22
                if isStableCh4 and isValidCh4:
                    LPGBTPhaseCh4 = ch4_sertest_valid.index(ch4_binary_list[0])
                else:
                    LPGBTPhaseCh4 = -99
                    if isStableCh4:
                        LPGBTPhaseCh4 += 11
                    if isValidCh4:
                        LPGBTPhaseCh4 += 22
                if isStableCh5 and isValidCh5:
                    LPGBTPhaseCh5 = ch5_sertest_valid.index(ch5_binary_list[0])
                else:
                    LPGBTPhaseCh5 = -99
                    if isStableCh5:
                        LPGBTPhaseCh5 += 11
                    if isValidCh5:
                        LPGBTPhaseCh5 += 22
                if isStableCh6 and isValidCh6:
                    LPGBTPhaseCh6 = ch6_sertest_valid.index(ch6_binary_list[0])
                else:
                    LPGBTPhaseCh6 = -99
                    if isStableCh6:
                        LPGBTPhaseCh6 += 11
                    if isValidCh6:
                        LPGBTPhaseCh6 += 22
                if isStableCh7 and isValidCh7:
                    LPGBTPhaseCh7 = ch7_sertest_valid.index(ch7_binary_list[0])
                else:
                    LPGBTPhaseCh7 = -99
                    if isStableCh7:
                        LPGBTPhaseCh7 += 11
                    if isValidCh7:
                        LPGBTPhaseCh7 += 22
                if isStableCh8 and isValidCh8:
                    LPGBTPhaseCh8 = ch8_sertest_valid.index(ch8_binary_list[0])
                else:
                    LPGBTPhaseCh8 = hex(int(ch8_binary_list[0],2))
                    #LPGBTPhaseCh8 = -99
                    #if isStableCh8:
                    #    LPGBTPhaseCh8 += '11'
                    #if isValidCh8:
                    #    LPGBTPhaseCh8 += '22'
            except:
                print('I could not synchronize with the COLUTA.  Please power cycle and restart GUI.')

            LPGBTPhaseCh1_list[delay_idx].append(LPGBTPhaseCh1)
            LPGBTPhaseCh2_list[delay_idx].append(LPGBTPhaseCh2)
            LPGBTPhaseCh3_list[delay_idx].append(LPGBTPhaseCh3)
            LPGBTPhaseCh4_list[delay_idx].append(LPGBTPhaseCh4)
            LPGBTPhaseCh5_list[delay_idx].append(LPGBTPhaseCh5)
            LPGBTPhaseCh6_list[delay_idx].append(LPGBTPhaseCh6)
            LPGBTPhaseCh7_list[delay_idx].append(LPGBTPhaseCh7)
            LPGBTPhaseCh8_list[delay_idx].append(LPGBTPhaseCh8)
    
    headers = [f'{i}\n' for i in range(0,16)]
    headers.insert(0,"xPhaseSelect -> \n INV/DELAY640 ")
    try:
        from tabulate import tabulate
        table8 = tabulate(LPGBTPhaseCh8_list, headers, showindex = "always", tablefmt="psql")
        print(table8)
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    table1 = tabulate(LPGBTPhaseCh1_list, headers, showindex = "always", tablefmt="psql")
    table2 = tabulate(LPGBTPhaseCh2_list, headers, showindex = "always", tablefmt="psql")
    table3 = tabulate(LPGBTPhaseCh3_list, headers, showindex = "always", tablefmt="psql")
    table4 = tabulate(LPGBTPhaseCh4_list, headers, showindex = "always", tablefmt="psql")
    table5 = tabulate(LPGBTPhaseCh5_list, headers, showindex = "always", tablefmt="psql")
    table6 = tabulate(LPGBTPhaseCh6_list, headers, showindex = "always", tablefmt="psql")
    table7 = tabulate(LPGBTPhaseCh7_list, headers, showindex = "always", tablefmt="psql")

    with open("clockScanColuta17.txt", "w") as f:
        f.write("Channel 1 \n")
        f.write(table1)
        f.write("\n \n")
        f.write("Channel 2 \n")
        f.write(table2)
        f.write("\n \n")
        f.write("Channel 3 \n")
        f.write(table3)
        f.write("\n \n")
        f.write("Channel 4 \n")
        f.write(table4)
        f.write("\n \n")
        f.write("Channel 5 \n")
        f.write(table5)
        f.write("\n \n")
        f.write("Channel 6 \n")
        f.write(table6)
        f.write("\n \n")
        f.write("Channel 7 \n")
        f.write(table7)
        f.write("\n \n")
        f.write("Channel 8 \n")
        f.write(table8)

def takeSamplesSimple():
    """Read and store output from VTRx+ 3 or 6"""
    if not self.isConnected and not self.pArgs.no_connect:
        self.showError("Board is not connected")
        return

    print("Reading data")
    dataByteArray = self.fifoAReadData("45")

    if self.pArgs.no_connect: return

    dataString = sliceMod.byteArrayToString(dataByteArray)
    dataStringChunks32 = "\n".join([dataString[i:i+32] for i in range(0, len(dataString), 32)])
    dataStringChunks16 = "\n".join([dataString[i:i+16] for i in range(0, len(dataString), 16)])
    #print(dataStringChunks16)
    if self.pArgs.debug: print(dataStringChunks16)

    return dataString
    #self.ODP.parseData(self.nSamples, dataString)
    #self.ODP.writeDataToFile()

def takeSamples(doDraw=True):
    """Read and store output data from LpGBT buffer"""

    doFFT = self.doFFTBox.isChecked()
    #saveHDF5 = self.saveHDF5Box.isChecked()
    csv = self.saveCSVBox.isChecked()
    # Take data and read from the FPGA
    if not self.isConnected: #and not self.pOptions.no_connect:
        self.showError('Chip is not connected.')
        return
    #self.updateStatusBar('Taking data')
    self.measurementTime = datetime.now().strftime("%y_%m_%d_%H_%M_%S.%f")
    
    # Read the data
    print("Reading data")
    dataByteArray = self.fifoAReadData("45")

    #if self.pOptions.no_connect: return
    #self.updateStatusBar('Writing data')
    # Display the data on the GUI window in groups of 32 bits and in groups on 16 bits on the 
    # terminal window for Jaro
    dataString = sliceMod.byteArrayToString(dataByteArray)
    dataStringByteChunks = "\n".join([dataString[i:i+32] for i in range(0,len(dataString),32)])
    dataStringByteChunks16 = "\n".join([dataString[i:i+16] for i in range(0,len(dataString),16)])
    #if self.debug: print(dataStringByteChunks16)
    #sectionLen = len(dataString)//self.nSamples
    sectionLen = 256
    print(len(dataString))
    print(sectionLen*self.nSamples)
    #print(sectionLen)
    repeats = [dataString[i:i+sectionLen] for i in range (0, len(dataString), sectionLen)]
    #print(repeats)
    dataStringCh78 = "\n".join([chunk[192:224] for chunk in repeats])
    #for chunk in repeats:
    #  print(chunk[192:224])

    with open("ch78_4000_samples.txt", "w") as f:
        f.write(dataStringCh78)
    #self.controlTextBox.setPlainText(dataStringCh78)
    self.controlTextBox.setPlainText(dataStringByteChunks)

    #self.ODP.parseData('coluta', self.nSamples,dataString)
    self.ODP.parseData(self.nSamples,dataString)
    #self.ODP.writeDataToFile(writeHDF5File=saveHDF5,writeCSVFile=csv)

    plotChip = self.plotChipBox.currentText().lower()
    plotChannel = self.plotChannelBox.currentText()
    channelsRead = getattr(self.ODP,plotChip).getSetting('data_channels')
    print("channels", channelsRead)
    # channelsRead = ['channel2','channel1']

    self.dataDisplay.resetData()
    #self.fftDisplay.resetData()

    if doDraw and plotChannel in channelsRead:
        print("Drawing")
        decimalDict = getattr(self.ODP,plotChip+'DecimalDict')
        adcData = decimalDict[plotChannel]
        self.dataDisplay.updateFigure(adcData,np.arange(len(adcData)))
        if doFFT:
            freq,psd,QA = colutaMod.doFFT(self,adcData)
            QAList = [plotChannel.upper(),
                      'ENOB: {:2f}'.format(QA['ENOB']),
                      'SNR: {:2f} dB'.format(QA['SNR']),
                      'SFDR: {:2f} dB'.format(QA['SFDR']),
                      'SINAD: {:2f} dB'.format(QA['SINAD'])]
            QAStr = '\n'.join(QAList)
            self.controlTextBox.setPlainText(QAStr)
            #self.fftDisplay.updateFigure(psd,freq)

    #self.updateStatusBar()
