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
import math
from scipy.signal import lfilter

def gauss(x, b, c, a):
    return a * np.exp(-(x - b)**2.0 / (2 * c**2))

def acf(x, length=30):
    return np.array([1]+[np.corrcoef(x[:-i], x[i:])[0,1]  \
        for i in range(1, length)])

def interlace(samples,pulse_length,n_phases):#, bits):

  block_length = len(samples)

  print("BLOCK LENGTH: ",block_length)
  print("PULSE LENGTH: ",pulse_length)
  new_samples = np.empty(block_length)
  #new_bits = np.empty(shape = (block_length,32))
  #new_bits = np.empty(block_length)
  for s in range(block_length-1):
      new_samples[s] = samples[(s*pulse_length)%(pulse_length*n_phases -1)] 
  return new_samples#, new_bits



def gen_physics_pulse(amp = 1,shift = 0):

        ##Generates a physics pulse. data1 is the raw pulse, data2 is the filtered/shaped pulse

        ext_freq = 1200e6  # arbitrary waveform generator frequency
        sim = float(1 / ext_freq)  # simulation time resolution
        rise = 2.4e-9  # rise time
        width = 330e-9  # width of pulse
        period = float(160000e-9 - 1 * sim)  # total length of signal
        #amp = 1  # amplitude of signal
        delay = 10*sim # 0e-9
        tau = 21.5e-9  # RC time constant
        time1 = np.linspace(0, period, math.floor(period / sim))  # time array
        pulse = np.zeros(len(time1))

        # Form signal wave
        i = 0
        for t in time1:
            if t < rise + delay and t > delay:
                pulse[i] = amp * (t - delay) / rise  # rising ramp
            elif t < width + delay and t > delay:
                pulse[i] = amp * (width - t + delay) / (width - rise)  # falling ramp
            else:
                pulse[i] = 0  # zeros elsewhere
            i += 1
        # print(pulse[0:10])
        # Filtering parameters
        ## lfilter is a rational transfer function filter described here:
        ##      https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.lfilter.html
        d = 2 * tau / sim  # bilinear transform from laplace to z
        c = d / ((1 + d) ** 3)
        f = (1 - d) / (1 + d)
        b_old = [1, 1, -1, -1]
        b = [c * j for j in b_old]  # transfer function numerator
        a = [1, 3 * f, 3 * f ** 2, f ** 3]  # transfer function denominator

        filtered_pulse = lfilter(b, a, pulse)


        data1 = 1*filtered_pulse
        data2 = 1*pulse

        return np.roll(data1, -np.argmax(data1) + shift)


