#Serializer validation

import h5py
import numpy as np
import json5

def serializerValidation(run_path):
	run = run_path[run_path.index("run"):run_path.index(".hdf5")]
	
	colutas = ["coluta"+str(i) for i in range(13,21)]
	channels = ['ch'+str(i) for i in range(1,9)] #Use all 8 channels
	channelSerializers = {channels[i] : bin(i)[2:].zfill(3) for i in range(0,8)} #ch1 = 000, ch2 = 001, ..., ch8 = 111
	upper = 16 #How many COLUTA & lpGBT settings to loop through - 16 is max
	
	i2cLabels = {}
	chanNames = {}
	valid = {}
	LPGBTPhase = {}

	for coluta in colutas:
		#colutaChip = GUI.chips[coluta]
		#i2cLabels[coluta] = colutaChip.i2cAddress[6:10] #collect I2C address - used in serializer pattern
		colutaNum = int(coluta[6:])
		i2cLabels[coluta] = bin(((colutaNum - 1) % 8) + 1)[2:].zfill(4) 
		chanNum = colutaNum*4-1 #convert to lowest feb2 channel number
		chanNames[coluta] = ["channel"+str(chanNum-i).zfill(3) for i in range (0,4)] #match all 4 FEB2 channel numbers to COLUTA

	for coluta in colutas:
		i2cLabel = i2cLabels[coluta]
		valid[coluta] = {}
		LPGBTPhase[coluta] = {}
		for chn in channels:
			sertest_true = "1010"+i2cLabel+channelSerializers[chn]+'01001' #correct serializer pattern
			sertest_repl = sertest_true*2
			sertest_valid = [sertest_repl[i:(16+i)] for i in range(0,16)] #valid permutaions of serializer pattern
			valid[coluta][chn] = sertest_valid[:] #save all valid permutations to dictionary
			LPGBTPhase[coluta][chn] = [] #dictionary to save lpGBT phase result

	#is serializer pattern the same across all samples?
	isStable_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

	#is serializer pattern a correct permutation?
	isValid_list = {coluta: {ch: [] for ch in channels} for coluta in colutas}

	datafile = h5py.File(run_path, "r") #open data
	m = str(len(datafile.keys())-1).zfill(3) #get latest measurement
	print(m)
	d = datafile.get("Measurement_"+m) #data
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
			LPGBTPhase[coluta][ch].append(phase)

	datafile.close()

	## Save results in a pretty table
	headers = [f'coluta{i}\n' for i in range(13,21)]
	headers.insert(0,run+"\n")

	try:
		from tabulate import tabulate
	except ModuleNotFoundError:
		print('You need the tabulate package...')

	with open("serializerValidation_"+run+".txt", "w") as f:
		to_table = [[ch] for ch in channels]
		for i, ch in enumerate(channels):
			for coluta in colutas:
				to_table[i] = to_table[i] + LPGBTPhase[coluta][ch]
 
		prettyTable = tabulate(to_table, headers, tablefmt="psql")
		f.write(prettyTable)
		f.write("\n \n")


if __name__ == "__main__":
	serializerValidation("/nevis/milne/files/gpm2117/Testboard/Runs/run0946.hdf5")
