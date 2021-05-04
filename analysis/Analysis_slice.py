import matplotlib
matplotlib.use("TkAgg")
#from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit
import csv
import matplotlib
matplotlib.use("TkAgg")
from matplotlib import pyplot as plt
from pylab import MaxNLocator     
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

def gauss(x, b, c, a):
    return a * np.exp(-(x - b)**2.0 / (2 * c**2))

class Analyze(object):

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
      self.ChanDict = {}
      self.GainDict = {}

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
        print(self.fileName)

        f = h5py.File(self.fileName,"r")
        self.Channels = f["Measurement_0/"].keys()        
        self.Gains = f["Measurement_0/{channel}".format(channel = self.Channels[0])].keys()[::-1]        
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
        print("Measurement_0/{channel}/{gain}/samples".format(channel = str(self.Channels[0]),gain = self.Gains[0]))
        samples_per_meas = len(f["Measurement_0/{channel}/{gain}/samples".format(channel = str(self.Channels[0]),gain = self.Gains[0])])

        self.Samples = np.zeros((len(f),len(self.Gains),len(self.Channels),samples_per_meas))
        #self.Samples = np.zeros((len(f),GAINS,CHANNELS,samples_per_meas)) #2 gains, 128 channels

        for meas in range(len(f)):
            for i,gain in enumerate(self.Gains):
                self.GainDict[gain] = i
                for j,channel in enumerate(self.Channels):
                    print(meas, gain, channel)
                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
                    self.Samples[meas,i,j,:] = raw_data 
                    self.ChanDict[channel] = j

        f.close()


    def PlotRaw(self,plot_dir,meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Plotting raw Pedestal....\n")

        if not meas_to_plot:  meas_to_plot = range(self.nMeas)
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):


              raw_data = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:] 

              #if max(raw_data) > 2**15: continue
              #if len(raw_data) <1: continue 
       	      #if min(raw_data) == max(raw_data): continue
  
              fig,ax = plt.subplots()
              ax.plot(raw_data[10:10 + int(self.nSamples*.1)],'b.')
              ax.grid(True)
              ax.set_xlim(0,int(self.nSamples*.1))
              ax.set_ylim(0,2**16)
              ax.set_title(channel + " " + gain + "gain raw data" )
              ax.set_xlabel("sample number")
              ax.set_ylabel("ADC Code")
              #plt.savefig('{plot_dir}/rawPed_meas{meas}_{channel}_{gain}.png'.format(plot_dir = plot_dir,runNo = self.runNo,\
              #                                                                                 meas = meas,channel =channel, gain = gain))
              plt.show()      
              plt.cla()
              plt.clf()
              plt.close()
              #self.getFftWaveform(raw_data,plot_dir,channel,gain)

