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

def PulseOverlay(datum,runList):

 fig,ax = plt.subplots()

 ax.grid()
 ax.set_title("Interleaved Pulses")
 ax.set_xlabel("time [ns]")
 ax.set_ylabel("Amplitude [ADC Counts]")
 ax.set_xlim(2000,3500)
 for i,(times,raw_data) in enumerate(datum):

    raw_data[raw_data > 50000] = 0

    time_indices_sorted = times.flatten().argsort()
    interleaved_times = times.flatten()[time_indices_sorted]
    interleaved_samples = raw_data.flatten()[time_indices_sorted]

    n_per_group = 30 
    av_times = np.mean(interleaved_times.reshape(-1,n_per_group),axis = 1)
    av_samples = np.mean(interleaved_samples.reshape(-1,n_per_group),axis = 1)
    plt.plot(av_times,av_samples,'-',label = str(runList[i]))

 plt.legend()
 plt.show()
 plt.cla()
 plt.clf()
 plt.close()

def calc_of_coeffs(ac, g, dg, amp, dg=None, verbose = 0):

    if verbose:
       print("AC",ac,type(ac))
       print("G,",g,type(g))
       print("AMP",amp,type(amp))

    ac = np.ravel(ac) / ac[0]
    g = np.ravel(g)
    dg = np.ravel(dg) #if dg is not None else np.gradient(g)
    #scale = max(g)
    scale = amp
    g /= scale
    dg /= scale
    # Calculate V = R^{-1}.
    inv_ac = linalg.inv(linalg.toeplitz(ac))
    # Calculate V*g and V*dg only once.
    vg = np.dot(inv_ac, g)
    vdg = np.dot(inv_ac, dg)
    # Calculate helper variables.
    q1 = np.dot(g, vg)
    q2 = np.dot(dg, vdg)
    q3 = np.dot(dg, vg)
    delta = q1*q2 - q3*q3
    # Calculate Lagrange multipliers
    lm_lambda = q2/delta
    lm_kappa = -q3/delta
    lm_mu = q3/delta
    lm_rho = -q1/delta
    # Calculate filter coefficients.
    a_coeffs = lm_lambda*vg + lm_kappa*vdg
    b_coeffs = lm_mu*vg + lm_rho*vdg
    # Reverse order to get canonical coefficient order.
    #return a_coeffs[::-1], b_coeffs[::-1]
    return a_coeffs, b_coeffs

