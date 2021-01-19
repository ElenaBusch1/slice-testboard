import h5py
import numpy as np
import helperfunctions as hf
import matplotlib.pyplot as plt
import os
import glob
import sys
import argparse
import time
import shutil
from builtins import input
from collections import defaultdict

#hello world!
      

#-------------------------------------------------------------------------
def isSequence(arg):
  """Determines if arg is a sequence. See https://stackoverflow.com/questions/1835018/"""
  return (not hasattr(arg, "strip") and
          (hasattr(arg, "__getitem__") or
           hasattr(arg, "__iter__")))

#-------------------------------------------------------------------------
def setHDF5Attributes(hdf5File,**kwargs):
  """Create and attach attributes specified in kwargs to the HDF5 group or dataset hdf5Object"""
  # with h5py.File(hdf5Object,'a') as hdf5File:
  for key, value in kwargs.items():
    if isSequence(value) and not isinstance(value, np.generic):
      if type(value[0]) is str:
        hdf5File.attrs.create(key,value,dtype=h5py.special_dtype(vlen=str))
      else:
        hdf5File.attrs.create(key,value)
    else:
      if type(value) is str:
        hdf5File.attrs.create(key,value,dtype=h5py.special_dtype(vlen=str))
      else:
        hdf5File.attrs.create(key,value)

