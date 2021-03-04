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

class AnalyzePed(object):

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

              if max(raw_data) > 2**15: continue
              if len(raw_data) <1: continue 
       	      if min(raw_data) == max(raw_data): continue
  
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
              self.getFftWaveform(raw_data,plot_dir,channel,gain)
             
    def getFftWaveform(self,data,plot_dir,channel,gain):

            data = data[1:] #DROP FIRST SAMPLE TO GET 6251 SAMPLES!!!! critical
            fft_wf = np.fft.fft(data)
	    fftWf_x = []
	    fftWf_y = []
	    psd = []
	    psd_x = []
	    for sampNum,samp in enumerate(fft_wf) :
	      if sampNum > float( len(fft_wf) ) / 2. :
		continue
	      freqVal = 40.8 * sampNum/float(len(fft_wf))
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

            plt.plot(psd_x,psd,'b-')
            plt.grid()
            plt.xlim(0,2)
            plt.ylim(-100,0)
            plt.xlabel("Frequency [MHz]")
            plt.ylabel("PSD [dB]")
            plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_FFT.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))
            #plt.show()
            plt.close()
            plt.clf()


    def makeFittedHist(self, data, plot_dir, title, channel,gain,coherent = 0,plot = True):

            do_fit = True
            fig,ax = plt.subplots()

            print("here!",max(data))
            #if max(data) > 2**15: return
            #if len(data) <1: return 
	    #if min(data) == max(data): return
            # data = data[data > 0]
            # data = data[data < 2**15]
	    fit_points = np.linspace(min(data),max(data),1000)
            bins = np.linspace(min(data) - .5, max(data) - .5, max(data) - min(data) + 1)

            if coherent: n, bins, _ = ax.hist(data,bins = bins,density = False,edgecolor ='black',zorder = 1,label= "std:" +str(round(np.std(data),2)) )
            else: n, bins, _ = ax.hist(data,bins = bins,density = 1,edgecolor ='black',zorder = 1,label= "Mean:"+str(round(np.mean(data),3))+", std:"+str(round(np.std(data),3)) )

            y_max = max(n)
  	    
	    centers = (0.5*(bins[1:]+bins[:-1]))
            if do_fit:
                if coherent: pars, cov = curve_fit(gauss, centers, n, p0=[0,np.std(data),y_max])  
                else: pars, cov = curve_fit(lambda x, mu, sig : stats.norm.pdf(x, loc=mu, scale=sig), centers, n, p0=[np.mean(data),np.std(data)])  

	        mu, dmu = pars[0], np.sqrt(cov[0,0 ]) 
	        sigma, dsigma = pars[1], np.sqrt(cov[1,1 ])  
                print(sigma, dsigma)

            if plot:
              if do_fit:
                  if coherent:
	              ax.plot(fit_points, gauss(fit_points,*pars), 'k-',linewidth = 1, label='$\mu=${:.1f}$\pm${:.1f}, $\sigma=${:.1f}$\pm${:.1f}'.format(mu,dmu,sigma,dsigma))   
	              ax.plot(centers, gauss(centers,*pars), 'r.',linewidth = 2)        
                  else:
	              ax.plot(fit_points, stats.norm.pdf(fit_points,*pars), 'k-',linewidth = 1, label='$\mu=${:.1f}$\pm${:.1f}, $\sigma=${:.1f}$\pm${:.1f}'.format(mu,dmu,sigma,dsigma))   
	              ax.plot(centers, stats.norm.pdf(centers,*pars), 'r.',linewidth = 2)        

              ax.legend()
              ax.set_xlabel("Sample Value [ADC Counts]")
              ax.set_ylabel("Normalized Frequency")
              ax.set_title(title + "(N = {N})".format(N = len(data)))
              if coherent: ax.set_xlabel("$\Sigma_{Ch} (S_{i} - \\bar{S})$ [ADC Counts]",horizontalalignment='right', x=1.0)
              if coherent: ax.set_ylabel("Events")
              if coherent: ax.set_title(title + " HG  (N = {N})".format(N = len(data))) 
              ax.xaxis.set_major_locator(MaxNLocator(integer=True))
              #ax.xaxis.set_tick_params(rotation=45)
              ax.set_ylim(0,y_max*(1 + .3))
              ax.grid(zorder = 0)
              #ax.set_xlim(42900,43100)
              if coherent: 
                  #ax.text(.6,.8,"$E[\sigma] = "  + str(round(coherent,3)) + "$",transform = ax.transAxes)
                  ax.text(.6,.8,"$E[\sigma] = {:.1f}\pm{:.1f} $".format(coherent[0],coherent[1]),transform = ax.transAxes)

                  #ax.text(.6,.8,"$E[\sigma] = {:.1f}\pm{:.1f} $".format(coherent[0],coherent[1]),transform = ax.transAxes)

              print("Plotting Baseline hist for " + channel + " " + gain + " gain...")
              #plt.show()
              plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_hist.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))

            plt.cla()
            plt.clf()
            plt.close()
            if do_fit:
                return mu, sigma, dsigma

    def AnalyzeBaseline(self,plot_dir, runName, meas_to_plot = None, gains_to_plot = None, chans_to_plot = None):

        print("Analyzing baseline....\n")

        if not meas_to_plot:  meas_to_plot = range(self.nMeas)
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

                print(meas,str(gain),str(channel))
                pedestal = self.Samples[meas,i,self.ChanDict[channel],:]

                mu, sigma, dsig = self.makeFittedHist(pedestal,plot_dir,"Baseline value, Ped Run",channel,gain)
		print(mu)
                if str(channel) in mdacChannels and str(gain) == 'hi': mdac_hi.append((channel[-2:],mu,sigma))
		elif str(channel) in mdacChannels and str(gain) == 'lo': mdac_lo.append((channel[-2:],mu,sigma))
 
	tit = ['Hi', 'Lo']
	
	for title,vals in zip(tit,[mdac_hi, mdac_lo]):
	  dataUnpack = [list(t) for t in zip(*vals)]
	  if title == "Lo":
	    dataUnpack[0].pop(-1)
	    dataUnpack[1].pop(-1)
	    dataUnpack[2].pop(-1)
	  muData = [dataUnpack[0], dataUnpack[1]]
	  sigData = [dataUnpack[0], dataUnpack[2]]

          self.PlotSigmaMuSummary(muData, "Means MDAC "+title+ " Gain Run"+runName, plot_dir+"/mdac_"+title+"_mu_run"+runName+".png")
          self.PlotSigmaMuSummary(sigData, "Sigma MDAC "+title+" Gain Run"+runName, plot_dir+"/mdac_"+title+"_sig_run"+runName+".png")
	
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

    
    def PlotCoherent2D(self,plot_dir,chs):# ch1 = None,ch2 = None):

        if not (chs): 
            print("Please specify 2 channels to see a coherent noise plot")
            return

        chs_l = [50,51,54,55,58,59,62,63]
        chs_r = [66,67,70,71,74,75,78,79]

        chs = [("channel0" + str(no)) for no in chs_l + chs_r]
        #chs = [("channel0" + str(no)) for no in chs_r]
        #chs = self.Channels
        print("self channels: ",self.Channels)        

        meas_to_plot = range(self.nMeas)
        for meas in meas_to_plot:
            for i,gain in enumerate(self.Gains):
            #for i,gain in enumerate(["lo"]):

                ped_tot_left = np.zeros(np.shape(self.Samples)[-1])
                ped_tot_right = np.zeros(np.shape(self.Samples)[-1])
                for channel in chs:

                    print("ANALYZING CHANNEL: ",channel) 

                    ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    print(gain,self.GainDict)
                    
                    if int(channel.strip("channel")) < 64: ped_tot_left += ped_i
                    else: ped_tot_right += ped_i

        fig,ax = plt.subplots()

        mult = 10

        xbins = np.linspace(min(ped_tot_left) - .5, max(ped_tot_left) - .5,int( (max(ped_tot_left) - min(ped_tot_left) + 1)/mult) )
        ybins = np.linspace(min(ped_tot_right) - .5, max(ped_tot_right) - .5,int( (max(ped_tot_right) - min(ped_tot_right) + 1)/mult) )
        histo,_,_,image = ax.hist2d(ped_tot_left,ped_tot_right,cmap = "Blues",bins = [xbins,ybins])

        ax.set_xlabel("Left  Side (ch 48-63) [cts.]")
        ax.set_ylabel("Right Side (ch 64-79) [cts.]")
        plt.colorbar(image,cmap = "Blues",ax = ax)
        ax.set_title("Coherent noise by Sliceboard side")
        plt.show()


    def PlotPairwiseCorr(self,plot_dir):

        meas_to_plot = range(self.nMeas)

        chs_a = [ ch for ch in self.Channels if int(ch.strip("channel")) < 64]
        chs_b = [ ch for ch in self.Channels if int(ch.strip("channel")) < 64]

        for meas in meas_to_plot:
         for i,a in enumerate(chs_a):
          for j,b in enumerate(chs_b):

              for k,gain in enumerate(["hi"]):


                 ped_a = self.Samples[meas,self.GainDict[gain],self.ChanDict[a],:]
                 ped_b = self.Samples[meas,self.GainDict[gain],self.ChanDict[b],:]

                 r = ()*()/np.sqrt()

  
    def PlotCoherentNoise(self,plot_dir,chs):# ch1 = None,ch2 = None):

        if not (chs): 
            print("Please specify 2 channels to see a coherent noise plot")
            return

        print("self channels: ",self.Channels)
        #chs = self.Channels
  
        chs_l = [50,51,54,55,58,59,62,63]
        chs_r = [66,67,70,71,74,75,78,79]

        #chs = [("channel0" + str(no)) for no in chs_l + chs_r]
        chs = [("channel0" + str(no)) for no in chs_r]

        #chs = chs[:16]

        print("channels: ",chs)

        #chs = chs[1:3] 

        meas_to_plot = range(self.nMeas)
        for i,gain in enumerate(["lo", "hi"]):
            for meas in meas_to_plot:
            #for i,gain in enumerate(self.Gains):

                if gain == "lo": chs.remove("channel079")
                ped_tot = np.zeros(np.shape(self.Samples)[-1])
                sig_2_tot = 0
                dsig_2_tot = 0
                for channel in chs:

                    #if int(channel.strip("channel")) < 64: continue
                    print("ANALYZING CHANNEL: ",channel) 

                    #ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    ped_i -= np.mean(ped_i)

                    mu_i,sig_i,dsig_i = self.makeFittedHist(ped_i,plot_dir,"",channel, gain, coherent = 1, plot = False)
                    print(mu_i, sig_i, dsig_i)
                     
                    sig_2_tot += sig_i**2
                    dsig_2_tot += (sig_i**2)*(dsig_i**2)
                    ped_tot += ped_i
                #ped_1 = self.Samples[meas,i,self.ChanDict[ch1],:]                
                #ped_2 = self.Samples[meas,i,self.ChanDict[ch2],:]

                #sig1 = self.makeFittedHist(ped_1,plot_dir,"",ch1, gain, plot = False)
                #sig2 = self.makeFittedHist(ped_2,plot_dir,"",ch2, gain, plot = False)
                #print("s1**2 + s2**2 = ",np.sqrt(sig1**2 + sig2**2))

                #joint_pedestal = ped_1 + ped_2               
                print(dsig_2_tot)
                print(sig_2_tot)
                dsig_2_tot/=sig_2_tot
                print(dsig_2_tot)

                self.makeFittedHist(ped_tot,plot_dir,"Coherent Noise ","coherence_all",gain, coherent = [np.sqrt(sig_2_tot),np.sqrt(dsig_2_tot)])



