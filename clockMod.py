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

def writeToHDF5(tables):

  fileName = 'clockScanColuta1319.hdf5'
  out_file = h5py.File(fileName,'w')
  print("Opening hdf5 file: "+ fileName)

  for coluta in tables.keys():
      out_file.create_group(coluta)
      for ch in tables[coluta].keys():
          out_file.create_dataset(coluta+"/Channel"+ch[-1], data=tables[coluta][ch])

  out_file.close()  
  print("Closing HDF5")

def scanClocks(GUI,colutas): 
    """ Scan all clock parameters """
    with open('config/colutaLpGBTMapping.txt','r') as f:
        mapping = pyjson5.load(f)
        #lpgbtRegDict = mapping[coluta]

    channels = ['ch'+str(i) for i in range(1,9)]
    channelSerializers = {channels[i]:bin(i)[2:].zfill(3) for i in range(0,8)}
    upper = 16

    i2cLabels = {}
    chanNames = {}
    valid = {}
    LPGBTPhase = {}
    for coluta in colutas:
        colutaChip = GUI.chips[coluta]
        i2cLabels[coluta] = colutaChip.i2cAddress[6:10]
        colutaNum = int(coluta[6:])
        chanNum = colutaNum*4-1
        chanNames[coluta] = ['channel'+str(chanNum-i).zfill(3) for i in range (0,4)]

    for coluta in colutas:
        i2cLabel = i2cLabels[coluta]
        valid[coluta] = {}
        LPGBTPhase[coluta] = {}
        for chn in channels:
            sertest_true = '1010'+i2cLabel+channelSerializers[chn]+'01001'  # correct serializer mode
            sertest_repl = sertest_true*2
            sertest_valid = [sertest_repl[i:(16+i)] for i in range (0,16)]  # valid iterations of serializer mode to be corrected by lpgbt phase
            valid[coluta][chn] = sertest_valid[:]
            LPGBTPhase[coluta][chn] = [[] for i in range(0,upper)]  #lpGBT phase result
    #for coluta in colutas:
    #    for chn in channelSerializers.keys():
    #        print(hex(int(valid[coluta][chn][1],2)))
    #return

    # is serializer the same across all samples?
    isStable_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

    # is serializer correct despite phase?
    isValid_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

    for delay_idx in range(0,upper):
        for coluta in colutas:
            sendInversionBits(GUI, delay_idx, coluta)

        for lpgbt_idx in range(0,upper):
            value = (lpgbt_idx<<4)+2
            for coluta in colutas:
                for lpgbt in mapping[coluta].keys():
                    registers = mapping[coluta][lpgbt]
                    print(lpgbt, registers)
                    for reg in registers:
                        GUI.writeToLPGBT(lpgbt, reg, [value], True)
            GUI.takeTriggerData('clockScan')
            print("Opening run", str(GUI.runNumber).zfill(4))
            datafile = h5py.File('Runs/run'+str(GUI.runNumber).zfill(4)+'.hdf5','r')
            m = str(len(datafile.keys())-1).zfill(3)
            print(m)
            d = datafile.get('Measurement_'+m)

            for coluta in colutas:  
                samples = {}
                samples['ch8'] = np.array(d[chanNames[coluta][0]]['lo']['samples'])
                samples['ch7'] = np.array(d[chanNames[coluta][0]]['hi']['samples'])
                samples['ch6'] = np.array(d[chanNames[coluta][1]]['hi']['samples'])
                samples['ch5'] = np.array(d[chanNames[coluta][1]]['lo']['samples'])
                samples['ch4'] = np.array(d[chanNames[coluta][2]]['lo']['samples'])
                samples['ch3'] = np.array(d[chanNames[coluta][2]]['hi']['samples'])
                samples['ch2'] = np.array(d[chanNames[coluta][3]]['hi']['samples'])
                samples['ch1'] = np.array(d[chanNames[coluta][3]]['lo']['samples'])

                for ch in channels:
                    #frame_list = [chunk[64:80] for chunk in repeats]
                    binary_list = [''.join([str(x) for x in samples[ch].tolist()[i]]) for i in range(0,samples[ch].shape[0])]
                    isStable = (len(set(binary_list)) == 1)  # test if data is stable
                    isStable_list[coluta][ch].append(isStable)
                    isValid = set(binary_list).issubset(valid[coluta][ch]) # test if data is a valid serializer pattern
                    isValid_list[coluta][ch].append(isValid)
                    if isStable and isValid:
                        phase = valid[coluta][ch].index(binary_list[0])
                    else:
                        phase = -1
                    LPGBTPhase[coluta][ch][delay_idx].append(phase) 

            datafile.close()

    
    headers = [f'{i}\n' for i in range(0,upper)]
    headers.insert(0,"xPhaseSelect -> \n INV/DELAY640 ")
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    for coluta in colutas:
        with open("clockScan"+coluta+".txt", "w") as f:
            for ch in channels:
                f.write("Channel "+ch[-1]+"\n")
                prettyTable = tabulate(LPGBTPhase[coluta][ch], headers, showindex = "always", tablefmt="psql")
                f.write(prettyTable)
                f.write("\n \n")

    writeToHDF5(LPGBTPhase)
    print("Finished Clock Scan")

