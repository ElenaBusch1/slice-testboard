import h5py
import numpy as np
import pyjson5
from termcolor import colored

def sendInversionBits(GUI, clock640, colutaName):
    """ Change the clock register on the COLUTA """
    binary = f'{clock640:04b}' # convert to binary
    inv640 = binary[0]
    delay640 = binary[1:] 
    GUI.chips[colutaName].setConfiguration("global", "INV640", inv640)
    print(f"Updated {colutaName} global, INV640: {inv640}")
    GUI.chips[colutaName].setConfiguration("global", "DELAY640", delay640)
    print(f"Updated {colutaName} global, DELAY640: {delay640}")

    readbackSuccess = GUI.writeToCOLUTAGlobal(colutaName)
    if readbackSuccess == False:
        print(colored(f"First write to {colutaName.upper()} failed, trying again...", "yellow"))
        readbackSuccess = GUI.writeToCOLUTAGlobal(colutaName)
        if readbackSuccess == False: print(colored(f"Readback error: write to {colutaName.upper()} failed", "red")) 

#Add read back

def writeToHDF5(tables):
  """ Saves clock scan results to an HDF5 """
  fileName = 'clockScanBoard634Repeat.hdf5'
  out_file = h5py.File(fileName,'w')
  print("Opening hdf5 file: "+ fileName)

  for coluta in tables.keys():
      out_file.create_group(coluta)
      for ch in tables[coluta].keys():
          out_file.create_dataset(coluta+"/Channel"+ch[-1], data=tables[coluta][ch])

  out_file.close()  
  print("Closing HDF5")

def putInSerializerMode(GUI, colutas):
    """ put all channels in serializer mode """
    for coluta in colutas:
        GUI.serializerTestMode(coluta, "1")
   #Add read back 

def setLPGBTPhaseToZero(GUI, colutas):
    """ undo any previous clock settings """
    for coluta in colutas:
        chip = GUI.chips[coluta]
        for ch in [f'ch{i}' for i in range(1,9)]:
            chip.setConfiguration(ch,"LPGBTPhase", '0000')
            boxName = coluta+ch+'LPGBTPhaseBox'
            GUI.updateBox(boxName, '0')

def prepareChips(GUI,colutas):
    """ put board in correct mode for clock scan """
    putInSerializerMode(GUI,colutas)
    setLPGBTPhaseToZero(GUI,colutas)
    GUI.sendUpdatedConfigurations()

