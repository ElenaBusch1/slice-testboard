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
                    #print((meas, gain, channel))
                    raw_data =  np.array(f["Measurement_{meas}/{channel}/{gain}/samples".format(meas = meas,\
                                                                  channel = str(channel),\
                                                                  gain = gain)])

                    #print(np.shape(raw_data),np.shape(self.Samples))
                    self.Samples[meas,i,j,:] = raw_data 
                    self.ChanDict[channel] = j



        f.close()


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
              plt.show()      
              plt.cla()
              plt.clf()
              plt.close()
              #self.getFftWaveform(raw_data,plot_dir,channel,gain)

    def getFftWaveform(self,vals,plot_dir,channel,gain):
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
              if sampNum == -1 :
                continue
              else:
                psd_x.append( fftWf_x[sampNum] )
                psd.append( 20*np.log10(samp) )

            fig,ax = plt.subplots()
            ax.plot(psd_x,psd,'b-')
            ax.grid(True)
            ax.set_title(channel + " " + gain + "gain")
            ax.set_xlabel("Frequency [MHz]")
            ax.set_ylabel("PSD [dB]")
            ax.set_xlim(0,1)
            #plt.ylim(-50,0)
            print("\tPlotting FFT waveform....\n")
            plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_FFT.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))
            plt.cla()
            plt.clf()
            plt.close()
            #plt.show()
            #return fftWf_x,fftWf_y,psd_x,psd,sinad,enob,snr 

    def getFftWaveformOrooni(self,data,plot_dir,channel,gain):

            data = data[1:] #DROP FIRST SAMPLE TO GET 6251 SAMPLES!!!! critical
            fft_wf = np.fft.fft(data)
            fftWf_x = []
            fftWf_y = []
            psd = []
            psd_x = []
            for sampNum,samp in enumerate(fft_wf) :
              if sampNum > float( len(fft_wf) ) / 2. :
                 pass
                 #continue
              freqVal = 40.8 * sampNum/float(len(fft_wf))
              sampVal = np.abs(samp)
              if sampNum == 0 :
                sampVal = 0
              fftWf_x.append(freqVal)
              fftWf_y.append(sampVal)
              if np.max(fftWf_y) <= 0 :
                print(psd_x,psd)

            fourier_fftWf_y = fftWf_y/np.max(fftWf_y)
            for sampNum,samp in enumerate(fourier_fftWf_y) :
                psd_x.append( fftWf_x[sampNum] )
                psd.append( 20*np.log10(samp) )

            plt.plot(psd_x,psd,'b-')
            plt.grid()
            #plt.xlim(0,2)
            #plt.ylim(-100,0)
            plt.xlabel("Frequency [MHz]")
            plt.ylabel("PSD [dB]")
            print("\tPlotting FFT waveform....\n")
            #plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_FFT.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))
            plt.show()
            plt.close()
            plt.clf()


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
        print("Channels to plot: ",chans_to_plot)
        print("")
        print("Gains to plot: ",gains_to_plot)
        print("")
        #print("mdac channels: ",mdacChannels)

        mdac_hi = []
        mdac_lo = []
        dre_hi = []
        dre_lo = []
 
        for meas in meas_to_plot:
          for i,gain in enumerate(gains_to_plot):
            for j,channel in enumerate(chans_to_plot):

                #print((meas,str(gain),str(channel)))
                pedestal = self.Samples[meas,i,self.ChanDict[channel],:]
                mu, sigma, dsig, rms = self.makeFittedHist(pedestal,plot_dir,"Baseline value, Ped Run",channel,gain)
                print("Mean pedestal value: " +  str(mu) + "\n")
                #### USE STD FROM FIT #####
                #if str(channel) in mdacChannels and str(gain) == 'hi': mdac_hi.append((channel[-2:],mu,sigma))
                #elif str(channel) in mdacChannels and str(gain) == 'lo': mdac_lo.append((channel[-2:],mu,sigma))
                #elif not(str(channel) in mdacChannels) and str(gain) == 'hi': dre_hi.append((channel[-2:],mu,sigma))
                #elif not(str(channel) in mdacChannels) and str(gain) == 'lo': dre_lo.append((channel[-2:],mu,sigma))
                #### USE RMS #####
                if str(channel) in mdacChannels and str(gain) == 'lo': mdac_hi.append((channel[-2:],mu,rms))
                elif str(channel) in mdacChannels and str(gain) == 'lo': mdac_lo.append((channel[-2:],mu,rms))
                elif not(str(channel) in mdacChannels) and str(gain) == 'hi': dre_hi.append((channel[-2:],mu,rms))
                elif not(str(channel) in mdacChannels) and str(gain) == 'lo': dre_lo.append((channel[-2:],mu,rms))

        ''' 
        tit = ['Hi', 'Lo']
        
        for title,vals in zip(tit,[mdac_hi, mdac_lo]):
          print("HG MDAC: ",mdac_hi)
          dataUnpack = [list(t) for t in zip(*vals)]
          print("Data Unpack", dataUnpack)
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
          if len(dre_hi) == 0 or len(dre_lo) == 0: print("No dre channels to analyze"); break
          dataUnpack = [list(t) for t in zip(*vals)]
          if title == "Lo" and False:
            dataUnpack[0].pop(-1)
            dataUnpack[1].pop(-1)
            dataUnpack[2].pop(-1)
          muData = [dataUnpack[0], dataUnpack[1]]
          sigData = [dataUnpack[0], dataUnpack[2]]

          self.PlotSigmaMuSummary(muData, "Means DRE "+title+ " Gain Run"+runName, plot_dir+"/DRE-"+title+"_mu_run"+runName+".png")
          self.PlotSigmaMuSummary(sigData, "RMS DRE "+title+" Gain Run"+runName, plot_dir+"/DRE-"+title+"_sig_run"+runName+".png")
          '''

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

        #chs_l = [50,51,54,55,58,59,62,63]
        #chs_r = [66,67,70,71,74,75,78,79]
        chs_l = [12,13,14,15,16,17,18,1928,29,30,31]
        chs_r = []

        #chs = [("channel0" + str(no)) for no in chs_l + chs_r]
        #chs = [("channel0" + str(no)) for no in chs_r]
        #chs = self.Channels
        print(("self channels: ",self.Channels))        

        meas_to_plot = list(range(self.nMeas))
        for meas in meas_to_plot:
            for i,gain in enumerate(self.Gains):
            #for i,gain in enumerate(["lo"]):

                ped_tot_left = np.zeros(np.shape(self.Samples)[-1])
                ped_tot_right = np.zeros(np.shape(self.Samples)[-1])
                for channel in chs:

                    print(("ANALYZING CHANNEL: ",channel)) 

                    ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    print((gain,self.GainDict))
                    
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
        #plt.show()
 
    def PlotPairwiseCorr(self,plot_dir,gain_flg = "hi",
                         chs_l = [48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63],
                         chs_r = [64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79]):

        meas_to_plot = list(range(self.nMeas))

        print("chs L:",chs_l)
        print("chs R:",chs_r)

        hilo = False
        if gain_flg == 'hi' or gain_flg == 'lo': gain = gain_flg
        else:
          hilo = True
          gain = 'HiLo'

        if not hilo:
          channels = [("channel0" + str(no)) for no in chs_l + chs_r]
          data_by_ch = np.zeros((len(channels),len(self.Samples[0,self.GainDict[gain],self.ChanDict[channels[0]],:])))
        else:
          channelshi = [("channel0" + str(no)+'hi') for no in chs_l + chs_r] 
          channelslo = [("channel0" + str(no)+'lo') for no in chs_l + chs_r] 
          #channels = channelshi+channelslo
          channels = [val for pair in zip(channelshi, channelslo) for val in pair]
          data_by_ch = np.zeros((len(channels),len(self.Samples[0,self.GainDict['hi'],self.ChanDict[channels[0][:-2]],:])))
 
         
        for meas in meas_to_plot:
          for row,ch in enumerate(channels):

            if not hilo:
              data_by_ch[row,:] = self.Samples[meas,self.GainDict[gain],self.ChanDict[ch],:]
            else:
              if 'hi' in ch: ch_gain = 'hi'
              else: ch_gain = 'lo'
              ch_num = ch[:-2]
                
              data_by_ch[row,:] = self.Samples[meas,self.GainDict[ch_gain],self.ChanDict[ch_num],:]

          pearson = np.corrcoef(data_by_ch)


          fig, ax = plt.subplots(figsize = (30,30))
          im = ax.imshow(pearson, cmap = "RdBu",vmin = -.3,vmax = .3)

          plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
               rotation_mode="anchor")

          channels_relabeled = [ "channel" + str(int(x.strip("channel")[:-2]) + 48) + x[-2:]  for x in channels]

          print(channels,channels_relabeled)
          ax.set_xticks(np.arange(len(channels)))
          ax.set_yticks(np.arange(len(channels)))
          #ax.set_xticklabels(channels_relabeled)
          #ax.set_yticklabels(channels_relabeled)
          ax.set_xticklabels(channels)
          ax.set_yticklabels(channels)

          for i in range(len(channels)):
            for j in range(len(channels)):
                if i == j: color = "w"
                else: color = "k"
                text = ax.text(j, i, int(round(pearson[i, j],2)*100),
                               ha="center",fontsize = 10, va="center", color=color)

          for edge, spine in list(ax.spines.items()):
              spine.set_visible(False)

          ax.set_title("Run {name} MDAC + DRE Pairwise Noise Correlation [%], {gain} gain".format(name = self.runNo,gain = str(gain)))
          ax.set_xticks(np.arange(len(channels)+1)-.5, minor=True)
          ax.set_yticks(np.arange(len(channels)+1)-.5, minor=True)
          ax.grid(which = "minor", color="w", linestyle='-', linewidth=3)
          #fig.tight_layout()
          #plt.show()
          figure = plt.gcf()
          figure.set_size_inches(16, 12)

          plt.savefig(r'{plot_dir}/{gain}_corr.png'.format(plot_dir = plot_dir,gain = gain),dpi = 100)
          plt.close()
          plt.clf()


          return

 
    def PlotCoherentNoise(self,plot_dir,chs):# ch1 = None,ch2 = None):

        if not (chs): 
            print("Please specify 2 channels to see a coherent noise plot")
            return

        print(("========= MAKING COHERENT NOISE PLOT WITH CHANNELS: ",chs))
        print(("========= AVAILABLE CHANNELS IN THIS RUN: ",self.Channels))
        #chs = self.Channels
  
        Nchan = len(chs)

        meas_to_plot = list(range(self.nMeas))
        for i,gain in enumerate(["lo", "hi"]):
            for meas in meas_to_plot:
            #for i,gain in enumerate(self.Gains):

                #if gain == "lo": chs.remove("channel079")
                ped_tot = np.zeros(np.shape(self.Samples)[-1])
                sig_2_tot = 0
                dsig_2_tot = 0
                for channel in chs:

                    #if int(channel.strip("channel")) < 64: continue
                    print("  NOW ANALYZING: {channel}".format(channel = channel)) 

                    #ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    ped_i = self.Samples[meas,self.GainDict[gain],self.ChanDict[channel],:]
                    ped_i -= np.mean(ped_i)

                    mu_i,sig_i,dsig_i, _ = self.makeFittedHist(ped_i,plot_dir,"",channel, gain, coherent = 1, plot = False)
                    print("\tMu: {mu_i}; Sigma: {sig_i}; dSigma: {dsig_i}\n".format(mu_i = mu_i, sig_i = sig_i, dsig_i = dsig_i))
                     
                    sig_2_tot += sig_i**2
                    dsig_2_tot += (sig_i**2)*(dsig_i**2)
                    ped_tot += ped_i
                #ped_1 = self.Samples[meas,i,self.ChanDict[ch1],:]                
                #ped_2 = self.Samples[meas,i,self.ChanDict[ch2],:]

                #sig1 = self.makeFittedHist(ped_1,plot_dir,"",ch1, gain, plot = False)
                #sig2 = self.makeFittedHist(ped_2,plot_dir,"",ch2, gain, plot = False)
                #print("s1**2 + s2**2 = ",np.sqrt(sig1**2 + sig2**2))

                #joint_pedestal = ped_1 + ped_2               
                #print("\tMu: {mu_i}; Sigma: {sig_i}; dSigma: {dsig_i}".format(mu_i = mu_i, sig_i = sig_i, dsig_i = dsig_i)
                #print(sig_2_tot)
                dsig_2_tot/=sig_2_tot
                #print(dsig_2_tot)

                gain_str = "HG"
                if gain == "lo":gain_str = "LG"

                self.makeFittedHist(ped_tot,plot_dir,"Sum over {} {} channels".format(Nchan,gain_str),"coherence_all",gain, coherent = [np.sqrt(sig_2_tot),np.sqrt(dsig_2_tot)])



