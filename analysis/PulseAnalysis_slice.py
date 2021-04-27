import numpy as np
from scipy.optimize import curve_fit
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
      self.nChannels = None
      self.nGains = None
      self.nSamples = None
      self.nMeas = None
      self.Interleaved = None
      self.Trains = None


    def __repr__(self):

     print("++++++++++++++++++++++++++++++")
     print("         Run  {name}          ".format(name = self.runNo))
     print("++++++++++++++++++++++++++++++\n\n")

     
     print("Gains: " + str(self.Gains))
     print("n Channels: " +str(self.nChannels))
     print("n Meas: " +str(self.nMeas))
     print("Samples per Meas: " +str(self.nSamples))
     return ""

    def getChannelsAndGains(self):

        print("Getting Channels and Gains from hdf5....\n")

        f = h5py.File(self.fileName,"r")
        self.Channels = f["Measurement_0/"].keys()        
        self.Gains = f["Measurement_0/{channel}".format(channel = self.Channels[0])].keys()        
        f.close()

    def getDimensions(self):

        print("Getting Dimensionality....\n")

        self.nChannels = len(self.Channels)
        self.nGains = len(self.Gains)
        self.nSamples = np.shape(self.Samples)[-1]
        self.nMeas = np.shape(self.Samples)[0]
        

    def getSamples(self):

        print("Getting Samples from hdf5....\n")

        f = h5py.File(self.fileName,"r")

        samples_per_meas = len(f["Measurement_0/{channel}/{gain}/samples".format(channel = str(self.Channels[0]),gain = self.Gains[0])])

        self.Samples = np.zeros((len(f),len(self.Gains),len(self.Channels),samples_per_meas))

        for meas in range(len(f)):
            for i,gain in enumerate(self.Gains):
                for j,channel in enumerate(self.Channels):
                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
                     
                    self.Samples[meas,i,j,:] = raw_data 


        f.close()

    def PlotRaw(self,plot_dir,meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Plotting raw pulses....\n")

        if not meas_to_plot:  meas_to_plot = range(self.nMeas)
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):


              raw_data = self.Samples[meas,i,j,:] 
              fig,ax = plt.subplots()
              ax.plot(raw_data,'b.')
              ax.grid(True)
              ax.set_xlim(0,int(self.nSamples/100))
              ax.set_title(channel + " " + gain + "gain raw data" )
              ax.set_xlabel("sample number")
              ax.set_ylabel("ADC Code")
              plt.savefig('{plot_dir}/rawPulse_meas{meas}_{channel}_{gain}.png'.format(plot_dir = plot_dir,runNo = self.runNo,\
                                                                                               meas = meas,channel =channel, gain = gain))
                    
              plt.cla()
              plt.clf()
              plt.close()
    
    def PlotInterleaved(self,plot_dir,meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Plotting interleaved Pulses from continuous measurerment....\n")

        if not meas_to_plot:  meas_to_plot = range(np.shape(self.Interleaved)[0])
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        print(np.shape(self.Interleaved)[0],gains_to_plot,chans_to_plot)
        print(np.shape(self.Interleaved))

        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):

                   fig,ax = plt.subplots()
                   #print("Plotting meas " + str(meas))
                   #channel = "channel" + str(j + 28); gain = str(i)
                   #ax.plot(,'b.')
                   ax.plot(self.Interleaved[meas,i,j,:],'b.')
                   ax.plot(self.Trains[meas,i,j,:],'r.')
                   spp = 64
                   ax.plot(np.arange(0,len(self.Trains[meas,i,j,::spp]))*spp,self.Trains[meas,i,j,::spp],'g.')
                   ax.grid(True)
                   #ax.set_ylim(7000,8000)
                   #ax.set_ylim(6000,11000)
                   ax.set_title(channel + " " + gain + " gain raw data" )
                   ax.set_xlabel("sample number")
                   ax.set_ylabel("ADC Code")
                   plt.savefig(r'{plot_dir}/interleavedPulse_meas{meas}_{channel}_{gain}.png'.format(plot_dir = plot_dir,runNo = self.runNo,\
                                                                                               meas = meas,channel =channel, gain = gain))
                   #plt.show()
                   plt.cla()
                   plt.clf()
                   plt.close()

 
    def InterleaveContinuous(self,plot_dir,spp = 64,n_phases = 11):

        MAX_ALIGN_INDEX = 200

        len_data = self.nSamples
        tmp = np.zeros(np.shape(self.Samples))
        tmp = tmp[:,:,:,:int((len_data//(spp*n_phases))*spp*n_phases)]
        self.Samples = self.Samples[:,:,:,:int((len_data//(spp*n_phases))*spp*n_phases)]
        n_trains = self.nSamples/(spp*n_phases)
        #trains = np.reshape(self.Samples,(np.shape(tmp)[-1]/(spp*n_phases),np.shape(tmp)[1],np.shape(tmp)[2],spp*n_phases))

        trains = np.reshape(self.Samples,(n_trains,self.nGains,self.nChannels,spp*n_phases))
        interleaved = np.zeros(np.shape(trains))
        #for meas in range(np.shape(trains)[0]):
        print("N_TRAINS: ",n_trains)
        for meas in range(n_trains):
         for i,gain in enumerate(self.Gains):
          for j,channel in enumerate(self.Channels):

           #for sample_ind,sample in enumerate(trains[meas,i,j,:-1]):
           for sample_ind,sample in enumerate(trains[meas,i,j,:]):

               if trains[meas,i,j,(sample_ind*spp)%(spp*n_phases -1)] == 0:  print( trains[meas,i,j,(sample_ind*spp)%(spp*n_phases -1)])
               interleaved[meas,i,j,sample_ind] = trains[meas,i,j,(sample_ind*spp)%(spp*n_phases -1)] 
            
           interleaved[meas,i,j,:] = reverseGroup(interleaved[meas,i,j,:],n_phases)

           peak_index = np.argmax(interleaved[meas,i,j,:])
           interleaved[meas,i,j,:] = np.roll(interleaved[meas,i,j,:],-peak_index + MAX_ALIGN_INDEX)

        print(np.shape(interleaved)) 
        #print(np.shape(av_train))
        self.Interleaved = interleaved 
        self.Trains = trains

    def AnalyzePeaks(self,plot_dir):
        
        n_trains = np.shape(self.Trains)[0]

        for i,gain in enumerate(self.Gains):
         for j,channel in enumerate(self.Channels):
        
            peaks = self.Interleaved[:,i,j,200] - np.mean(self.Interleaved[:,i,j,500:],axis = -1)


            self.makeFittedHist(peaks)

    def AnalyzeBaseline(self,plot_dir):
        
        n_trains = np.shape(self.Trains)[0]
        train_len = np.shape(self.Trains)[-1]

        baseline_samples = []
        for i,gain in enumerate(self.Gains):
         for j,channel in enumerate(self.Channels):
          for t in range(n_trains):
           for k in range(500,train_len):
        
             baseline_samples.append(self.Interleaved[t,i,j,k])


          self.makeFittedHist(baseline_samples)

    def PlotAvInterleaved(self,plot_dir):
        
        plt.plot(np.mean(self.Interleaved[:,0,0,:],axis = 0))
        plt.show()

    def makeFittedHist(self,data):

            fir,ax = plt.subplots()

            fit_points = np.linspace(min(data),max(data),1000)
            bins = np.linspace(min(data) - .5, max(data) - .5, max(data) - min(data) + 1)
                  
            n, bins, _ = ax.hist(data,bins = bins, density =1,edgecolor ='black',zorder = 1,label='Mean: '+str(round(np.mean(data),3))+", std:"+str(round(np.std(data),3)) )
            y_max = max(n)
            
            centers = (0.5*(bins[1:]+bins[:-1]))
            pars, cov = curve_fit(lambda x, mu, sig : stats.norm.pdf(x, loc=mu, scale=sig), centers, n, p0=[np.mean(data),np.std(data)])  

            mu, dmu = pars[0], np.sqrt(cov[0,0 ]) 
            sigma, dsigma = pars[1], np.sqrt(cov[1,1 ])  

            ax.plot(fit_points, stats.norm.pdf(fit_points,*pars), 'k-',linewidth = 1, label='$\mu=${:.4f}$\pm${:.4f}, $\sigma=${:.4f}$\pm${:.4f}'.format(mu,dmu,sigma,dsigma))   
            ax.plot(centers, stats.norm.pdf(centers,*pars), 'r.',linewidth = 2)        
            ax.legend()
            ax.set_xlabel("Sample Value [ADC Counts]")
            ax.set_ylabel("Normalized Frequency")
            ax.set_title("Baseline Value Continuous Pulse Run (N = {N})".format(N = len(data))) 
            ax.set_ylim(0,y_max*(1 + .3))
            ax.grid(zorder = 0)
            plt.show()
            plt.cla()
            plt.clf()
            plt.close()




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

    #print("Gains: ",PulseData.Gains)
    #print("Channels: ",PulseData.Channels)

    #### IF YOU WANT TO SET SPECIFIC CHANNELS/GAINS TO ANALYZE #####
    ##### you can do it here

    PulseData.Channels = ["channel028"]
    PulseData.Gains = ["hi"]


    PulseData.getSamples() 
    PulseData.getDimensions()
    print(PulseData)

    PulseData.InterleaveContinuous(plot_dir)

    ### MAKE RAW AND INTERLEAVED PLOTS
    #PulseData.PlotRaw(plot_dir)
    #PulseData.PlotInterleaved(plot_dir)#,meas_to_plot)# = range(10))
    #PulseData.PlotAvInterleaved(plot_dir)
    
    #PulseData.AnalyzePeaks(plot_dir)
    PulseData.AnalyzeBaseline(plot_dir)


if __name__ == "__main__":

    main()



