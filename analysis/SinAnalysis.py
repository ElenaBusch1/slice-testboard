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
import atlas_plotter as plotter
from helperfunctions import *
import time
from itertools import product

dataDir = checkDir(getRootDir()+"/Data/Processed/Sine/")

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


if __name__ == "__main__":

  t_start = time.time()

  print("\n\nCOLUTA Sine Analysis\n\n")

  #Get directories to run in
  parser = argparse.ArgumentParser()
  #Allow user input for choice of runs
  parser.add_argument("-r", "--runs", default = [], type=str, nargs='+',
                     help="list of runs (directories in Data/Processed/) to include")

  args = parser.parse_args()

  runs = [dataDir + run + "/" for run in args.runs]

  f = h5py.File(runs[0] + "/Sine_Data_1x.hdf5","r")

  N_MEAS_PER_CHANNEL = 10
  N_CHANNELS = 8
 
  MEAS_TO_SAVE = np.arange(N_CHANNELS)*N_MEAS_PER_CHANNEL #take a look at the first measurement from each channel

  print("MEAS_TO_SAVE",MEAS_TO_SAVE)

  resultsDir = checkDir(getRootDir()+"/TestPlots/" + short(runs[0]))
  results_dict = {}

  for meas in range(0,N_MEAS_PER_CHANNEL*8): #only include mdac channels 
  #for meas in range(N_MEAS_PER_CHANNEL*4,N_MEAS_PER_CHANNEL*8): #only include mdac channels 
  #for meas in range(0,N_MEAS_PER_CHANNEL): #only include mdac channels 

    #print(meas)
    this_chan = f['Measurement_'  +  str(meas) + '/coluta1'].attrs["channels"]  
    if not(this_chan[0]) in results_dict.keys():

        results_dict[this_chan[0]] = {"ENOB":[],"SINAD":[],"SFDR":[],"SNR":[]}

    #print(meas,this_chan)
    #print('Measurement_'  +  str(meas) + '/coluta1/' + str(this_chan[0]) + '/samples') 
    waveform = f['Measurement_'  +  str(meas) + '/coluta1/' + str(this_chan[0]) + '/samples'][()]

    waveform = waveform[1:] #DROP FIRST SAMPLE TO GET 6251 SAMPLES!!!! critical

    #print(waveform)

    if meas in (MEAS_TO_SAVE):

            print("PLOTTING MEASUREMENT",meas)
            plt.plot(waveform[:1000],'b.')
            plt.grid()
            plt.ylabel("ADC Code")
            plt.xlabel("time [ns]")
            plt.ylim(0,32000)
            #plt.show()
            plt.savefig(resultsDir + "/" + this_chan[0] + "/rawSin.png")
            plt.close()
            plt.clf()

    fftWf_x,fftWf_y, psd_x,psd,sinad,enob,snr = getFftWaveform(waveform)

    sfdr = GetSFDR(fftWf_x,fftWf_y)
    
    if meas in (MEAS_TO_SAVE):

            plt.plot(psd_x,psd,'b-')
            plt.grid()
            plt.xlabel("Frequency [MHz]")
            plt.ylabel("PSD [dB]")
            #plt.show()
            plt.savefig(resultsDir + "/" + this_chan[0] + "/sinFFT.png")
            plt.close()
            plt.clf()

    print(sinad,enob)
    results_dict[this_chan[0]]["ENOB"].append(enob)
    results_dict[this_chan[0]]["SINAD"].append(sinad)
    results_dict[this_chan[0]]["SFDR"].append(sfdr)
    results_dict[this_chan[0]]["SNR"].append(snr)

  print(results_dict)
  f.close()

  g = open(resultsDir + "/SineResults.txt","w")
  for channel in results_dict.keys():

      print("Channel: " + str(channel))
      print("mean ENOB: " + str(np.mean(results_dict[channel]["ENOB"]))) 
      print("mean SINAD: " + str(np.mean(results_dict[channel]["SINAD"]))) 
      print("mean SFDR: " + str(np.mean(results_dict[channel]["SFDR"]))) 
      print("mean SNR: " + str(np.mean(results_dict[channel]["SNR"]))) 

      g.write("Channel: " + str(channel) + "\n")
      g.write("mean ENOB: " + str(np.round(np.mean(results_dict[channel]["ENOB"]),3)) + "\n") 
      g.write("mean SNDR: " + str(np.round(np.mean(results_dict[channel]["SINAD"]),3)) + "\n") 
      g.write("mean SNR: " + str(np.round(np.mean(results_dict[channel]["SNR"]),3))+ "\n") 
      g.write("mean SFDR: " + str(np.round(np.mean(results_dict[channel]["SFDR"]),5))+ "\n") 

  g.close()