def saveDataToHDF5(out_file, input_file, meas_range, float_weight,meas_to_use = []):
  """Loops through given measurement range and saves cut attributes and data for each channel"""
 
  for index,meas_i in enumerate(meas_to_use):
    n_adcs = 1
    this_channel = input_file["Measurement_" + str(meas_i)].attrs["measChan"]
    cut_attrs = [attr for attr in input_file["Measurement_" + str(meas_i)].attrs
                 if len(np.unique(input_file["Measurement_" + str(meas_i)].attrs[attr])) > 1]
    cut_attrs_dict = {attr: input_file["Measurement_" + str(meas_i)].attrs[attr] for attr in cut_attrs}
  

    #print("creating group: Measurement_"+ str(index)) 
    out_file.create_group("Measurement_" + str(index))
    setHDF5Attributes(out_file["Measurement_" + str(index)], **cut_attrs_dict)

    #out_file.create_group("Measurement_" + str(meas_i))
    #setHDF5Attributes(out_file["Measurement_" + str(meas_i)], **cut_attrs_dict)

    
    print(this_channel)
    #for adc in range(out_file.attrs["n_adcs"]):
    #channels = ['channel6']
    #channel2 = 'channel5'
    channels = ['channel1']
    #channels = ['channel5','channel6','channel7','channel8']
    invalid = 0
    #LOGIC for choosing channel in test measurements  
    if this_channel == "channel1":
        address_1 = 'Measurement_{meas_i}/coluta/channel1'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel2'.format(meas_i = meas_i)

    elif this_channel == "channel2":
        address_1 = 'Measurement_{meas_i}/coluta/channel2'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel1'.format(meas_i = meas_i)

    elif this_channel == "channel3":
        address_1 = 'Measurement_{meas_i}/coluta/channel3'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel4'.format(meas_i = meas_i)

    elif this_channel == "channel4":
        address_1 = 'Measurement_{meas_i}/coluta/channel4'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel3'.format(meas_i = meas_i)

    elif this_channel == "channel5":
        address_1 = 'Measurement_{meas_i}/coluta/channel5'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel6'.format(meas_i = meas_i)

    elif this_channel == "channel6":
        address_1 = 'Measurement_{meas_i}/coluta/channel6'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel5'.format(meas_i = meas_i)

    elif this_channel == "channel7":
        address_1 = 'Measurement_{meas_i}/coluta/channel7'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel8'.format(meas_i = meas_i)

    elif this_channel == "channel8":
        address_1 = 'Measurement_{meas_i}/coluta/channel8'.format(meas_i = meas_i)
        address_2 = 'Measurement_{meas_i}/coluta/channel7'.format(meas_i = meas_i) #print(this_channel)

    #print(address_1)
    #print(address_2)
   
    for adc in range(n_adcs):

      #print("creating group: " + f"Measurement_{index}/coluta{str(adc + 1)}")
   
      out_file.create_group("Measurement_{index}/coluta{this_adc}".format(index = index, this_adc = adc + 1))
      setHDF5Attributes(out_file["Measurement_{index}/coluta{this_adc}".format(index = index, this_adc = adc + 1)],
                        channels=[this_channel])
      #out_file.create_group(f"Measurement_{meas_i}/coluta{str(adc + 1)}")
      #setHDF5Attributes(out_file[f"Measurement_{meas_i}/coluta{str(adc + 1)}"],
                        #channels=[this_channel])
      #for channel in out_file[f"Measurement_{str(meas_i)}/coluta{str(adc + 1)}"].attrs["channels"]:
      for channel in channels:
        if channel == 'frame': continue
        if str(this_channel) == "0":
            address_1 = 'Measurement_{meas_i}/coluta/channel5'.format(meas_i = meas_i)
            address_2 = 'Measurement_{meas_i}/coluta/channel6'.format(meas_i = meas_i)
          

            
        if int(this_channel[-1]) < 5:  
            SAR_weights = [13624, 7785, 3892, 2433, 1459, 973, 486, 851, 486, 243, 121, 91, 60, 38, 22, 16, 8, 4, 2, 1]
            MDAC_corr_codes = [0, 0, 0, 0, 0, 0, 0, 0]
            #SAR_weights  = [3584, 2048, 1024, 640, 384, 256, 128, 224, 128, 64, 32, 24, 16, 10, 6, 4, 2, 1, 0.5, 0.25]  
            #MDAC_corr_codes = [4280, 4280, 4280, 4280, 4280, 4280, 4280, 4280]

            
            #SAR_weights  = [3584, 2048, 1024, 640, 384, 256, 128, 224, 128, 64, 32, 24, 16, 10, 6, 4, 2, 1, 0.5, 0.25]  
            #MDAC_corr_codes = [4280, 4280, 4280, 4280, 4280, 4280, 4280, 4280]
            #SAR_weights = [x*4 + 4218 for x in SAR_weights]
            #MDAC_corr_codes = [x*4 + 4218 for x in MDAC_corr_codes]

        else: #if this is a testfile, we need to use mdac and sar weights for this specific chip
            print("here!")        
            weight_dir = hf.getRootDir() + "/TestPlots/" + run_name + "/" + this_channel + "/"  
        
            f = open(weight_dir + "scaleSarWeightsFinal.txt","r")
            g = open(weight_dir + "scaleMdacWeightsFinal.txt","r")
          
            SAR_weights = [float(x) for x in f.readlines()]
            MDAC_corr_codes =  [float(x) for x in g.readlines()]
       
            #SAR_weights = [3584.0, 2048.0, 1025.25, 641.5, 385.0, 257.0, 128.0, 220.5, 126.5, 63.0, 31.75, 23.5, 15.75, 9.75, 5.75, 4.0, 2.0, 1.0, 0.5, 0.25]
            #MDAC_corr_codes = [4269.25, 4266.5, 4267.25, 4269.0, 4267.25, 4267.25, 4268.0, 4272.25]
   

            #SAR_weights  = [3584, 2048, 1024, 640, 384, 256, 128, 224, 128, 64, 32, 24, 16, 10, 6, 4, 2, 1, 0.5, 0.25]  
            #MDAC_corr_codes = [4280, 4280, 4280, 4280, 4280, 4280, 4280, 4280]
 
            f.close()
            g.close()

            #address_1 = f"Measurement_{str(meas_range[meas_i])}/coluta/channel8"
            #address_2 = f"Measurement_{str(meas_range[meas_i])}/coluta/channel7" 
     
            SAR_old = [13624,7785,3897,2438,1463,976,486,836,479,239,121,90,59,36,21,16,8,4,2,1] #Brian's method
            MDAC_old = [16434,16427,16431,16441,16437,16435,16436,16457] #Brian's method

        '''
        print("SAR old: " ,SAR_old)
        print("SAR new: " ,SAR_weights)
        print("MDAC old: " ,MDAC_old)
        print("MDAC new: " ,MDAC_corr_codes)
        
        try:
          SAR_weights = input_file.attrs[f"coluta{adc+1}_{channel}_SAR_weights"]
        except KeyError: #Define sar and mdac weights by hand
        '''
     
        #SAR_weights =[4*x for x in SAR_weights]
        #MDAC_corr_codes = [4*x for x in MDAC_corr_codes]

        print("SAR",SAR_weights)
        print("MDAC",MDAC_corr_codes)      
          
        raw_data_msbs = np.array(input_file["{address_1}/raw_data".format(address_1 = address_1)])
        raw_data_lsbs = np.array(input_file["{address_2}/raw_data".format(address_2 = address_2)])
        #raw_data = []
        #samples = []
        raw_data = np.concatenate((raw_data_msbs.transpose(),raw_data_lsbs.transpose()))
        print(np.shape(raw_data))
        print(raw_data)
        
        Mdac_sar_info = np.zeros(32)
        Mdac_sar_info[4:12] = MDAC_corr_codes
        Mdac_sar_info[12:] = SAR_weights

        print()
        print(Mdac_sar_info)
        print()

        samples = np.sum(raw_data*Mdac_sar_info[:,np.newaxis],axis = 0)

        if int(this_channel[-1]) >= 5:
            samples = samples/4.0 - 4218

        #plt.plot(np.sum(raw_data*Mdac_sar_info[:,np.newaxis],axis = 0),'k.')
        #plt.show()

        ''' 
        #print(raw_data_msbs,raw_data_lsbs)
        for ele in range(len(raw_data_msbs)): 
          row = np.append(raw_data_msbs[ele],raw_data_lsbs[ele])
          raw_data.append(row)
          #print(row)
          sample_val = 0.0
          sample_val += np.dot(row[4:12], MDAC_corr_codes)
          sample_val += np.dot(row[12:], SAR_weights)
          
          if not(float_weight):
              if int(this_channel[-1]) >= 5: 
                  sample_val = sample_val/4.0 - 4218
              #print(sample_val)

              if sample_val > 32767:
                  pass 
                  #print("sample invalid!")
                  #invalid =+ 1
          #print(round(sample_val))
          samples.append(round(sample_val))
        '''
      
        print(str(meas_i))
        #bits = raw_data
        if invalid > 0:
            #continue
            pass
            #print("keeping invalids for now")
        else:
            #plt.plot(np.array(samples))
            #plt.show()
            print("Creating Dataset: "+ "Measurement_{index}/coluta{this_adc}/{this_channel}/samples".format(index = index,this_adc = adc + 1,this_channel = this_channel))
            out_file.create_dataset("Measurement_{index}/coluta{this_adc}/{this_channel}/samples".format(index = index,this_adc = adc + 1,this_channel = this_channel), data=samples)
            #out_file.create_dataset(f"Measurement_{str(meas_i)}/coluta{str(adc + 1)}/{channel}/bits", data=bits)

