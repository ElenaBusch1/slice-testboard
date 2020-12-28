import numpy as np
from math import *
import matplotlib.pyplot as plt
import sys
import struct
import h5py
import argparse
from datetime import datetime


#-------------------------------------------------------------------------
def make_chanData_trigger(allPackets):

  chanData = [[],[],[],[],[],[],[],[]]
  reqPacketLength = 168
  for num,packet in enumerate(allPackets) :
    #print('NEW packet: ', len(packet), packet)
    #if num>20:
    #  break
    if len(packet) != reqPacketLength :
      print("WEIRD ERROR")
      return None
    #print( len(packet) )
    for num, line in enumerate(packet) :
      if num > 7: print(num,"\t","0x "+"".join('%02x ' % c for c in line) )

    # ADC 7 
    cu1frame1 = packet[132][1] # frame  
    cu1ch1 = packet[132][0] # lo 
    cu1ch2 = packet[131][1] # hi 
    cu1ch3 = packet[131][0] # hi 
    cu1ch4 = packet[130][1] # lo 
    cu1ch5 = packet[130][0] # lo 
    cu1ch6 = packet[129][1] # hi 
    cu1ch7 = packet[129][0] # hi 
    cu1ch8 = packet[128][1] # lo
    cu1frame2 = packet[128][0] # lo
  
    # ??? 
    cu2frame1 = packet[160][0]
    cu2ch1 = packet[159][1]
    cu2ch2 = packet[159][0]
    cu2ch3 = packet[158][1]
    cu2ch4 = packet[158][0]
    cu2ch5 = packet[157][1]
    cu2ch6 = packet[157][0]
    cu2ch7 = packet[156][1]
    cu2ch8 = packet[156][0]
    cu2frame2 = packet[155][1]

    #select channel to 
    chanData[0].append((cu1ch1, cu2ch1))
    chanData[1].append((cu1ch2, cu2ch2))
    chanData[2].append((cu1ch3, cu2ch3))
    chanData[3].append((cu1ch4, cu2ch4))
    chanData[4].append((cu1ch5, cu2ch5))
    chanData[5].append((cu1ch6, cu2ch6))
    chanData[6].append((cu1ch7, cu2ch7))
    chanData[7].append((cu1ch8, cu2ch8))

    #print( hex(frame) )
    if num % 500 == 0:
        print("Packet #: ",num,"frame",hex(cu1frame),"ch1",hex(cu1ch1),"ch2",hex(cu1ch2),"ch3",hex(cu1ch3),"ch4",hex(cu1ch4),"ch5",hex(cu1ch5),"ch6",hex(cu1ch6),"ch7", hex(cu1ch7),"ch8",hex(cu1ch8))
        print("frame1",hex(cu2frame1),"ch1",hex(cu2ch1),"ch2",hex(cu2ch2),"ch3",hex(cu2ch3),"ch4",hex(cu2ch4),"ch5",hex(cu2ch5),"ch6",hex(cu2ch6),"ch7", hex(cu2ch7),"ch8",hex(cu2ch8), "frame2", hex(cu2frame2))
    #print( hex(ch8) )

  return chanData


#-------------------------------------------------------------------------
def make_chanData_adc(allPackets):
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

    #print("\t",hex(packet[1][0]),"\t",int(packet[1][0]))
    #print("\t",hex(packet[6][0]),"\t",int(packet[6][0]))
    #print("\t",hex(packet[11][1]),"\t",int(packet[11][1]))
    counter = int(packet[0][1]) & 0xFF
    chData = [ packet[4][1], packet[4][0], packet[3][1], packet[3][0], packet[2][1], packet[2][0], packet[1][1], packet[1][0] ]
    chanData.append( chData )
    chData = [ packet[9][1], packet[9][0], packet[8][1], packet[8][0], packet[7][1], packet[7][0], packet[6][1], packet[6][0] ]
    chanData.append( chData )
    chData = [ packet[15][0], packet[14][1], packet[14][0], packet[13][1], packet[13][0], packet[12][1], packet[12][0], packet[11][1] ]
    chanData.append( chData )

    #chanData.append( (packet[1][1] , packet[1][0]) )
    #chanData.append( (packet[6][1] , packet[6][0]) )
    #chanData.append( (packet[12][0], packet[11][1]) )
  #end for loop
  return chanData

#-------------------------------------------------------------------------
def make_packets(allData):
  
  print('Making packets.....')
  #each element in the list is 4 bytes ie 32 bits
  #detect Jack's 0xdeadbeef words, organize according to that
  allPackets = []
  tempPacket = []
  for num,line in enumerate(allData) :
    #print('Num: ', num, ', 32 bit line: ', line)
    if len(line) != 2 :
      print("WEIRD ERROR")
      return None

    #when we find dead beef, add current packet to stack and start fresh
    if (line[0] == 0xdead ) and (line[1] == 0xbeef) :
      #print('this is dead beef: '+str(hex(line[0]))+' '+str(hex(line[1])))
      allPackets.append( tempPacket.copy()  )
      tempPacket.clear()
    tempPacket.append(line)
    #print(num, "0x "+"".join('%02x ' % c for c in line) ,"\t",len(tempPacket))

  #first packet is always wrong
  allPackets.pop(0)
  allPackets.pop()
 
  return allPackets 

