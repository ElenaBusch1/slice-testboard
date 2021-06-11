import numpy as np
from math import *
import matplotlib.pyplot as plt
import sys
import struct
import h5py
import argparse
import os
from datetime import datetime

#-------------------------------------------------------------------------
def convert_to_bin(num):
    binNum=str(int(bin(num)[2:]))
    while(len(str(binNum)) < 16):
      binNum = '0'+binNum
    returnArr = []
    for i in binNum:
      returnArr.append(int(i))
    return returnArr

#-------------------------------------------------------------------------
def convert_to_dec(binArray):
    decArray = []
    for num in binArray:
       dec = int(''.join([str(x) for x in num]),2)
       decArray.append(dec)
    return decArray

#-------------------------------------------------------------------------
def makeHistograms(chanData, runNumber):
  print('Making histograms... ')
  #plotDir = "Runs/Run_"+str(runNumber).zfill(4)+"/plots"
  #if not os.path.exists(plotDir):
  #  os.makedirs(plotDir)
  saveDir = "../Runs/plots/Run_"+str(runNumber).zfill(4)+"/"
  if not os.path.exists(saveDir):
    os.makedirs(saveDir)

  adc = 0
  for chan in range(len(chanData)): 
    if (chan) % 4 == 0: adc += 1
    for gain in range(len(chanData[chan])): #lo, hi 
      bin_data = chanData[chan][gain]
      if np.all(np.asarray(bin_data)==[]): continue #ignore fake data
      data = convert_to_dec(bin_data)
      if np.all(np.asarray(data)==0): continue #dont bother plotting
      fig, ax = plt.subplots()
      avg = np.mean(data)
      std = np.std(data)
      lbl = (
          r'$\mu$: {:.1f}'.format(avg) + '\n' +
          r'$\sigma$: {:.2f}'.format(std)
      )
      bins = int(np.divide(max(data)-min(data)+1,10))

      plt.hist(data)
      if gain == 0: plt.title("Channel "+str(chan)+", ADC "+str(adc)+", lo gain")
      else: plt.title("Channel "+str(chan)+", ADC "+str(adc)+", hi gain")
      plt.text(0.98,0.85, lbl, horizontalalignment='right', transform = ax.transAxes)
      plt.savefig(saveDir+"channel"+str(chan)+"_adc"+str(adc)+"_gain"+str(gain)+".pdf")
      print('Saved fig '+saveDir+"channel"+str(chan)+"_adc"+str(adc)+"_gain"+str(gain)+".pdf")
      plt.clf()
      plt.close()

#-------------------------------------------------------------------------
def makePlots(chanData):
  plt.plot(chanData[28][0][0:1000])
  plt.title("Sine, ADC 8 / Chan 28 Lo") 
  plt.savefig("0120_testsine_adc8_lo.pdf")
  plt.clf()
  plt.plot(chanData[28][1][0:1000])
  plt.title("Sine, ADC 8 / Chan 28 Hi") 
  plt.savefig("0120_testsine_adc8_hi.pdf")
  plt.clf()
  plt.close()


#-------------------------------------------------------------------------
def make_adc_dict():
  orig_ADC = 32
  orig_line = 8 #first 7 are header info
  #d_ADCs = np.zeros((32,2))
  d_ADCs = {}
  for y in range(32,0,-1):
    d_ADCs[y] = [orig_line, orig_line + 4]
    orig_line +=5 #each ADC data = 160 bits = 5 32-bit lines
  
  return d_ADCs