def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/Processed/" + runName + "/"
    plot_dir = "../data/Processed/" + runName + "/Plots"
    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

    PedData = AnalyzePed(input_dir + "Pedestal_Data_Normal.hdf5",runName)

    PedData.getChannelsAndGains()

    print("Gains: ",PedData.Gains)
    print("Channels: ",PedData.Channels)

    PedData.getSamples() 
    PedData.getDimensions()
    print(PedData)
    #### IF YOU WANT TO SET SPECIFIC CHANNELS/GAINS TO ANALYZE #####
    ##### you can do it here

    #PedData.Channels = ["channel030","channel031"]
    #PedData.Gains = ["lo"]
    print(PedData.ChanDict)
    #PedData.PlotRaw(plot_dir)
    #PedData.AnalyzeBaseline(plot_dir, runName)
    #PedData.PlotCoherentNoise(plot_dir, ch1 = "channel018",ch2 = "channel019")
    PedData.PlotCoherentNoise(plot_dir, chs = ["channel014","channel015","channel018","channel019","channel030","channel031"])
    PedData.PlotCoherent2D(plot_dir, chs = ["channel014","channel015","channel018","channel019","channel030","channel031"])
    ##PedData.PlotPairwiseCorr(plot_dir)

    '''
    PedData.Channels = ["channel031"]
    peddata.gains = ["hi"]

    PedData.PlotRaw(plot_dir)
    PedData.AnalyzeBaseline(plot_dir)
    '''

if __name__ == "__main__":

    main()



