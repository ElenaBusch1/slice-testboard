import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import csv
from matplotlib import pyplot as plt
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



class AnalyzeSin(object):

    #__INIT__#
    def __init__(self, fileName = None,run_no = None):

      self.fileName = fileName
      self.runNo = run_no
      self.measTypeDict = None
      self.Gains = None
      self.Channels = None

    def getChannelsAndGains(self):

        f = h5py.File(self.fileName,"r")
        self.Channels = f["Measurement_0/"].keys()        
        self.Gains = f["Measurement_0/{channel}".format(channel = self.Channels[0])].keys()        
        f.close()

    def makePlots(self,plot_dir):

        f = h5py.File(self.fileName,"r")

        for meas in range(len(f)):
            for gain in self.Gains:

                for channel in self.Channels:


                    
                    try:
                        raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
              
                    except KeyError:
                        continue

                    if (max(raw_data) - min(raw_data) < 2000): continue
                    fig,ax = plt.subplots()


                    even_raw_data = raw_data[raw_data%2 == 0]
                    even_raw_data_index = np.arange(len(raw_data))[raw_data%2 == 0]

                    percent_even = 100*round(len(even_raw_data)*1.0/len(raw_data),2)

                    ax.plot(raw_data,'b.')
                    ax.plot(even_raw_data_index,even_raw_data,'k.',label = "Even code, " + str(percent_even) + "%")
                    ax.grid(True)
                    #ax.set_xlim(0,100)
                    #ax.set_ylim(7075,7275)
                    ax.set_title("Run " + self.runNo +" " +  channel + " " + gain + "gain raw data" )
                    ax.set_xlabel("sample number")
                    ax.set_ylabel("ADC Code")
                    ax.legend(loc = "upper right")
                    plt.savefig(plot_dir + "/rawSin_" +str(meas) + channel + gain + ".png") 
                    #plt.show() 
                    plt.cla()
                    plt.clf()
                    plt.close()

        f.close()


def ENOB(fourier):
    return (SINAD(fourier)-1.76)/6.02


def GetSFDR(fft_x,fft_y):
   
    largest = 0
    second_largest = 0
    for i,val in enumerate(fft_y):

        if val > largest:
            largest = val
            largest_freq = fft_x[i]
        elif largest > val  > second_largest:
            second_largest = val
            second_largest_freq = fft_x[i]
 
    print(largest,largest_freq)
    print(second_largest,second_largest_freq)   

    return(second_largest/largest)

def SINAD(fourier):
    sum2 = 0
    for normBin in fourier:
      if normBin==1: continue
      sum2 += normBin**2
    return -10*np.log10(sum2)

def SNR(fourier):
    sum2 = 0

    fourier.sort()
    fourier = fourier[:-3] #remove signal and first two harmonics

    for normBin in fourier:
      if normBin==1: continue
      sum2 += normBin**2
    return -10*np.log10(sum2)    

def getFftWaveform(vals):
    fft_wf = np.fft.fft(vals)
    fftWf_x = []
    fftWf_y = []
    psd = []
    psd_x = []
    for sampNum,samp in enumerate(fft_wf) :
      if sampNum > float( len(fft_wf) ) / 2. :
        continue
      freqVal = 40. * sampNum/float(len(fft_wf))
      sampVal = np.abs(samp)
      if sampNum == 0 :
        sampVal = 0
      fftWf_x.append(freqVal)
      fftWf_y.append(sampVal)
    if np.max(fftWf_y) <= 0 :
      return psd_x,psd

    fourier_fftWf_y = fftWf_y/np.max(fftWf_y)
    for sampNum,samp in enumerate(fourier_fftWf_y) :
      if sampNum == 0 :
        continue
      else:
        psd_x.append( fftWf_x[sampNum] )
        psd.append( 20*np.log10(samp) )
    sinad = SINAD(fourier_fftWf_y)
    enob = ENOB(fourier_fftWf_y)
    snr = SNR(fourier_fftWf_y)

    print("SINAD: ", sinad)
    print("ENOB: ", enob)
    print("SNR: ", snr)

    return fftWf_x,fftWf_y,psd_x,psd,sinad,enob,snr


def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/Processed/" + runName + "/"
    plot_dir = "../data/Processed/" + runName + "/Plots"
    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

    SineData = AnalyzeSin(input_dir + "Sine_Data_Normal.hdf5",runName)

    #SineData.getChannelsAndGains()

    SineData.Channels = ["channel5","channel6","channel7","channel8"]
    SineData.Gains = ["lo"]#,"channel6","channel7","channel8"]

    SineData.makePlots(plot_dir)

if __name__ == "__main__":

    main()



