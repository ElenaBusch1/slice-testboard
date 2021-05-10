import numpy as np
from math import *
import matplotlib.pyplot as plt
import sys
import struct
import h5py
import argparse
import os
from datetime import datetime


def makeCorrectData():
   correctData = {48: {0: 0xa5, 1: }}

def takeTriggerData(outputPath):
  """Runs takeTriggerData script"""

  subprocess.call("python takeTriggerData.py -o "+outputPath+" -t trigger -a 20", shell=True)
  time.sleep(5)

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
        cu_ch3_lo = convert_to_bin(packet[d_ADCs[adc][0]+4][0]) # bits 31:16 = ADC ch1
        cu_ch3_hi = convert_to_bin(packet[d_ADCs[adc][0]+3][1]) # ADC ch2  
        cu_ch2_hi = convert_to_bin(packet[d_ADCs[adc][0]+3][0]) # ADC ch3
        cu_ch2_lo = convert_to_bin(packet[d_ADCs[adc][0]+2][1]) 
        cu_ch1_lo = convert_to_bin(packet[d_ADCs[adc][0]+2][0]) 
        cu_ch1_hi = convert_to_bin(packet[d_ADCs[adc][0]+1][1]) 
        cu_ch0_hi = convert_to_bin(packet[d_ADCs[adc][0]+1][0]) 
        cu_ch0_lo = convert_to_bin(packet[d_ADCs[adc][0]][1]) # ADC ch8
      cu1frame8 = convert_to_bin(packet[d_ADCs[adc][0]][0]) # frame
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

def parseData(fileName,dataType,maxNumReads):

  struct_fmt = ">2H"
  struct_len = struct.calcsize(struct_fmt)
  struct_unpack = struct.Struct(struct_fmt).unpack_from
  
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
  chanData = make_chanData_trigger(allPackets)
  return chanData

def checkData(chanData, channels, goodMeas, badMeas, correctData):

  for chanNum in channels:
    for gain in [0,1]:
      for samp in chanData[chanNum][gain]:
        if chanData[chanNum][gain][samp] == correctData[chanNum][gain]:
          goodMeas[chanNum][gain] += 1
        else:
          badMeas[chanNum][gain].append(chanData[chanNum][gain][samp])

  return goodMead, badMeas

def runStabilityChecks():
    outputDirectory = 'stability'
    outputFile = "stabilityMeas.dat"
    stampedOutputFile = "stabilityMeas-1.dat"
    outputPath = outputDirectory+"/"+outputFile
    outputPathStamped = outputDirectory+"/"+stampedOutputFile

    channels = [i for i in range(48,80)]
    goodMeas = {chanNum: {gain: 0 for gain in [0,1]} for chanNum in channels}
    badMeas = {chanNum: {gain: [] for gain in [0,1]} for chanNum in channels}
    repeats = 2
    maxReads = 100000
    for i in range(repeats):
      takeTriggerData(outputPath)
      chanData = parseData(outputPathStamped,'trigger', maxReads) 
      goodMeas, badMeas = checkData(chanData, channels, goodMeas, badMeas)
      print("Channel 79 HG Good:", goodMeas[79][1])
      print("Channel 79 HG Bad:", len(badMeas[79][1])
      ## remove

if __name__ == "__main__":
  runStabilityChecks()

