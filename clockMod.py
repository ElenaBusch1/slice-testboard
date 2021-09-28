import os
import h5py
import numpy as np
import pyjson5
import findClockParam
from termcolor import colored
from timeit import default_timer as timer
from datetime import timedelta

def sendInversionBits(GUI, clock640, colutaName):
    """ Change the clock register on the COLUTA """
    binary = f'{clock640:04b}' # convert to binary
    inv640 = binary[0]
    delay640 = binary[1:] 
    GUI.chips[colutaName].setConfiguration("global", "INV640", inv640)
    print(f"Updated {colutaName} global, INV640: {inv640}")
    GUI.chips[colutaName].setConfiguration("global", "DELAY640", delay640)
    print(f"Updated {colutaName} global, DELAY640: {delay640}")

    #Readback
    attempts = 0
    while attempts < 2:
        readbackSuccess = GUI.writeToCOLUTAGlobal(colutaName)
        if readbackSuccess is True:
            break
        elif attempts == 0:
            print(colored(f"First write to {colutaName.upper()} failed, trying again...", "yellow"))
        elif attempts == 1:
            print(colored(f"Readback error: write to {colutaName.upper()} failed", "red"))
            readbackSuccess = False
            #return(False)
        attempts += 1
    
    return(readbackSuccess)

def writeToHDF5(GUI, tables):
  """ Saves clock scan results to an HDF5 """
  fileName = f'clockScanBoard{GUI.boardID}Repeat.hdf5'
  out_file = h5py.File(f"clockScan_board{GUI.boardID}/clockScanResults/" + fileName,'w')
  print("Opening hdf5 file: " + fileName)

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

def writeToLpGBT(GUI, coluta, lpgbt, reg, value):
    
    ## Matches lpGBT to correct COLUTA channel
    with open("config/lpGBTColutaMapping.txt", "r") as f:
        regToChannel = pyjson5.load(f)

    ## Readback
    chn = regToChannel[lpgbt][coluta].get(reg)
    if chn is not None:
        attempts = 0
        while attempts < 2:
            GUI.writeToLPGBT(lpgbt, reg, [value], True)
            readback = GUI.readFromLPGBT(lpgbt, reg, 1)
            if value == readback[0]:
                return chn, True
                break
            elif attempts == 0:
                print(colored(f"First write to {lpgbt} register {reg} failed, trying again...", "yellow"))
            elif attempts == 1:
                print(colored(f"Readback error: write to {lpgbt} register {reg} failed", "red"))
                return chn, False
            attempts += 1
    
    ## For frames...?
    else: GUI.writeToLPGBT(lpgbt, reg, [value], True)