#-------------------------------------------------------------------------
def convertSine(output_dir, input_file, gain_dict,run_type = "sine", float_weight = 0,meas_to_use = []):
  """Loops through gains and ignores amplitudes for pedestal data"""
  for gain, amp_dict in gain_dict.items():
    meas_range = [meas for amp in amp_dict.values() for meas in amp]

    print("MEAS RANGE: ",meas_range)
    meas_to_use = meas_range
    with h5py.File(output_dir + "Sine_Data_{gain}.hdf5".format(gain = gain),"w") as out_file:
      setHDF5Attributes(out_file,
                        #n_adcs=input_file.attrs["n_adcs"],
                        n_measurements=len(meas_range),
                        #n_pulses=n_pulses,
                        #n_samples_per_pulse=n_samples_per_pulse,
                        adc_freq=40,
                        awg_freq=5.0368,
                        run_type = run_type
                        )
      saveDataToHDF5(out_file, input_file, meas_range,float_weight,meas_to_use)

#-------------------------------------------------------------------------
def convertPedestal(output_dir, input_file, gain_dict,float_weight = 0,meas_to_use = []):
  """Loops through gains and ignores amplitudes for pedestal data"""
  for gain, amp_dict in gain_dict.items():
    meas_range = [meas for amp in amp_dict.values() for meas in amp]

    print("MEAS RANGE: ",meas_range)

    with h5py.File(output_dir + "Pedestal_Data_{gain}.hdf5".format(gain = gain),"w") as out_file:
      setHDF5Attributes(out_file,
                        #n_adcs=input_file.attrs["n_adcs"],
                        n_adcs=1,
                        n_measurements=len(meas_range),
                        adc_freq=40
                        )
      saveDataToHDF5(out_file, input_file, meas_range,float_weight,meas_to_use)