#-------------------------------------------------------------------------
def make_chanData_trigger(allPackets):

  print('Starting to make chanData...')

  reqPacketLength = 168
  d_ADCs = make_adc_dict()
  chanData = [] # 0, 128
  for z in range(128): chanData.append([[],[]])

  # each packet has 32 chans of readout 
  for num,packet in enumerate(allPackets) :
    #print('NEW packet: ', len(packet), packet)
    if len(packet) != reqPacketLength :
      print("WEIRD ERROR")
      return None

    #for num, line in enumerate(packet) :
    #  print(num,"\t","0x "+"".join('%02x ' % c for c in line), line )

    chanNum=127 #start at 128 and go in reverse order
    for adc in d_ADCs: # loop over all 32 adcs 
      cu1frame1 = packet[d_ADCs[adc][0]+4][1] # bits 15:0
      if int(cu1frame1) == int(0xfa1): # fake data 
        cu_ch3_lo = []
        cu_ch3_hi = []
        cu_ch2_hi = []
        cu_ch2_lo = []
        cu_ch1_lo = []
        cu_ch1_hi = []
        cu_ch0_hi = []
        cu_ch0_lo = []
      else: 
        cu_ch3_lo = packet[d_ADCs[adc][0]+4][0] # bits 31:16 = ADC ch1
        cu_ch3_hi = packet[d_ADCs[adc][0]+3][1] # ADC ch2  
        cu_ch2_hi = packet[d_ADCs[adc][0]+3][0] # ADC ch3
        cu_ch2_lo = packet[d_ADCs[adc][0]+2][1] 
        cu_ch1_lo = packet[d_ADCs[adc][0]+2][0] 
        cu_ch1_hi = packet[d_ADCs[adc][0]+1][1] 
        cu_ch0_hi = packet[d_ADCs[adc][0]+1][0] 
        cu_ch0_lo = packet[d_ADCs[adc][0]][1] # ADC ch8
      cu1frame8 = packet[d_ADCs[adc][0]][0] # frame
      #if int(cu1frame8) == int(0xfa8): continue # will never get to here
      corr_chanNum = (chanNum+48)%128
      # add to master channel dataset 
      chanData[corr_chanNum][0].append(cu_ch0_lo) #index 0 is low gain, index 1 is high gain
      chanData[corr_chanNum][1].append(cu_ch0_hi) 
      chanData[corr_chanNum-1][0].append(cu_ch1_lo)
      chanData[corr_chanNum-1][1].append(cu_ch1_hi)
      chanData[corr_chanNum-2][0].append(cu_ch2_lo)
      chanData[corr_chanNum-2][1].append(cu_ch2_hi)
      chanData[corr_chanNum-3][0].append(cu_ch3_lo)
      chanData[corr_chanNum-3][1].append(cu_ch3_hi)
      chanNum -= 4

  return chanData


