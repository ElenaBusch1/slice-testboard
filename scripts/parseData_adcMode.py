import numpy as np
from math import *
import matplotlib.pyplot as plt
import sys
import struct

def parseData(fileName):

  #fileName = "/home/kirbybri/SCRATCH/2020_ATLAS_sliceTestboard/sliceAnalysis/alldata-1.dat" 
  struct_fmt = ">2H"
  struct_len = struct.calcsize(struct_fmt)
  struct_unpack = struct.Struct(struct_fmt).unpack_from
  
  #get binary data using struct
  allData = []
  chanData = []
  readCount = 0
  maxNumReads = 1000000
  #maxNumReads = 10000
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
  prevNum = 0
  for num,line in enumerate(allData) :
    if len(line) != 2 :
      print("WEIRD ERROR")
      return None
    #print( hex(line[0]),"\t",hex(line[1]) ,"\t", )
    #if ( (int(line[0]) & 0xFF00) == 0x5900 ) and ( int(line[1] == 0x0 ) ) :
    if ( (int(line[0]) & 0xFF00) == 0x5900 ) :
      if num < len(allData) -8 :
        if ( (int(allData[num+8][0]) & 0xFF00) == 0x6a00 ) :
          allPackets.append( tempPacket.copy()  )
          tempPacket.clear()
    tempPacket.append(line)
  #end for loop

  if len(allPackets) < 2:
    return []

  #first packet is always wrong
  allPackets.pop(0)
  #also drop last 
  allPackets.pop()
  
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

def main():
  if len(sys.argv) != 2 :
    print("ERROR, program requires filename argument")
    return
  fileName = sys.argv[1]
  chanData = parseData(fileName)
  print("Number of samples",len(chanData))
  
  with open('output_parseData.txt', 'w') as f:
    for line in chanData :
      varStr = ""
      for samp in line :
        varStr = varStr + str(int(samp)) + "\t"
      #f.write("%s\n" % samp)
      varStr = varStr + "\n"
      f.write(varStr)
  
  return None
  
#-------------------------------------------------------------------------
if __name__ == "__main__":
  main()