#-------------------------------------------------------------------------
def writeToHDF5(chanData,fileName):

  out_file = h5py.File(fileName.replace('.dat','')+'.hdf5','a')
  print("Creating hdf5 file: "+ fileName.replace('.dat','')+'.hdf5')
  print(np.shape(chanData)) #8 channels, m measurements, 2 chips

  #for m in range(np.shape(chanData)[1]):
  #  out_file.create_group("Measurement_" + str(m))
  for c in range(np.shape(chanData)[2]-1): 
    out_file.create_group("coluta"+str(c+1))
    for h in range(np.shape(chanData)[0]): 
      out_file.create_group("coluta"+str(c+1)+"/channel"+str(h+1))
      out_file.create_dataset("coluta"+str(c+1)+"/channel"+str(h+1)+"/samples",data=list(zip(*chanData[h]))[c])
  #TODO setHDF5Attributes(out_file["Measurement_" + str(index)], **cut_attrs_dict)


  out_file.close()  

#-------------------------------------------------------------------------
def makeHistograms(chanData):
  saveDir = "plots/"

  #----  All chans
  makeAllChans(chanData,saveDir)
  #----  Cross-channel coherence
  makeCrossChans(chanData,saveDir)
#-------------------------------------------------------------------------
def makeAllChans(chanData,saveDir):
  counter = 0
  chipNames = ['Chip1', 'Chip2', 'Coherence']
  for chan in chanData:
    counter += 1
    #if counter != 7:
    #  continue
    chanSort = list(zip(*chan))
    for chip, chipName in zip(chanSort, chipNames):
      fig, ax = plt.subplots()
      avg = np.mean(chip)
      std = np.std(chip)
      lbl = (
          r'$\mu$: {:.1f}'.format(avg) + '\n' +
          r'$\sigma$: {:.2f}'.format(std)
      )
      #chip1+chip2
      if chipName == "Coherence":
        ex_std = np.sqrt(np.std(chanSort[0])**2 + np.std(chanSort[1])**2)
        lbl = (
          r'$\mu$: {:.1f}'.format(avg) + '\n' +
          r'$\sigma$: {:.2f}'.format(std) + '\n' +
          r'E[$\sigma$]: {:.2f}'.format(ex_std)
        )
      bins = max(chip)-min(chip)+1
      plt.hist(chip, bins = bins, range = (min(chip), max(chip)+1))
      plt.title(chipName + " Channel "+str(counter))
      plt.text(0.98,0.85, lbl, horizontalalignment='right', transform = ax.transAxes)
      #plt.show()
      plt.savefig(saveDir+"channel"+str(counter)+chipName+".png")
      print('Saved fig '+saveDir+"channel"+str(counter)+chipName+".png")
      plt.clf()
      plt.close()
#-------------------------------------------------------------------------
def makeCrossChans(chanData,saveDir):
  ch6 = list(zip(*chanData[5]))
  ch7 = list(zip(*chanData[6]))
  chip1ch67 = [x+y for (x,y) in zip(ch6[0],ch7[0])]
  chip2ch67 = [x+y for (x,y) in zip(ch6[1],ch7[1])]
  ch76 = [chip1ch67, chip2ch67]
  i = 0
  for chip in ch76:
    fig, ax = plt.subplots()
    avg = np.mean(chip)
    std = np.std(chip)
    ex_std = np.sqrt(np.std(ch6[i])**2 + np.std(ch7[i])**2)
    lbl = (
      r'$\mu$: {:.1f}'.format(avg) + '\n' +
      r'$\sigma$: {:.2f}'.format(std) + '\n' +
      r'E[$\sigma$]: {:.2f}'.format(ex_std)
    )
    i += 1
    bins = max(chip)-min(chip)+1
    plt.hist(chip, bins = bins, range = (min(chip), max(chip)+1))
    plt.title("Ch6-Ch7 Coherence, Chip "+str(i))
    plt.text(0.98,0.85, lbl, horizontalalignment='right', transform = ax.transAxes)
    #plt.show()
    plt.savefig(saveDir+"ch6ch7chip"+str(i)+".png")
    print('Saved fig '+saveDir+"ch6ch7chip"+str(i)+".png")
    plt.clf()
    plt.close()


#-------------------------------------------------------------------------
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
  allPackets = make_packets(allData)

  # -- turn packets in chanData
  if dataType=='trigger': chanData = make_chanData_trigger(allPackets)
  elif dataType=='singleADC': chanData = make_chanData_singleADC(allPackets)
    
  return chanData

    

#-------------------------------------------------------------------------
def main():

  # make ADC dictionary 
  orig_ADC = 31
  orig_line = 8
  #d_ADCs = np.zeros((32,2))
  d_ADCs = {}
  for y in range(31,-1,-1):
    d_ADCs[y] = [orig_line, orig_line + 4]
    orig_line +=5
  print(d_ADCs)


  parser = argparse.ArgumentParser()
  parser.add_argument("-f", "--file", default = '', type=str,
                     help="file to parse")
  parser.add_argument("-t", "--type", default = 0, type=str,
                     help="data taking type (trigger, singleADC, allADC)")
  parser.add_argument("-x", "--max", default = 10000000, type=int,
                     help="maxNumReads")
  args = parser.parse_args()
  
  fileName = args.file 
  dataType = args.type
  maxNumReads = args.max
  #fileName = sys.argv[1]

  print('Parsing '+fileName+' of type '+dataType) 
  startTime = datetime.now()
  #chanData = parseData(fileName,dataType,maxNumReads)
  #print("Number of samples",len(chanData))
  ##makeHistograms(chanData)
  #writeToHDF5(chanData,fileName)
  #print('runtime: ',datetime.now() - startTime)
  #return None
  
if __name__ == "__main__":
  main()