def calc_of_coeffs(ac, g, amp, dg=None, verbose = 0):

    if verbose:
       print("AC",ac,type(ac))
       print("G,",g,type(g))
       print("AMP",amp,type(amp))
    g = np.ravel(g)
    dg = np.ravel(dg) if dg is not None else np.gradient(g)
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


    def TriggerAndInterleave(self,plot_dir,gain,channel):


       fig,ax = plt.subplots()
       for j in range(1):

               raw_data = self.Samples[0,self.GainDict[gain],self.ChanDict[channel],:].astype(int)        
               SAMPLES_PER_PULSE = 501
               MAX_ALIGN_INDEX = 200
               N_PULSES = 30


               #raw_data = raw_data[220000:270000]  #chop off start
               baseline = np.mean(raw_data[:500])

               raw_data = raw_data -  baseline

               #plt.plot(raw_data,'b.')
               #plt.show()

               for i,sample in enumerate(raw_data):

                   if sample > 50:

                      print("FIRST PULSE CANDIDATE: ",sample)
                      #plt.plot(i,sample,'ro')
                      START_SAMPLE_INDEX = i 
                      break

               #plt.show()
               #plt.cla()
               #plt.clf()
               #plt.close()

               raw_data = raw_data[j*SAMPLES_PER_PULSE*N_PULSES +  START_SAMPLE_INDEX - 100:(START_SAMPLE_INDEX - 100) + (j +1)*SAMPLES_PER_PULSE*N_PULSES]

               pulses = raw_data.reshape(N_PULSES,SAMPLES_PER_PULSE)



               interleaved = interlace(raw_data,pulse_length,n_phases)#, bits):

               #interleaved = np.rot90(pulses)

               #interleaved = interleaved[::-1,:]

               print("INTERLEAVED: ",interleaved, np.shape(interleaved))

               #ax.plot(np.arange(len(interleaved.flatten())),interleaved.flatten(),'.',label = "pulse set " + str(j))
               ax.plot(np.arange(len(interleaved)) ,interleaved,'.',label = "pulse set " + str(j))
               plt.show()
               if j == 0:

                   av_interleaved = np.zeros((5,len(interleaved.flatten())))

               av_interleaved[j,:] = interleaved.flatten()


       ax.grid()
       #ax.plot(np.arange(len(interleaved.flatten())) + 30*j,np.mean(av_interleaved,axis =-1),'.',label = "pulse set " + str(j))
       ax.legend()
       ax.set_xlabel("time [ns]")
       ax.set_ylabel("Pulse Height [ADC Counts]")
       ax.set_title("Interleaved Pulse (30 phases, 1200MHz spacing) Run 0526; (N = " + str(len(interleaved)) + ")")
       #ax.set_xlim(0,12500)

       plt.show()


    def TriggerAndChop(self,plot_dir,gain,channel):
 
       raw_data = self.Samples[0,self.GainDict[gain],self.ChanDict[channel],:].astype(int)        

       SAMPLES_PER_PULSE = 6400
       MAX_ALIGN_INDEX = 200

       baseline = np.mean(raw_data[:3000])


       raw_data = raw_data[3000:] - baseline #chop off beginning of first pulse to center pulses

       plt.plot(raw_data,'b.')
       plt.grid()
       plt.show()
       plt.cla()
       plt.clf()
       plt.close()

       n_pulses = int(len(raw_data)/SAMPLES_PER_PULSE)
       print(n_pulses)

       raw_data = raw_data[:n_pulses*SAMPLES_PER_PULSE] #chop off stragglers

       pulses = raw_data.reshape(n_pulses,SAMPLES_PER_PULSE)


       maxima = np.amax(pulses,axis = 1)

       pulses = pulses[maxima >  50,:]


       maxima = maxima[maxima >  50]
       maxima_indices = np.argmax(pulses,axis = 1)

       
       for i,index in enumerate(maxima_indices): pulses[i,:] = np.roll(pulses[i,:], - index +  MAX_ALIGN_INDEX)# align peaks
       print(np.shape(pulses))
       #plt.hist(maxima - baseline)
       #n, bins = self.makeFittedHist(pulses[:,1000:6000].flatten() ,plot_dir, "Pulse Presample noise, ch 79 LG (Run 496)", channel, gain)

        
       filtered_pulse = gen_physics_pulse( shift = MAX_ALIGN_INDEX*25) 
       filtered_pulse = filtered_pulse[:len(pulses[0])]       

       plt.plot(np.arange(len(filtered_pulse))*25,pulses[1,:],'.',label = "aligned pulse samples")
       for i in range(10):

           plt.plot(np.arange(len(filtered_pulse))*25,pulses[i*23,:],'.')
       plt.plot(filtered_pulse*np.mean(maxima)/(max(filtered_pulse)),'b--',label = "physics pulse")
       plt.xlim(4400,6000)
       plt.legend()
       plt.show()
       

       n, bins = self.makeFittedHist(maxima ,plot_dir, "Peak Heights", channel, gain)
 
       mode_pulses =  pulses[ (maxima).astype(int)  == int(bins[np.argmax(n) ] ),:] #take most common pulse 'phase' to calculate OFCs 
 
       print(np.shape(mode_pulses) )

       acCoeffs = acf(mode_pulses[0,1000:])[:5] #first 5 autocorrelation coeffs

       g = np.mean(mode_pulses[:, MAX_ALIGN_INDEX - 2: MAX_ALIGN_INDEX + 3], axis = 0)

       plt.plot(g,'.')
       plt.show()

       print("g: ",g)
       print("dg: ",np.gradient(g) )
       print("AC Coeffs: ",acCoeffs)

       a, b = calc_of_coeffs(acCoeffs, g, np.max(g), np.gradient(g),verbose = 1)
       print("OFCs: ")
       print(a,b)

       '''
       for k in range(len(pulses)):
          tmp_energy = 0
          tmp_time = 0
          tmp_time_offset = 0
          for s in range(n_samples):
            tmp_energy += blocks[b][start_sample+phase+n_phases*s]*ofcs_a[s]
            tmp_time += blocks[b][start_sample+phase+n_phases*s]*ofcs_b[s]
            tmp_time_offset += blocks[b][start_sample+phase+1+n_phases*s]*ofcs_b[s]


       for pulse in pulses:

           pulse_energy = sum(pulse[MAX_ALIGN_INDEX - 2: MAX_ALIGN_INDEX + 3]*a)
           pulse_time = sum(pulse[MAX_ALIGN_INDEX - 2: MAX_ALIGN_INDEX + 3]*b)

           print("Pulse Energy:", pulse_energy) 
           print("Pulse Time:", pulse_time) 
       '''


       pulse_energies = np.sum(pulses[:,MAX_ALIGN_INDEX - 2: MAX_ALIGN_INDEX + 3]*a,axis = 1)

       print(pulse_energies)

       n, bins = self.makeFittedHist(pulse_energies ,plot_dir, "OFC Energies", channel, gain)
       '''
       a = np.zeros( (5,len(g)) )
       b = np.zeros( (5,len(g)) )

       for i,sample in enumerate(g):

           a[:,i], b[:,i] = calc_of_coeffs(acCoeffs, sample, np.gradient(sample),verbose = 1)

           print("OFCs: ")
           print(a[:,i],b[:,i])
           print()
       '''
       

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
              plt.show()
              #plt.savefig(r'{plot_dir}/{channel}_{gain}_pedestal_hist.png'.format(plot_dir = plot_dir,channel = channel,gain = gain))
              print(("Figure saved as: ",'{plot_dir}/{channel}_{gain}_pedestal_hist.png'.format(plot_dir = plot_dir,channel = channel,gain = gain)))

            plt.cla()
            plt.clf()
            plt.close()
            #if do_fit:
            #return  mu, sigma, dsigma, np.std(data)
            return n, bins