def scanClocks(GUI,colutas): 
    """ Scan all clock parameters """
    print(GUI.boardID)
    ## Makes sure at least one COLUTA is selected for clock scan
    if colutas is None:
        print(colored("Please select at least one COLUTA", "red"))
        return    

    start = timer()
    ## Load information which matches COLUTA channels and lpGBT registers
    with open('config/colutaLpGBTMapping.txt','r') as f:
        mapping = pyjson5.load(f)
        #lpgbtRegDict = mapping[coluta]
        
    prepareChips(GUI,colutas)

    channels = ['ch'+str(i) for i in range(1,9)] # Use all 8 channels
    channelSerializers = {channels[i] : bin(i)[2:].zfill(3) for i in range(0,8)} #ch1 = 000, ch2 = 001, ..., ch8 = 111
    upper = 16 ## How many COLUTA & lpGBT settings to loop through - 16 is max

    i2cLabels = {}
    chanNames = {}
    valid = {}
    LPGBTPhase = {}
    readback = {}
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
        readback[coluta] = {}
        for chn in channels:
            sertest_true = '1010'+i2cLabel+channelSerializers[chn]+'01001'  # correct serializer pattern
            sertest_repl = sertest_true*2
            sertest_valid = [sertest_repl[i:(16+i)] for i in range (0,16)]  # valid permutations of serializer pattern
            valid[coluta][chn] = sertest_valid[:] # save all valid permutations to dictionary 
            LPGBTPhase[coluta][chn] = [[] for i in range(0,upper)]  # dictionary to save lpGBT phase result
            readback[coluta][chn] = [[1]*upper for i in range(0, upper)] # map with failed readbacks
    
    ## Uncomment to see serializer mode in hex
    #for coluta in colutas:
    #    for chn in channelSerializers.keys():
    #        print(hex(int(valid[coluta][chn][1],2)))
    #return

    # is serializer pattern the same across all samples?
    isStable_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

    # is serializer pattern a correct permutations?
    isValid_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}
    
    if not os.path.exists(f"clockScan_board{GUI.boardID}"):
        os.makedirs(f"clockScan_board{GUI.boardID}") # Creates directory for given board
        print(f"Creating clockScan_board{GUI.boardID} directory...")

    for delay_idx in range(0,upper):
        for coluta in colutas:
            configureSuccess = sendInversionBits(GUI, delay_idx, coluta) # set the COLUTA clock setting
            #Useless to change lpgbt_idx if failed
            if configureSuccess is False:
                for chn in channels: readback[coluta][chn][delay_idx] = [0]*upper # readback failed so can't trust entire row             
  
        for lpgbt_idx in range(0,upper):
            value = (lpgbt_idx<<4)+2 # lpgbt clock setting register value
            # lpgt_idx = 1100 (XPhaseSelect)
            # register where we want to write this 0xce, and it expected 8 bits
            # 0xce: XPhaseSelect (4bit), XA(1), XI(1), XT(1), XE (1) 
            # if we just wriute 1100 to 0xce, then we will be writing XA, XT, XI, XE 
            # we need to write 1100<><><XT><XE>
            # 1100<<4 = 1100 0000
            # 1100<<4 + 2 = 1100 0010 (which is the default config)

            for coluta in colutas:
                for lpgbt in mapping[coluta].keys():
                    registers = mapping[coluta][lpgbt]
                    #print(lpgbt, registers)
                    for reg in registers:
                        try:
                            chn, configureSuccess = writeToLpGBT(GUI, coluta, lpgbt, reg, value)
                            if configureSuccess is False and readback[coluta][chn][delay_idx][lpgbt_idx] > 0: 
                                readback[coluta][chn][delay_idx][lpgbt_idx] = 0
                        except TypeError:
                            continue
                            
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
                    
                    if readback[coluta][ch][delay_idx][lpgbt_idx] == 0:
                        phase = -2 # flags failed writes

                    LPGBTPhase[coluta][ch][delay_idx].append(phase)
                    #dictionary readback success in same format -- 1 or 0 if combination successful
                    #if delay_idx bad, all 0s  

            datafile.close()

    ## Save results in a pretty table
    if not os.path.exists(f"clockScan_board{GUI.boardID}/clockScanResults"):
        os.makedirs(f"clockScan_board{GUI.boardID}/clockScanResults")
        print(f"Creating clockScanResults directory...")

    headers = [f'{i}\n' for i in range(0,upper)]
    headers.insert(0,"xPhaseSelect -> \n INV/DELAY640 ")
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        print('You need the tabulate package...')

    for coluta in colutas:
        with open(f"clockScan_board{GUI.boardID}/clockScanResults/clockScanBoard{GUI.boardID}Repeat"+coluta+".txt", "w") as f:
            for ch in channels:
                f.write("Channel "+ch[-1]+"\n")
                prettyTable = tabulate(LPGBTPhase[coluta][ch], headers, showindex = "always", tablefmt="psql")
                f.write(prettyTable)
                f.write("\n \n")

                #Uncomment to see readback tables
                #f.write("Readback \n")
                #readbackTable = tabulate(readback[coluta][ch], headers, showindex = "always", tablefmt="psql")
                #f.write(readbackTable)
                #f.write("\n \n")

    ## Save results in an hdf5
    writeToHDF5(GUI, LPGBTPhase)
    end = timer()
    print("\n")
    print(colored("Finished ", "cyan") + "clock scan for: " + ", ".join(colutas))
    print(colored("Time elapsed: ", "cyan") + str(timedelta(seconds = end-start)))
    print("\n")
    if upper == 16: findClockParam.findParams(GUI.boardID)

