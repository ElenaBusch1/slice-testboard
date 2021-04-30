import numpy as np
from math import *
import sys
import h5py
import os
#BEGIN SLICE PROCESS DATAFILE CLASS

class Process(object):

    #__INIT__#
    def __init__(self, fileName = None):

      self.fileName = fileName
      #self.mdacWeights = [4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288]
      #self.sarWeights = [4*3584,4*2048,4*1024,4*640,4*384,4*256,4*128,4*224,4*128,4*64,4*32,4*24,4*16,4*10,4*6,4*4,4*2,4*1,4*0.5,4*0.25]
      self.measTypeDict = None
      self.Gains = None
      self.Channels = None

    def getNormalWF(self,output_dir,mType,isBinary = 0):

        bit_range = np.arange(0,16)[::-1]
        normal_codes = np.array([2**(i) for i in bit_range])

        f = h5py.File(self.fileName,"r")

        out_file = h5py.File(output_dir + "Data_Normal.hdf5","w")


        for meas_ind,meas in enumerate(self.measTypeDict[mType]):
            out_file.create_group("Measurement_" + str(meas_ind))
            for gain in self.Gains:        
                  print(gain)
                  for channel in self.Channels:
                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = str(meas_ind).zfill(3),\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
                    #raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = str(meas_ind).zfill(3)))
                    if np.shape(raw_data)[-1] == 0: continue  

                    print((np.shape(raw_data)))
                    samples = raw_data

                    if isBinary:
                        raw_data = raw_data.transpose()
                        samples = np.sum(raw_data*normal_codes[:,np.newaxis],axis = 0)
                    #print("Samples: ",samples)
                    #print(samples[ samples >2**15])


                    dataset_str = "Measurement_{meas_ind}/{channel}/{gain}/samples".format(meas_ind = meas_ind, channel = str(channel),gain = gain)
                    print(("Creating Dataset: "+ dataset_str))
                    out_file.create_dataset(dataset_str, data=samples)

       
        f.close()
        out_file.close()
        return   

    def getChannelsAndGains(self):

        f = h5py.File(self.fileName,"r")
        self.Channels = list(f["Measurement_000/"].keys())        
        self.Gains = list(f["Measurement_000/{channel}".format(channel = self.Channels[0])].keys())        
        f.close()

    def getMeasTypeDict(self):

      meas_dict = {}

      f = h5py.File(self.fileName,"r")

      for meas_num in range(len(f)):
          
          meas_str = str(meas_num).zfill(3)
          try:
              measType = f["Measurement_"+meas_str].attrs["measType"]
          except KeyError:
              measType = "normal"

          measType = "Pedestal"
          if not measType in list(meas_dict.keys()):

                 meas_dict[measType] = []
 
          meas_dict[measType].append(meas_num)

      f.close() 

      self.measTypeDict =  meas_dict

def main():

    isBinary = 0
    print("Len of args:" ,len(sys.argv))

    if len(sys.argv) < 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    if len(sys.argv) > 2:   isBinary = sys.argv[2] 

    input_dir = "../data/Raw/"
    output_dir = "../data/Processed/" + runName + "/"
    if not (os.path.exists(output_dir)): os.mkdir(output_dir)

    sliceAnalyzeFile = Process(input_dir + "run"+ runName + ".hdf5")
    #sliceAnalyzeFile = Process(input_dir + "Run_" + runName + "_Output.hdf5")
    print((sliceAnalyzeFile.fileName))
    sliceAnalyzeFile.getMeasTypeDict()
    sliceAnalyzeFile.getChannelsAndGains()

    #sliceAnalyzeFile.Gains = [""]
    #sliceAnalyzeFile.Channels = ["channel5","channel6","channel7","channel8"]
    print((sliceAnalyzeFile.measTypeDict))
    print((sliceAnalyzeFile.Channels))
    #mType = "sine_normal"
    mType = "Pedestal"

    sliceAnalyzeFile.getNormalWF(output_dir,mType,isBinary)

if __name__ == "__main__":

    main()