def autocorr(x):
  result = np.correlate(x, x, mode='full')
  return result[result.size // 2:]

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
      self.ChanDict = {}
      self.GainDict = {}

    def __repr__(self):

     print("++++++++++++++++++++++++++++++")
     print(("         Run  {name}          ".format(name = self.runNo)))
     print("++++++++++++++++++++++++++++++\n\n")

     
     print(("Gains: " + str(self.Gains)))
     print(("n Channels: " +str(self.nChannels)))
     print(("n Meas: " +str(self.nMeas)))
     print(("Samples per Meas: " +str(self.nSamples)))
     return ""

    def getChannelsAndGains(self):

        print("Getting Channels and Gains from hdf5....\n")

        f = h5py.File(self.fileName,"r")
        self.Channels = list(f["Measurement_0/"].keys())        
        self.Gains = list(f["Measurement_0/{channel}".format(channel = self.Channels[0])].keys())[::-1]        
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
        #self.Samples = np.zeros((len(f),GAINS,CHANNELS,samples_per_meas)) #2 gains, 128 channels

        for meas in range(len(f)):
            for i,gain in enumerate(self.Gains):
                self.GainDict[gain] = i
                for j,channel in enumerate(self.Channels):
                    print((meas, gain, channel))
                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])
                    self.Samples[meas,i,j,:] = raw_data 
                    self.ChanDict[channel] = j

        f.close()


    def PlotRaw(self,plot_dir,meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Plotting raw Pulseestal....\n")

        if not meas_to_plot:  meas_to_plot = list(range(self.nMeas))
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):


              raw_data = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:] 
              print( "\t Meas {meas}; {gain} gain; {channel};".format(meas = meas, gain = gain, channel = channel))   
  
              fig,ax = plt.subplots()
              ax.plot(raw_data[10:],'b.')
              ax.grid(True)
              #ax.set_xlim(0,int(self.nSamples/100))
              ax.set_title(channel + " " + gain + "gain raw data" )
              ax.set_xlabel("sample number")
              ax.set_ylabel("ADC Code")
              plt.savefig('{plot_dir}/rawPulse_meas{meas}_{channel}_{gain}.png'.format(plot_dir = plot_dir,runNo = self.runNo,\
                                                                                               meas = meas,channel =channel, gain = gain))
              plt.show()      
              plt.cla()
              plt.clf()
              plt.close()

    def makeFittedHist(self, data, plot_dir, title, channel,gain,coherent = 0,plot = True):

            do_fit = True
            fig,ax = plt.subplots()

            print("\tMaking Fitted Hist!")
            fit_points = np.linspace(min(data),max(data),1000)
            bins = np.linspace(min(data) - .5, max(data) - .5, int(max(data) - min(data) + 1))

            #if coherent:
            n, bins, _ = ax.hist(data,bins = bins,edgecolor ='black',zorder = 1,label= "RMS = " +str(round(np.std(data),2)) )
            #else: n, bins, _ i      = ax.hist(data,bins = bins,density = 1,edgecolor ='black',zorder = 1,label= "RMS:"+str(round(np.std(data),2)) )
             


            y_max = max(n)
      
            centers = (0.5*(bins[1:]+bins[:-1]))
            if do_fit:
                if coherent: pars, cov = curve_fit(gauss, centers, n, p0=[0,np.std(data),y_max])  
                else: 
                  try:
                    pars, cov = curve_fit(gauss, centers, n, p0=[np.mean(data),np.std(data),y_max])  
                  except:
                    print("WARNING: Could not complete curve fit - using statistical data instead")
                    pars = [np.mean(data),np.std(data)]
                    cov = np.array([[0,0,0],[0,0,0],[0,0,0]]) 
                    do_fit = False
                #print(cov)
                mu, dmu = pars[0], np.sqrt(cov[0,0 ]) 
                sigma, dsigma = pars[1], np.sqrt(cov[1,1 ])  
                #print((sigma, dsigma))

            if plot:
              if do_fit:
            #ax.plot(fit_points, gauss(fit_points,*pars), 'k-',linewidth = 1, label='$\mu=${:.1f}$\pm${:.1f}, $\sigma=${:.1f}$\pm${:.1f}'.format(mu,dmu,sigma,dsigma))   
                 ax.plot(fit_points, gauss(fit_points,*pars), 'r-',linewidth = 2,label='$\mu=${:.1f}$\pm${:.1f}, $\sigma=${:.1f}$\pm${:.1f}'.format(mu,dmu,sigma,dsigma))        

              ax.legend()
              ax.set_xlabel("Sample Value [ADC Counts]")
              ax.set_ylabel("Events")
              #ax.set_ylabel("Normalized Frequency")
              ax.set_title(title)# + " (N = {N})".format(N = len(data)))
              if coherent: ax.set_xlabel("$\Sigma_{Ch} (S_{i} - \\bar{S})$ [ADC Counts]",horizontalalignment='right', x=1.0)
              if coherent: ax.set_title(title )
              ax.xaxis.set_major_locator(MaxNLocator(integer=True))
              #ax.xaxis.set_tick_params(rotation=45)
              ax.set_ylim(0,y_max*(1 + .3))
              ax.grid(zorder = 0)
              #ax.set_xlim(42900,43100)
              if coherent: 
                  #ax.text(.6,.8,"$E[\sigma] = "  + str(round(coherent,3)) + "$",transform = ax.transAxes)
                  formula = "\sqrt{ \Sigma (\sigma_i)^2}" 
                  ax.text(.6,.75,"${}= {:.1f}\pm{:.1f} $".format(formula,coherent[0],coherent[1]),transform = ax.transAxes)

                  #ax.text(.6,.8,"$E[\sigma] = {:.1f}\pm{:.1f} $".format(coherent[0],coherent[1]),transform = ax.transAxes)

              print(("Plotting Baseline hist for " + channel + " " + gain + " gain..."))
              #plt.show()
              plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_hist.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))
              print(("Figure saved as: ",'{plot_dir}/{channel}_{gain}_pedestal_hist.png'.format(plot_dir = plot_dir,channel = channel,gain = gain)))

            plt.cla()
            plt.clf()
            plt.close()
            #if do_fit:
            return mu, sigma, dsigma, np.std(data)

    def AnalyzeBaseline(self,plot_dir, runName, meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Analyzing baseline....\n")

        if not meas_to_plot:  meas_to_plot = list(range(self.nMeas))
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        mdacChannels = ['channel'+str(i).zfill(3) for i in range(0,128) if i%4 ==2 or i%4  == 3]
        print(mdacChannels)

        mdac_hi = []
        mdac_lo = []
        dre_hi = []
        dre_lo = []
 
        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):

                print((meas,str(gain),str(channel)))
                pedestal = self.Samples[meas,i,self.ChanDict[channel],:]
                mu, sigma, dsig, rms = self.makeFittedHist(pedestal,plot_dir,"Baseline value, Pulse Run",channel,gain)
                print(mu)
                #### USE STD FROM FIT #####
                #if str(channel) in mdacChannels and str(gain) == 'hi': mdac_hi.append((channel[-2:],mu,sigma))
                #elif str(channel) in mdacChannels and str(gain) == 'lo': mdac_lo.append((channel[-2:],mu,sigma))
                #elif not(str(channel) in mdacChannels) and str(gain) == 'hi': dre_hi.append((channel[-2:],mu,sigma))
                #elif not(str(channel) in mdacChannels) and str(gain) == 'lo': dre_lo.append((channel[-2:],mu,sigma))
                #### USE RMS #####
                if str(channel) in mdacChannels and str(gain) == 'hi': mdac_hi.append((channel[-2:],mu,rms))
                elif str(channel) in mdacChannels and str(gain) == 'lo': mdac_lo.append((channel[-2:],mu,rms))
                elif not(str(channel) in mdacChannels) and str(gain) == 'hi': dre_hi.append((channel[-2:],mu,rms))
                elif not(str(channel) in mdacChannels) and str(gain) == 'lo': dre_lo.append((channel[-2:],mu,rms))
 
        tit = ['Hi', 'Lo']
        
        for title,vals in zip(tit,[mdac_hi, mdac_lo]):
          print("HG MDAC: ",dre_hi)
          dataUnpack = [list(t) for t in zip(*vals)]
          if title == "Lo" and False:
            dataUnpack[0].pop(-1)
            dataUnpack[1].pop(-1)
            dataUnpack[2].pop(-1)
          muData = [dataUnpack[0], dataUnpack[1]]
          sigData = [dataUnpack[0], dataUnpack[2]]

          self.PlotSigmaMuSummary(muData, "Means MDAC "+title+ " Gain Run"+runName, plot_dir+"/mdac_"+title+"_mu_run"+runName+".png")
          self.PlotSigmaMuSummary(sigData, "RMS MDAC "+title+" Gain Run"+runName, plot_dir+"/mdac_"+title+"_sig_run"+runName+".png")
        
        for title,vals in zip(tit,[dre_hi, dre_lo]):

          print("HG DRE: ",dre_hi)
          dataUnpack = [list(t) for t in zip(*vals)]
          if title == "Lo" and False:
            dataUnpack[0].pop(-1)
            dataUnpack[1].pop(-1)
            dataUnpack[2].pop(-1)
          muData = [dataUnpack[0], dataUnpack[1]]
          sigData = [dataUnpack[0], dataUnpack[2]]

          self.PlotSigmaMuSummary(muData, "Means DRE "+title+ " Gain Run"+runName, plot_dir+"/DRE-"+title+"_mu_run"+runName+".png")
          self.PlotSigmaMuSummary(sigData, "RMS DRE "+title+" Gain Run"+runName, plot_dir+"/DRE-"+title+"_sig_run"+runName+".png")

    def PlotSigmaMuSummary(self,data,title,saveStr):
        fig,ax = plt.subplots(1)

        ax.bar(data[0],data[1])
        #for i, v in enumerate(data[1]):
        #    ax.text(i+0.25, v+0.5, str(v), color='blue')
        ax.set_title(title)
        plt.xlabel('Channel')
        plt.savefig(saveStr)


        plt.cla()
        plt.clf()
        plt.close()
        return

    def FindTrainStart(self,START = 0, plot = 0):

          """
          Trigger on pulse train 
          """

          raw_data = self.Samples[0,self.GainDict[self.Gains[0]],self.ChanDict[self.Channels[0]],:] 
          print("raw data length: ",len(raw_data))

          baseline = np.mean(raw_data[START: START + 1000])

          ac = autocorr(baseline)

          raw_data = raw_data[START:]  - baseline #subtract baseline

          height = np.max(raw_data)

          low_points = np.copy(raw_data)
          low_points[raw_data < .1*height] = 0 #set data points less that 10% of pulse height to zero

          trigger = np.nonzero(low_points)[0][0] #find index corresponding to first nonzero value of low_points, this is our trigger

          #check
          if plot:
              plt.plot(raw_data,'b.')
              plt.plot(trigger,raw_data[trigger],'r.')
              plt.show()
              plt.cla()
              plt.clf()
              plt.close()

          return ac, baseline, START + trigger

    def Interleave(self,plot_dir, ac, baseline,start_sample, samples_per_pulse = 501,pulses_per_train = 500):

          FLX_FRQ = 40.079 #MHz
          AWG_FRQ = 1200.0 #MHZ 

          sec_per_sample = (1.0/FLX_FRQ) * 1000 #ns
          offset = (1.0/AWG_FRQ) * 1000 #ns


          print("Seconds per sample: ", sec_per_sample)
          print("AWG offset: ", -offset)

          raw_data = self.Samples[0,self.GainDict[self.Gains[0]],self.ChanDict[self.Channels[0]],:]

          raw_data -= baseline

          start_sample -= 100 #cushion

          raw_data = raw_data[start_sample: start_sample +  samples_per_pulse*pulses_per_train]


          raw_data = raw_data.reshape(pulses_per_train,samples_per_pulse)
          n_phases = 30

          times = np.zeros(np.shape(raw_data))
     
          for j in range(pulses_per_train):  

              times[j,:] = np.arange(samples_per_pulse)*sec_per_sample + j*offset
              #plt.plot(np.arange(samples_per_pulse)*sec_per_sample + j*offset, raw_data[j,:])
              #plt.plot(times[j,:], raw_data[j,:])

          time_indices_sorted = times.flatten().argsort()
          interleaved_times = times.flatten()[time_indices_sorted]
          interleaved_samples = raw_data.flatten()[time_indices_sorted]


          plt.plot(times.flatten(),'k.')
          plt.show()

          n_per_group = 30 
          av_times = np.mean(interleaved_times.reshape(-1,n_per_group),axis = 1)
          av_samples = np.mean(interleaved_samples.reshape(-1,n_per_group),axis = 1)

          OFCs = calc_of_coeffs(ac, av_samples, av_times)

          #plt.plot(np.mean(interleaved_times.reshape(-1,n_per_group),axis = 1),np.mean(interleaved_samples.reshape(-1,n_per_group),axis = 1),'b-')
          #plt.show()

          return OFCs, times, raw_data

    def PlotRaw(self,plot_dir,meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Plotting raw Pedestal....\n")

        if not meas_to_plot:  meas_to_plot = list(range(self.nMeas))
        if not gains_to_plot: gains_to_plot = self.Gains
        if not chans_to_plot: chans_to_plot = self.Channels

        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):


              raw_data = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:] 
              print( "\t Meas {meas}; {gain} gain; {channel};".format(meas = meas, gain = gain, channel = channel))   
  
              fig,ax = plt.subplots()
              ax.plot(raw_data[10:],'b.')
              ax.grid(True)
              #ax.set_xlim(0,int(self.nSamples/100))
              ax.set_title(channel + " " + gain + "gain raw data" )
              ax.set_xlabel("sample number")
              ax.set_ylabel("ADC Code")
              plt.savefig('{plot_dir}/rawPed_meas{meas}_{channel}_{gain}.png'.format(plot_dir = plot_dir,runNo = self.runNo,\
                                                                                               meas = meas,channel =channel, gain = gain))
              #plt.show()      
              plt.cla()
              plt.clf()
              plt.close()