#-------------------------------------------------------------------------
def convertPulse(output_dir, input_file, gain_dict, n_pulses = 8, n_samples_per_pulse = 440, awg_freq = 320, run_type = "onboard", float_weight = 0,meas_to_use = []):
  """Loops through gains and amplitudes for onboard or pulse data"""
 
  for gain, amp_dict in gain_dict.items():
    for amp, meas_range in amp_dict.items():
      with h5py.File(output_dir + "Pulse_Amp{amp}_{gain}.hdf5".format(amp = amp, gain = gain),"w") as out_file:
        setHDF5Attributes(out_file, 
                          #n_adcs=input_file.attrs["n_adcs"],
                          n_adcs = 1,
                          n_measurements=len(meas_range),
                          n_pulses=n_pulses,
                          n_samples_per_pulse=n_samples_per_pulse,
                          adc_freq=40,
                          awg_freq=awg_freq,
                          run_type = "pulse"
                          )
        print("in convertPulse: Meas to use:, ",meas_to_use)
        saveDataToHDF5(out_file, input_file, meas_range,float_weight,meas_to_use)

#-------------------------------------------------------------------------
def main():
  
  data_dir = "/data/users/acs2325/slice/"

  raw_dir = hf.checkDir(datadir+"/Data/Raw/Pulses/")
  raw_dir_pedestal = hf.checkDir(datadir+"/Data/Raw/Pedestal/")
  raw_dir_tf = hf.checkDir(datadir+"/Data/Raw/Test/")

  #Get directories to run in
  parser = argparse.ArgumentParser()
  parser.add_argument("-r", "--runs", default = [], type=str, nargs='+',
                     help="list of runs (directories in Data/Processed/) to include")
  parser.add_argument("-s", "--start", default = 0, type=int, nargs='+',
                     help="start measurement")
  parser.add_argument("-e", "--end", default = 1200, type=int, nargs='+',
                     help="end measurement")
  parser.add_argument("-sar", "--sar_dir", default='', type=str,
                     help="parent directory containing textfile with sar weights")
  
  #Allow user input for choice of runs
  args = parser.parse_args()
  runs = [raw_dir + run + "/" for run in args.runs]
  startMeas = args.start[0]
  endMeas = args.end[0]

  global sar_dir 
  sar_dir = args.sar_dir

  measurement_dict = {} 

  if runs == []:
    print('No run number specified')
    sys.exit(0)
  global run_name

  for run in runs:
    run_name = hf.short(run)[:-1]
    #Choose Input File
    #----------------------------------
    infile_name = run_name + "_Output.hdf5"
    #----------------------------------

    #Try to find the file in either the raw data path, or in this directory
    
    else:
        try:
          input_file = h5py.File(raw_dir+infile_name, "r")
        except:
          try:
            input_file = h5py.File(raw_dir_pedestal+infile_name, "r")
          except:
            print("Input file not found in either ../Data/Raw/Pulses/ or ../Data/Raw/Pedestal/")
            sys.exit(0)

    #Define measurement ranges per run_type, gain, and amplitude
    gain_array = ['AG', '4x', '1x']
    meas_dict = defaultdict(lambda : defaultdict(lambda : defaultdict(list)))

    for measurement in range(startMeas, endMeas):
      #gain = gain_array[input_file['Measurement_'+str(measurement)+'/coluta/channel1'].attrs['gain']]
      gain = '1x' #tmp
      if isTestFile:
          run_type = input_file['Measurement_'+str(measurement)].attrs['measType']
      
      else:
          #run_type = input_file['Measurement_'+str(measurement)].attrs['run_type']
          run_type = 'pulse'
      #run_type = 'pedestal'
      #run_type = 'pulse'
      if run_type == 'pulse':
        #print(measurement)
        #print(input_file['Measurement_'+str(measurement)].attrs['awg_amp'])
        pulse_amp = input_file['Measurement_'+str(measurement)].attrs['awg_amp'].replace('.','p') #CV3
        #print(pulse_amp)
        #pulse_amp = input_file['Measurement_'+str(measurement)].attrs['pulse_amplitude'].replace('.','p')
      else:
        pulse_amp = input_file['Measurement_'+str(measurement)].attrs['awg_amp']
      meas_dict[run_type][gain][pulse_amp].append(measurement)

      #print('pulse amp: ' , pulse_amp)
    print(meas_dict[run_type][gain]['4p0'])
    
    for run_type, gain_dict in meas_dict.items():
      print('Using run type ', run_type)
      
      #meas_to_use = meas_dict[run_type]['1x']
      
      if run_type == "pedestal":
        #continue 
          
        meas_to_use = meas_dict[run_type]['1x'][0]
        print("meas to use!: ", meas_to_use)
          
        output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed/Pedestal/{run_name}/".format(run_name = run_name))
        print("Writing processed output to: " + output_dir)
        convertPedestal(output_dir, input_file, gain_dict,meas_to_use=meas_to_use)
        
      elif run_type == "pulse":
        if args.test_file: continue        
        meas_to_use = range(startMeas,endMeas)
        output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed/Pulses/{run_name}/".format(run_name = run_name))
        if args.float_weight: output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed_FW/Pulses/{run_name}/".format(run_name = run_name))
        print("Writing processed output to: " + output_dir)
        convertPulse(output_dir, input_file, gain_dict, n_pulses=30, n_samples_per_pulse=256, awg_freq=1200, run_type=run_type)
          
        if isTestFile:
            
            meas_to_use = meas_dict[run_type]['1x']['6p0']
            print("Pre convert pulse: meas_to_use ",meas_to_use )
            convertPulse(output_dir, input_file, gain_dict, n_pulses=30, n_samples_per_pulse=256, awg_freq=1200, run_type=run_type,float_weight=args.float_weight,meas_to_use=meas_to_use)

      elif run_type == "sine":  
        #if args.test_file: continue        
          
        meas_to_use = meas_dict[run_type]['1x']['10p5']
        print("meas to use!: ", meas_to_use)
          
        output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed/Sine/{run_name}/".format(run_name = run_name))
        print("Writing processed output to: " + output_dir)
        convertSine(output_dir, input_file, gain_dict,meas_to_use=meas_to_use)

 
      elif run_type == "onboard":
        output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed/Pulses/{run_name}/".format(run_name = run_name))
        if args.float_weight: output_dir = hf.checkDir(hf.getRootDir() + "/Data/Processed_FW/Pulses/{run_name}/".format(run_name = run_name))
        print("Writing processed output to: " + output_dir)
        convertPulse(output_dir, input_file, gain_dict, n_pulses=8, n_samples_per_pulse=440, awg_freq=320, run_type=run_type,float_weight=args.float_weight)
      else:
        continue
    
    input_file.close()

#-------------------------------------------------------------------------
if __name__ == "__main__":
  main()

