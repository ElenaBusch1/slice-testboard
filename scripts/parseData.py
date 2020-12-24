import numpy as np
from math import *
import matplotlib.pyplot as plt
import sys
import struct
import h5py

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
def parseData(fileName):

  #fileName = "/home/kirbybri/SCRATCH/2020_ATLAS_sliceTestboard/sliceAnalysis/alldata-1.dat" 
  #fileName = "/scratch/kchen/alldata-1.dat" 
  struct_fmt = ">2H"
  struct_len = struct.calcsize(struct_fmt)
  struct_unpack = struct.Struct(struct_fmt).unpack_from
  
  #get binary data using struct
  allData = []
  readCount = 0
  maxNumReads = 10000000
  with open(fileName, mode='rb') as fp:
    #fileContent = fp.read()
    while True :
      data = fp.read(struct_len)
      if not data: break
      s = struct_unpack(data)
      allData.append(s)
      readCount = readCount + 1
      if readCount > maxNumReads:
        break
  
  #each element in the list is 4 bytes ie 32 bits
  #detect Jack's 0xdeadbeef words, organize according to that
  allPackets = []
  tempPacket = []
  foundBeef = False
  for num,line in enumerate(allData) :
    #print('Num: ', num, ', line: ', line)
    if len(line) != 2 :
      print("WEIRD ERROR")
      return None
    if (line[0] == 0xdead ) and (line[1] == 0xbeef) :
      allPackets.append( tempPacket.copy()  )
      tempPacket.clear()
      #foundBeef = True
    #if foundBeef :
    tempPacket.append(line)
    #print(num, "0x "+"".join('%02x ' % c for c in line) ,"\t",len(tempPacket))

  #first packet is always wrong
  allPackets.pop(0)
  allPackets.pop()

  chanData = [[],[],[],[],[],[],[],[]]
  reqPacketLength = 168
  for num,packet in enumerate(allPackets) :
    #print('NEW packet: ', packet)
    #if num>20:
    #  break
    if len(packet) != reqPacketLength :
      print("WEIRD ERROR")
      return None
    #print( len(packet) )
    #for num, line in enumerate(packet) :
    #  print(num,"\t","0x "+"".join('%02x ' % c for c in line) )
    cu1frame = packet[132][1]
    cu1ch1 = packet[132][0]
    cu1ch2 = packet[131][1]
    cu1ch3 = packet[131][0]
    cu1ch4 = packet[130][1]
    cu1ch5 = packet[130][0]
    cu1ch6 = packet[129][1]
    cu1ch7 = packet[129][0]
    cu1ch8 = packet[128][1]
    
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
    chanData[0].append((cu1ch1, cu2ch1, cu1ch1+cu2ch1))
    chanData[1].append((cu1ch2, cu2ch2, cu1ch2+cu2ch2))
    chanData[2].append((cu1ch3, cu2ch3, cu1ch3+cu2ch3))
    chanData[3].append((cu1ch4, cu2ch4, cu1ch4+cu2ch4))
    chanData[4].append((cu1ch5, cu2ch5, cu1ch5+cu2ch5))
    chanData[5].append((cu1ch6, cu2ch6, cu1ch6+cu2ch6))
    chanData[6].append((cu1ch7, cu2ch7, cu1ch7+cu2ch7))
    chanData[7].append((cu1ch8, cu2ch8, cu1ch8+cu2ch8))

    
    #print( hex(frame) )
    if num % 500 == 0:
        print("Packet #: ",num,"frame",hex(cu1frame),"ch1",hex(cu1ch1),"ch2",hex(cu1ch2),"ch3",hex(cu1ch3),"ch4",hex(cu1ch4),"ch5",hex(cu1ch5),"ch6",hex(cu1ch6),"ch7", hex(cu1ch7),"ch8",hex(cu1ch8))
        print("frame1",hex(cu2frame1),"ch1",hex(cu2ch1),"ch2",hex(cu2ch2),"ch3",hex(cu2ch3),"ch4",hex(cu2ch4),"ch5",hex(cu2ch5),"ch6",hex(cu2ch6),"ch7", hex(cu2ch7),"ch8",hex(cu2ch8), "frame2", hex(cu2frame2))
    #print( hex(ch8) )
  #print(len(chanData))
  return chanData

#-------------------------------------------------------------------------
def makeHistograms(chanData):
  saveDir = "plots/"

  #----  All chans
  makeAllChans(chanData,saveDir)

  #----  Cross-channel coherence
  makeCrossChans(chanData,saveDir)
    

#-------------------------------------------------------------------------
def main():
  if len(sys.argv) != 2 :
    print("ERROR, program requires filename argument")
    return
  fileName = sys.argv[1]
  chanData = parseData(fileName)
  print("Number of samples",len(chanData))
  #makeHistograms(chanData)
  writeToHDF5(chanData,fileName)
  return None
  
if __name__ == "__main__":
  main()