def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/Processed/" + runName + "/"
    plot_dir = "../data/Processed/" + runName + "/Plots"
    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

    PedData = AnalyzePed(input_dir + "Data_Normal.hdf5",runName)

    PedData.getChannelsAndGains()

    print(("Gains containing data in this run: ",PedData.Gains))
    print(("Channels containing data in this run: ",PedData.Channels))
    print("")

    PedData.getSamples() 
    PedData.getDimensions()

    #### IF YOU WANT TO SET SPECIFIC CHANNELS/GAINS TO ANALYZE #####
    ##### you can do it here:

    '''Example'''
    #PedData.Channels = ["channel018","channel019","channel014","channel015","channel030","channel031"]
    #PedData.Gains = ["lo"]


    #PedData.PlotRaw(plot_dir,chans_to_plot = ["channel079"]) #plot raw baseline samples, can specify channel or gain
     
    #PedData.AnalyzeBaseline(plot_dir, runName) #make fitted baseline histogram plot + summary mean/RMS plots
    PedData.AnalyzeBaseline(plot_dir, runName,chans_to_plot = ["channel050","channel051","channel078","channel079"] ) #example specifying certain channels to analyze
   
    chs_l = [50,51,54,55,58,59,62,63] #MDAC channels on left side of board 
    chs_r = [66,67,70,71,74,75,78,79] #MDAC channels on right side of board

    chs_to_plot = [("channel0" + str(no)) for no in chs_l + chs_r]
    #PedData.PlotCoherentNoise(plot_dir,chs = chs_to_plot) #make coherent noise histogram

    PedData.PlotPairwiseCorr(plot_dir, 'hilo', chs_l = chs_l, chs_r = chs_r) #plot pairwise noise correlation for hi and lo gain
    #PedData.PlotPairwiseCorr(plot_dir, 'hi',chs_l = chs_l,chs_r  = chs_r) #plot pairwise noise corelation for hi gain only
    #PedData.PlotPairwiseCorr(plot_dir, 'lo',chs_l = chs_l,chs_r = chs_r)


if __name__ == "__main__":

    main()



