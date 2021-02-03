import numpy as np
import csv
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from scipy import linalg
import os
import glob
import sys
import h5py
from scipy import stats 
from scipy.stats import norm
from optparse import OptionParser
import argparse
import time
from itertools import product


def reverseGroup(input,k): 
  
    # set starting index at 0 
    start = 0
  
    # run a while loop len(input)/k times 
    # because there will be len(input)/k number  
    # of groups of size k  
    result = [] 
    while (start<len(input)): 
  
           # if length of group is less than k 
           # that means we are left with only last  
           # group reverse remaining elements  
           if len(input[start:])<k: 
                result = result + list(reversed(input[start:])) 
                break
  
           # select current group of size of k 
           # reverse it and concatenate  
           result = result + list(reversed(input[start:start + k])) 
           start = start + k 
    return result

class AnalyzePulse(object):

    #__INIT__#
    def __init__(self, fileName = None,run_no = None):

      self.fileName = fileName
      self.runNo = run_no
      self.measTypeDict = None
      self.Gains = None
      self.Channels = None
      self.Samples = None

    def getChannelsAndGains(self):

        f = h5py.File(self.fileName,"r")
        self.Channels = f["Measurement_0/"].keys()        
        self.Gains = f["Measurement_0/{channel}".format(channel = self.Channels[0])].keys()        
        f.close()

    def makePlots(self,plot_dir):

        f = h5py.File(self.fileName,"r")

        self.Samples = np.zeros((len(f),len(self.Gains),len(self.Channels),187494))

        for meas in range(len(f)):
            for i,gain in enumerate(self.Gains):

                for j,channel in enumerate(self.Channels):

                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
                     
                    self.Samples[meas,i,j,:] = raw_data 

                    fig,ax = plt.subplots()

                    ax.plot(raw_data,'b.')
                    ax.grid(True)
                    ax.set_xlim(187000,187494)
                    #ax.set_ylim(7075,7275)
                    ax.set_title(channel + " " + gain + "gain raw data" )
                    ax.set_xlabel("sample number")
                    ax.set_ylabel("ADC Code")
                    plt.savefig(plot_dir + "/" + self.runNo + "_rawPulse_" +str(meas) +"_" +  channel + "_" + gain + ".png") 
                    
                    plt.cla()
                    plt.clf()
                    plt.close()

        f.close()
        print(self.Samples.shape)
       

    def InterleaveContinuous(self,plot_dir):

        spp = 64
        n_phases = 12

        len_data = np.shape(self.Samples)[-1]

        inter = np.zeros(np.shape(self.Samples))
        inter = inter[:,:,:,:int((len_data//(spp*n_phases))*spp*n_phases)]
        self.Samples = self.Samples[:,:,:,:int((len_data//(spp*n_phases))*spp*n_phases)]
        trains = np.reshape(self.Samples,(np.shape(inter)[-1]/(spp*n_phases),np.shape(inter)[1],np.shape(inter)[2],spp*n_phases))

        #av_train = np.mean(trains,axis = 0)
        for meas in range(np.shape(trains)[0]):
                pass
                '''
		fig,ax = plt.subplots()
                print("Plotting meas " + str(meas))
		ax.plot(trains[meas,0,0,:],'b.')
		#ax.plot(interleaved[k,i,j,:-1],'b.')
		ax.grid(True)
		ax.set_xlabel("sample number")
		ax.set_ylabel("ADC Code")
		plt.savefig(plot_dir + "/MEAS_" +str(meas) + self.runNo +  ".png") 
		#plt.show()
		plt.cla()
		plt.clf()
		plt.close()
                '''

        MAX_ALIGN_INDEX = 200
        print("N_MEAS: ",np.shape(trains)[0])
        for meas in range(np.shape(trains)[0]):

           interleaved = np.zeros(np.shape(trains))

           for sample_ind,sample in enumerate(trains[meas,0,0,:-1]):

               if trains[meas,0,0,(sample_ind*spp)%(spp*n_phases -1)] == 0:  print( trains[meas,0,0,(sample_ind*spp)%(spp*n_phases -1)])
               interleaved[meas,0,0,sample_ind] = trains[meas,0,0,(sample_ind*spp)%(spp*n_phases -1)] 

           interleaved[meas,0,0,:] = reverseGroup(interleaved[meas,0,0,:],n_phases)

           peak_index = np.argmax(interleaved[meas,0,0,:])
           print("PEAK_INDEX",peak_index)
           print(-peak_index + MAX_ALIGN_INDEX)
           interleaved[meas,0,0,:] = np.roll(interleaved[meas,0,0,:],-peak_index + MAX_ALIGN_INDEX)

           #print("interleaved: ",interleaved[meas,0,0,:-1])

           i = 0; j = 0; 
  	   fig,ax = plt.subplots()
	   print("Plotting meas " + str(meas))
 	   #print("interleaved: ",interleaved[meas,i,j,:-1])
	   channel = "channel" + str(j + 28); gain = str(i)
	   #ax.plot(,'b.')
	   ax.plot(interleaved[meas,i,j,:-1],'b.')
	   ax.plot(trains[meas,i,j,:],'r.')
	   ax.plot(np.arange(0,len(trains[meas,i,j,::64]))*64,trains[meas,i,j,::64],'g.')
	   ax.grid(True)
	   #ax.set_xlim(0,100)
	   ax.set_ylim(6000,11000)
	   ax.set_title(channel + " " + gain + " gain raw data" )
	   ax.set_xlabel("sample number")
	   ax.set_ylabel("ADC Code")
	   plt.savefig(plot_dir + "/MEAS_" +str(meas) + "_PHASE_" +str(n_phases) + "_" +  self.runNo + "_avInterleaved_"  + channel + gain + ".png") 
	   #plt.show()
	   plt.cla()
	   plt.clf()
	   plt.close()
        
        #print(np.shape(av_train))
        return interleaved 

def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/Processed/" + runName + "/"
    plot_dir = "../data/Processed/" + runName + "/Plots"
    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

    PulseData = AnalyzePulse(input_dir + "Pulse_Data_Normal.hdf5",runName)

    PulseData.getChannelsAndGains()

    print("Gains: ",PulseData.Gains)
    print("Channels: ",PulseData.Channels)

    PulseData.Channels = ["channel028"]
    PulseData.Gains = ["hi"]

    PulseData.makePlots(plot_dir)

    PulseData.InterleaveContinuous(plot_dir)


if __name__ == "__main__":

    main()