def main():

    if len(sys.argv) < 2 :
        print("ERROR, program requires filename argument")
        return 

    runList = sys.argv[1:]

    datum = []

    for runName in runList:

	    input_dir = "../data/Processed/" + runName + "/"
	    plot_dir = "../data/Processed/" + runName + "/Plots"
	    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

	    PulseData = AnalyzePulse(input_dir + "Data_Normal.hdf5",runName)


	    PulseData.getChannelsAndGains()
	    #### IF YOU WANT TO SET SPECIFIC CHANNELS/GAINS TO ANALYZE #####
	    ##### you can do it here
            PulseData.Gains = ["hi"]
            PulseData.Channels = ["channel079"]

	    print(("Gains: ",PulseData.Gains))
	    print(("Channels: ",PulseData.Channels))

	    PulseData.getSamples() 
	    PulseData.getDimensions()
            #PulseData.PlotRaw(plot_dir,chans_to_plot = ["channel079"])
 
            
            ac, baseline,start_sample = PulseData.FindTrainStart(START = 250000)

            print("Baseline,start_sample: ",baseline,start_sample)
            times, raw_data =  PulseData.Interleave(plot_dir, ac, baseline, start_sample)

            datum.append((times,raw_data))

    #PulseOverlay(datum,runList)

if __name__ == "__main__":

    main()