def main():

    if len(sys.argv) != 2 :
        print("ERROR, program requires filename argument")
        return 

    runName = sys.argv[1]
    input_dir = "../data/Processed/" + runName + "/"
    plot_dir = "../data/Processed/" + runName + "/Plots"
    if not (os.path.exists(plot_dir)): os.mkdir(plot_dir)

    PulseData = AnalyzePulse(input_dir + "Pedestal_Data_Normal.hdf5",runName)

    PulseData.getChannelsAndGains()

    print(("Gains: ",PulseData.Gains))
    print(("Channels: ",PulseData.Channels))

    PulseData.getSamples() 
    PulseData.getDimensions()
    #### IF YOU WANT TO SET SPECIFIC CHANNELS/GAINS TO ANALYZE #####
    ##### you can do it here

    PulseData.Channels = ["channel079"] #,"channel019","channel014","channel015","channel030","channel031"]
    PulseData.Gains = ["hi"]

    #PulseData.TriggerAndChop(plot_dir,PulseData.Gains[0],PulseData.Channels[0])
    PulseData.TriggerAndInterleave(plot_dir,PulseData.Gains[0],PulseData.Channels[0])

    #PulseData.PlotRaw(plot_dir)
    #print(PedData.ChanDict)
    #PedData.PlotRaw(plot_dir,chans_to_plot = ["channel079"])


if __name__ == "__main__":

    main()