#-------------------------------------------------------------------------
def make_chanData_singleADC(allPackets,adc):

  adcNum = int(adc[6:])
  chanNum = adcNum*4-1
  chanData = [] # 0, 128
  for z in range(128): chanData.append([[],[]])
  reqPacketLength = 16
  prevCounter = 0
  prevNum = 0
  for num,packet in enumerate(allPackets) :
    #print("NEW PACKET")
    #print( len(packet) )
    #for num, line in enumerate(packet) :
    #  print(num,"\t","0x "+"".join('%02x ' % c for c in line) )

    if len(packet) != reqPacketLength :
      print("WEIRD ERROR")
      return chanData
    #check if last 256 bits have correct header
    if ( (int( packet[8][0] ) & 0xFF00) != 0x6a00 ) :
      print("WEIRD ERROR")
      return chanData

    #something else...
    #chData = [ packet[4][1], packet[4][0], packet[3][1], packet[3][0], packet[2][1], packet[2][0], packet[1][1], packet[1][0] ]
    #chanData.append( chData )
    #chData = [ packet[9][1], packet[9][0], packet[8][1], packet[8][0], packet[7][1], packet[7][0], packet[6][1], packet[6][0] ]
    #chanData.append( chData )
    #chData = [ packet[15][0], packet[14][1], packet[14][0], packet[13][1], packet[13][0], packet[12][1], packet[12][0], packet[11][1] ]
    #chanData.append( chData )
    
    #samples only 
    #chanData.append( (packet[1][1] , packet[1][0]) )
    #chanData.append( (packet[6][1] , packet[6][0]) )
    #chanData.append( (packet[12][0], packet[11][1]) )
    #chanData.append( packet[1][0] )
    #chanData.append( packet[6][0] )
    #chanData.append( packet[11][1] ) 

    counter = int(packet[0][1]) & 0xFF
    """
    # 3 samples for this ADC in each packet
    cu_ch3_lo = [convert_to_bin(packet[4][1]), convert_to_bin(packet[10][0]), convert_to_bin(packet[15][0])] # bits 31:16 = ADC ch1
    cu_ch3_hi = [convert_to_bin(packet[4][0]), convert_to_bin(packet[9][1]), convert_to_bin(packet[14][1])] # ADC ch2  
    cu_ch2_hi = [convert_to_bin(packet[3][1]), convert_to_bin(packet[9][0]), convert_to_bin(packet[14][0])] # ADC ch3
    cu_ch2_lo = [convert_to_bin(packet[3][0]), convert_to_bin(packet[8][1]), convert_to_bin(packet[13][1])] 
    cu_ch1_lo = [convert_to_bin(packet[2][1]), convert_to_bin(packet[7][1]), convert_to_bin(packet[13][0])] 
    cu_ch1_hi = [convert_to_bin(packet[2][0]), convert_to_bin(packet[7][0]), convert_to_bin(packet[12][1])] 
    cu_ch0_hi = [convert_to_bin(packet[1][1]), convert_to_bin(packet[6][1]), convert_to_bin(packet[12][0])] 
    cu_ch0_lo = [convert_to_bin(packet[1][0]), convert_to_bin(packet[6][0]), convert_to_bin(packet[11][1])] #ADC ch8
    """
    #save samples as 16-bits
    cu_ch3_lo = [packet[4][1], packet[10][0], packet[15][0]] # bits 31:16 = ADC ch1
    cu_ch3_hi = [packet[4][0], packet[9][1], packet[14][1]] # ADC ch2  
    cu_ch2_hi = [packet[3][1], packet[9][0], packet[14][0]] # ADC ch3
    cu_ch2_lo = [packet[3][0], packet[8][1], packet[13][1]] 
    cu_ch1_lo = [packet[2][1], packet[7][1], packet[13][0]] 
    cu_ch1_hi = [packet[2][0], packet[7][0], packet[12][1]] 
    cu_ch0_hi = [packet[1][1], packet[6][1], packet[12][0]] 
    cu_ch0_lo = [packet[1][0], packet[6][0], packet[11][1]]

    # add to master channel dataset 
    chanData[chanNum][0].append(  cu_ch0_lo) #index 0 is low gain, index 1 is high gain
    chanData[chanNum][1].append(  cu_ch0_hi) 
    chanData[chanNum-1][0].append(cu_ch1_lo)
    chanData[chanNum-1][1].append(cu_ch1_hi)
    chanData[chanNum-2][0].append(cu_ch2_lo)
    chanData[chanNum-2][1].append(cu_ch2_hi)
    chanData[chanNum-3][0].append(cu_ch3_lo)
    chanData[chanNum-3][1].append(cu_ch3_hi)

  for i in range(len(chanData)):
    for j in range(2):
      if len(chanData[i][j]) > 0: 
        #print(chanData[i][j])
        #print(np.concatenate(chanData[i][j],axis=0))
        chanData[i][j] = (np.concatenate(chanData[i][j],axis=0))

  print(np.shape(chanData))
  #end for loop
  return chanData

#-------------------------------------------------------------------------
def make_packets(allData,dataType):
  
  print('Making packets.....')
  #each element in the list is 4 bytes ie 32 bits
  #detect Jack's 0xdeadbeef words, organize according to that
  allPackets = []
  tempPacket = []
  for num,line in enumerate(allData) :
    #print('Num: ', num, ', line: ', line)
    #print('Num: ', num, ', 32 bit line: ', line)

    if len(line) != 2 :
      print("WEIRD ERROR")
      return None

    #trigger 
    if dataType == 'trigger':
      #when we find dead beef, add current packet to stack and start fresh
      if (line[0] == 0xdead ) and (line[1] == 0xbeef) :
        #print('this is dead beef: '+str(hex(line[0]))+' '+str(hex(line[1])))
        allPackets.append( tempPacket.copy()  )
        tempPacket.clear()
      tempPacket.append(line)
      #print(num, "0x "+"".join('%02x ' % c for c in line) ,"\t",len(tempPacket))

    #single ADC
    elif dataType == 'singleADC':
      if ( (int(line[0]) & 0xFF00) == 0x5900 ) :
        if num < len(allData) -8 :
          if ( (int(allData[num+8][0]) & 0xFF00) == 0x6a00 ) :
            allPackets.append( tempPacket.copy()  )
            #print([[hex(x) for x in tp] for tp in tempPacket])
            tempPacket.clear()
      tempPacket.append(line)
  #end for loop

  
  if dataType == 'singleADC':
    if len(allPackets) < 2: return []

  #first packet is always wrong
  allPackets.pop(0)
  allPackets.pop()
 
  return allPackets 

