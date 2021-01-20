import numpy as np
from math import *
import sys
import h5py
#BEGIN SLICE PROCESS DATAFILE CLASS

class Process(object):

    #__INIT__#
    def __init__(self, fileName = None):

      self.fileName = fileName
      self.mdacWeights = [4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288, 4*4288]
      self.sarWeights = [4*3584,4*2048,4*1024,4*640,4*384,4*256,4*128,4*224,4*128,4*64,4*32,4*24,4*16,4*10,4*6,4*4,4*2,4*1,4*0.5,4*0.25]
      self.measTypeDict = None

    def getMeasTypeDict(self):

      f = h5py.File(self.fileName,"r")

      for ch_num in range(len(f)):

          #raw_data_msbs = np.array(input_file["{address_1}/raw_data".format(address_1 = address_1)])
          print(f["channel{ch_num}/lo/samples".format(ch_num = ch_num)][:])
  
      f.close() 

      return

def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/"

    sliceAnalyzeFile = Process(input_dir + runName + "_test_trigger-1.hdf5")
    print(sliceAnalyzeFile.fileName)
    sliceAnalyzeFile.getMeasTypeDict()

if __name__ == "__main__":

    main()