def scanClocks(GUI,colutas): 
    """ Scan all clock parameters """
    ## Load information which matches COLUTA channels and lpGBT registers
    with open('config/colutaLpGBTMapping.txt','r') as f:
        mapping = pyjson5.load(f)
        #lpgbtRegDict = mapping[coluta]

    prepareChips(GUI,colutas)

    channels = ['ch'+str(i) for i in range(1,9)] # Use all 8 channels
    channelSerializers = {channels[i] : bin(i)[2:].zfill(3) for i in range(0,8)} #ch1 = 000, ch2 = 001, ..., ch8 = 111
    upper = 2 ## How many COLUTA & lpGBT settings to loop through - 16 is max

    i2cLabels = {}
    chanNames = {}
    valid = {}
    LPGBTPhase = {}
    for coluta in colutas:
        colutaChip = GUI.chips[coluta]
        i2cLabels[coluta] = colutaChip.i2cAddress[6:10] # collect I2C address - used in serializer pattern
        colutaNum = int(coluta[6:])
        chanNum = colutaNum*4-1 #convert to lowest feb2 channel number
        chanNames[coluta] = ['channel'+str(chanNum-i).zfill(3) for i in range (0,4)] #match all 4 FEB2 channel numbers to COLUTA

    for coluta in colutas:
        i2cLabel = i2cLabels[coluta]
        valid[coluta] = {}
        LPGBTPhase[coluta] = {}
        for chn in channels:
            sertest_true = '1010'+i2cLabel+channelSerializers[chn]+'01001'  # correct serializer pattern
            sertest_repl = sertest_true*2
            sertest_valid = [sertest_repl[i:(16+i)] for i in range (0,16)]  # valid permutations of serializer pattern
            valid[coluta][chn] = sertest_valid[:] # save all valid permutations to dictionary 
            LPGBTPhase[coluta][chn] = [[] for i in range(0,upper)]  #dictionary to save lpGBT phase result

    ## Uncomment to see serializer mode in hex
    #for coluta in colutas:
    #    for chn in channelSerializers.keys():
    #        print(hex(int(valid[coluta][chn][1],2)))
    #return

    # is serializer pattern the same across all samples?
    isStable_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

    # is serializer pattern a correct permutations?
    isValid_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

    for delay_idx in range(0,upper):
        for coluta in colutas:
            sendInversionBits(GUI, delay_idx, coluta) # set the COLUTA clock setting

        for lpgbt_idx in range(0,upper):
            value = (lpgbt_idx<<4)+2 # lpgbt clock setting register value
            # lpgt_idx = 1100 (XPhaseSelect)
            # register where we want to write this 0xce, and it expected 8 bits
            # 0xce: XPhaseSelect (4bit), XA(1), XI(1), XT(1), XE (1) 
            # if we just wriute 1100 to 0xce, then we will be writing XA, XT, XI, XE 
            # we need to write 1100<><><XT><XE>
            # 1100<<4 = 1100 0000
            # 1100<<4 + 2 = 1100 0010 (which is the default config)
            print(colored(f"Value: {value}", "cyan"))
            for coluta in colutas:
                for lpgbt in mapping[coluta].keys():
                    registers = mapping[coluta][lpgbt]
                    print(lpgbt, registers)
                    for reg in registers:
                        print(reg)
                        error = False
                        for i in range(3):
                            if i == 1:
                                print(colored("First write failed, trying again...", "yellow"))
                            if i == 2:
                                print(colored("Readback error: write failed", "red"))
                                break 
                            GUI.writeToLPGBT(lpgbt, reg, [value], True) # set the lpGBT clock setting
                            readback = GUI.readFromLPGBT(lpgbt, reg, 16)
                            if value == readback[0]: break
                        #print(f"Readback: {readback}")
                        #if readback == value: print
                        ## Add readback
            GUI.takeTriggerData('clockScan') # take data
            print("Opening run", str(GUI.runNumber).zfill(4))
            datafile = h5py.File('../Runs/run'+str(GUI.runNumber).zfill(4)+'.hdf5','r')  # open the data
            m = str(len(datafile.keys())-1).zfill(3) # get the latest measurement
            print(m)
            d = datafile.get('Measurement_'+m) # data

            for coluta in colutas:  
                ## Read in data
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
                    binary_list = [str(bin(x))[2:].zfill(16) for x in samples[ch]]
                    isStable = (len(set(binary_list)) == 1)  # test if data is stable
                    isStable_list[coluta][ch].append(isStable)
                    isValid = set(binary_list).issubset(valid[coluta][ch]) # test if data is a valid serializer pattern
                    isValid_list[coluta][ch].append(isValid)
                    if isStable and isValid:
                        phase = valid[coluta][ch].index(binary_list[0]) # save the phase needed for the correct permutation
                    else:
                        phase = -1 # invalid
                    LPGBTPhase[coluta][ch][delay_idx].append(phase) 

            datafile.close()

    ## Save results in a pretty table
    headers = [f'{i}\n' for i in range(0,upper)]
    headers.insert(0,"xPhaseSelect -> \n INV/DELAY640 ")
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    for coluta in colutas:
        with open("clockScanBoard634Repeat"+coluta+".txt", "w") as f:
            for ch in channels:
                f.write("Channel "+ch[-1]+"\n")
                prettyTable = tabulate(LPGBTPhase[coluta][ch], headers, showindex = "always", tablefmt="psql")
                f.write(prettyTable)
                f.write("\n \n")

    ## Save results in an hdf5
    writeToHDF5(LPGBTPhase)
    print("Finished Clock Scan")