#-------------------------------------------------------------------------
def writeToHDF5(chanData,fileName,attributes,chan=28):

  out_file = h5py.File(fileName.replace('-1.dat','')+'.hdf5','a')
  print("Opening hdf5 file: "+ fileName.replace('-1.dat','')+'.hdf5')

  m = str(len(out_file.keys())).zfill(3)
  grp = out_file.create_group("Measurement_"+m)
  for attr in attributes:
    print(attr, attributes[attr])
    grp.attrs[attr] = attributes[attr]
  for c in range(len(chanData)): 
    if c < 10: cc = '00'+str(c)
    elif c >=10 and c< 100: cc = '0'+str(c)
    elif c >= 100: cc =str(c)

    out_file.create_group("Measurement_"+m+"/channel"+cc)
    out_file.create_group("Measurement_"+m+"/channel"+cc+"/hi")
    out_file.create_group("Measurement_"+m+"/channel"+cc+"/lo")
    out_file.create_dataset("Measurement_"+m+"/channel"+cc+"/lo/samples",data=chanData[c][0], chunks=True, compression="gzip", dtype='u2')
    out_file.create_dataset("Measurement_"+m+"/channel"+cc+"/hi/samples",data=chanData[c][1], chunks=True, compression="gzip", dtype='u2')
  #TODO setHDF5Attributes(out_file["Measurement_" + str(index)], **cut_attrs_dict)


  out_file.close()  

#-------------------------------------------------------------------------
def parseData(fileName,dataType,maxNumReads, attributes):

  struct_fmt = ">2H"
  struct_len = struct.calcsize(struct_fmt)
  struct_unpack = struct.Struct(struct_fmt).unpack_from
  
  adc = attributes['adc']

  #get binary data using struct
  allData = []
  readCount = 0
  print('Parsing binary file......')
  with open(fileName, mode='rb') as fp:
    #fileContent = fp.read()
    while True :
      data = fp.read(struct_len)
      if not data: break
      s = struct_unpack(data)
      if readCount % np.divide(maxNumReads,10) == 0: print(readCount)
      allData.append(s)
      readCount = readCount + 1
      if readCount > maxNumReads: break
  
  #--- parse data, make packets
  allPackets = make_packets(allData,dataType)

  # -- turn packets in chanData
  if dataType=='trigger': chanData = make_chanData_trigger(allPackets)
  elif dataType=='singleADC': chanData = make_chanData_singleADC(allPackets,adc)
  else: print("Unknown data type") 
  return chanData

    

#-------------------------------------------------------------------------
def main(GUI, fileName):
 
  dataType = GUI.daqMode
  maxNumReads = GUI.nSamples
  try:
      saveHists = GUI.saveHistogramsCheckBox.isChecked()
  except:
      saveHists = True
  runNumber = GUI.runNumber

  attributes = {}
  attributes['boardID'] = GUI.boardID
  attributes['att_val'] = GUI.att_val
  attributes['awg_amp'] = GUI.sineAmplitude
  attributes['awg_freq'] = GUI.awgFreq
  #attributes['measChan'] = GUI.measChan
  attributes['measStep'] = GUI.measStep
  attributes['measType'] = GUI.runType
  attributes['runNum'] = GUI.runNumber
  attributes['adc'] = GUI.singleADCMode_ADC
  attributes['timestamp'] = str(datetime.now())

  print('Parsing '+fileName+' of type '+dataType) 
  startTime = datetime.now()
  chanData = parseData(fileName,dataType,maxNumReads, attributes)
  print("Number of samples",len(chanData))
  #makePlots(chanData)
  if False and saveHists:
      makeHistograms(chanData, runNumber)
  writeToHDF5(chanData,fileName,attributes)
  print('runtime: ',datetime.now() - startTime)
  return None

