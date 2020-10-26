# Copyright (c) 2015, Kai Chen <kchen@bnl.gov>
# All rights reserved.
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions are met:
 #
 #     * Redistributions of source code must retain the above copyright
 #       notice, this list of conditions and the following disclaimer.
 #     * Redistributions in binary form must reproduce the above copyright
 #       notice, this list of conditions and the following disclaimer in the
 #       documentation and/or other materials provided with the distribution.
 #
 # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 # ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 # WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 # DISCLAIMED. IN NO EVENT SHALL A COPYRIGHT HOLDER BE LIABLE FOR ANY
 # DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 # (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 # LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 # ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 # SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 #

# for IC & EC configuration: GBTX and GBT-SCA
# 2015 Nov.

import numpy as np

def crc16_ccitt(sel, data):
    #print data
    if sel==0:
        msb=0x00
        lsb=0x00
    elif sel==1:
        msb=0xFF
        lsb=0xFF
    else:
        msb=0x1D
        lsb=0x0F
    dataout=np.arange(len(data)+2)


    for i in range(len(data)):
        dataout[i]=int(data[i])
        x = int(data[i]) ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    dataout[i+1]=msb
    dataout[i+2]=lsb
    #print dataout
    return dataout

def bitreverse(DATA):
    for i in range(len(DATA)):
        DATA[i]=int('{:08b}'.format(int(DATA[i]))[::-1], 2)
    return DATA

def byte2bit(DATA):
    IN=np.arange(len(DATA)*8)
    for i in range(len(DATA)):
        temp=DATA[i]
        IN[i*8]=temp%2
        temp=int(temp/2)
        IN[i*8+1]=temp%2
        temp=int(temp/2)
        IN[i*8+2]=temp%2
        temp=int(temp/2)
        IN[i*8+3]=temp%2
        temp=int(temp/2)
        IN[i*8+4]=temp%2
        temp=int(temp/2)
        IN[i*8+5]=temp%2
        temp=int(temp/2)
        IN[i*8+6]=temp%2
        temp=int(temp/2)
        IN[i*8+7]=temp%2
    return IN

def bit_stuffing_and_delimiter(IN):
    OUT=np.arange(128)
    num=0
    k=8
    OUT[0]=0
    OUT[1]=1
    OUT[2]=1
    OUT[3]=1
    OUT[4]=1
    OUT[5]=1
    OUT[6]=1
    OUT[7]=0
    for i in range(len(IN)):
        OUT[k]=IN[i]
        k=k+1
        if IN[i]==0:
            num=0
        else:
            num=num+1
            if num==5:
                OUT[k]=0
                k=k+1
                num=0

    OUT[k]=0
    OUT[k+1]=1
    OUT[k+2]=1
    OUT[k+3]=1
    OUT[k+4]=1
    OUT[k+5]=1
    OUT[k+6]=1
    OUT[k+7]=0
    s=0
    for i in range(128-k-8):
        OUT[k+8+i]=1
        '''
        if s==7:
            OUT[k+8+i]=1
            s=0
        else:
            s=s+1
            OUT[k+8+i]=1
        '''
    return OUT

def DATA64b_gen(BITIN):
    
    DATA0=0
    DATA1=0

    offset=0
    for i in range(64):
        DATA0 = int(2**i*BITIN[i+offset]) | DATA0

    offset=64
    for i in range(64):
        DATA1 = int(2**i*BITIN[i+offset]) | DATA1

    return DATA0, DATA1

def parity_gen(DATAALL):
    length=len(DATAALL)
    PARITY=0
    for i in range(length):
        PARITY=PARITY ^ DATAALL[i]

    return PARITY



def byte64tobit(RXDATA0,RXDATA1):
    IN=np.arange(128)
    temp=RXDATA0
    for i in range(64):
        IN[i]=temp%2
        temp=temp>>1
    temp=RXDATA1
    for i in range(64):
        IN[64+i]=temp%2
        temp=temp>>1
    return IN

def bit_destuffing(IN):
    OUT=np.arange(128)
    k=0
    num=0
    for i in range(128-8):
        if IN[i+8]==0:
            # if num == 5:
            if (num==5 and list(IN[i+8:i+8+8]) != [0,1,1,1,1,1,1,0]):
                # print("bit de-stuffing")
                num=0
            else:
                num=0
                OUT[k]=0
                k=k+1
        elif num==6:
            #print("done")
            break;
        else:
            num=num+1
            OUT[k]=1
            k=k+1
    return OUT[0:k-6]

def delimiter_count(IN):
    one_num=0
    del_num=0
    for i in range(256):
       if IN[i]==0:
           if one_num==6:
               del_num+=1
               if del_num==2:
                   k=i+1
          
           one_num=0
          
       else:
           one_num+=1
    if del_num==3:
        OUT=IN[k-8:256]
    else:
        OUT=IN
           
    return OUT, del_num

def EC_PACKING(DATA):
    
    DATA=bitreverse(DATA)
    
    DATA1=crc16_ccitt(1,DATA)
    
    DATA1=bitreverse(DATA1)
    
    BITIN=byte2bit(DATA1)
    
    BITOUT=bit_stuffing_and_delimiter(BITIN)
    
    [DATA0,DATA1,DATA2,DATA3]=DATA64b_gen(BITOUT)
    return DATA0, DATA1, DATA2, DATA3

def EC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3):
    IN=byte64tobit(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    [OUT1, del_num]=delimiter_count(IN)
    #print "delimeter number: %d" % del_num
    OUT=bit_destuffing(OUT1)
    #print IN
    #print OUT
    RXDATA=np.arange(int(len(OUT)/8)-1)
    for i in range(len(RXDATA)):
        RXDATA[i]=0
        for j in range(8):
            RXDATA[i]+= OUT[8*i+j]*2**j
        RXDATA[i]=int(RXDATA[i])
    RXDATA=bitreverse(RXDATA)
    DATA_F=crc16_ccitt(1,RXDATA)
    DATA_F=bitreverse(DATA_F)
    CRC_ERR_FLAG=(DATA_F[len(RXDATA)]<<8)+DATA_F[len(RXDATA)+1]
    return DATA_F[0:len(RXDATA)-2], CRC_ERR_FLAG

def IC_PACKING(I2CADDR, ADDR, GBT_LEN, RW, DATA):
    cal_len=5
    if RW==0:
        cal_len+=GBT_LEN
    byte_len=8
    if RW==0:
        byte_len+=GBT_LEN

    ADDRL=ADDR%256
    ADDRH=int(ADDR/256)
    DATAALL=np.arange(30)
    DATAALL[0]=0x00
    if RW==0:
        DATAALL[1]=2*I2CADDR
    else:
        DATAALL[1]=2*I2CADDR+1
    DATAALL[2]=0x01
    DATAALL[3]=GBT_LEN
    DATAALL[4]=0x00
    DATAALL[5]=ADDRL
    DATAALL[6]=ADDRH
    for i in range(GBT_LEN):
        #print(i, DATA[i])
        DATAALL[7+i]=DATA[i]

    print(cal_len)
    print(DATAALL)
    print(DATAALL[2:2+cal_len])
    PARITY=parity_gen(DATAALL[2:2+cal_len])
    DATAALL[2+cal_len]=PARITY

    #IN=np.arange(256)
    #OUT=np.arange(256)
    BITIN=byte2bit(DATAALL[0:byte_len])

    BITOUT=bit_stuffing_and_delimiter(BITIN)
    [DATA0,DATA1]=DATA64b_gen(BITOUT)
    return DATA0, DATA1


def IC_DEPACKING(RXDATA0, RXDATA1):

    IN=byte64tobit(RXDATA0, RXDATA1)
    for i in range(0, IN.size, 8):
        print(str(i/8) + ": " + str(IN[i]) + str(IN[i+1]) + str(IN[i+2]) + str(IN[i+3]) + str(IN[i+4]) + str(IN[i+5]) + str(IN[i+6]) + str(IN[i+7]))
    print("OUT:")
    OUT=bit_destuffing(IN)
    print(OUT)
    for i in range(0, OUT.size, 8):
        print(str(i/8) + ": " + str(OUT[i]) + str(OUT[i+1]) + str(OUT[i+2]) + str(OUT[i+3]) + str(OUT[i+4]) + str(OUT[i+5]) + str(OUT[i+6]) + str(OUT[i+7]))

    GBTX_I2CADDR=OUT[1]+OUT[2]*2+OUT[3]*4+OUT[4]*8+OUT[5]*16+OUT[6]*32+OUT[7]*64
    GBTX_RW=OUT[0]
    TXCHK=OUT[16]
    GBTX_LEN=0
    GBTX_ADDR=0
    GBTX_CMD=0

    for i in range(8):
        GBTX_CMD += OUT[16+i]*2**i
    for i in range(16):
        GBTX_LEN += OUT[24+i]*2**i
    for i in range(16):
        GBTX_ADDR += OUT[40+i]*2**i
    GBTX_DATA=np.arange(GBTX_LEN)
    for i in range(GBTX_LEN):
        GBTX_DATA[i]=0
        for j in range(8):
            GBTX_DATA[i]+= OUT[56+8*i+j]*2**j
    GBTX_RXPARITY=0
    for i in range(8):
        GBTX_RXPARITY += OUT[56+8*GBTX_LEN+i]*2**i

    ALLDATA=np.arange(5+GBTX_LEN)
    ALLDATA[0]= GBTX_CMD
    ALLDATA[1]= GBTX_LEN%256
    ALLDATA[2]= int(GBTX_LEN/256)
    ALLDATA[3]= GBTX_ADDR%256
    ALLDATA[4]= int(GBTX_ADDR/256)
    for i in range(GBTX_LEN):
        ALLDATA[5+i]=GBTX_DATA[i]

    PARITY=parity_gen(ALLDATA[0:GBTX_LEN+5])

    if PARITY==GBTX_RXPARITY:
        RXCHK=1
    else:
        RXCHK=0


    return GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK

    #def test():

def IC_PACKING_NO_BIT_STUFFING(I2CADDR, ADDR, GBT_LEN, RW, DATA):
    cal_len=5
    if RW==0:
        cal_len+=GBT_LEN

    ADDRL=ADDR%256
    ADDRH=int(ADDR/256)
    DATAALL=np.arange(30)
    DATAALL[0]=0x7E
    DATAALL[1]=0x00
    if RW==0:
        DATAALL[2]=2*I2CADDR
    else:
        DATAALL[2]=2*I2CADDR+1
    DATAALL[3]=0x01
    DATAALL[4]=GBT_LEN
    DATAALL[5]=0x00
    DATAALL[6]=ADDRL
    DATAALL[7]=ADDRH
    for i in range(GBT_LEN):
        DATAALL[8+i]=DATA[i]

    PARITY=parity_gen(DATAALL[3:3+cal_len])
    DATAALL[3+cal_len]=PARITY
    DATAALL[4+cal_len]=0x7E
    cal_len=cal_len+5

    print(cal_len)

    return DATAALL, cal_len
   

def IC_DEPACKING_NO_BIT_DESTUFFING(DATA):
    
    '''
    IN=byte64tobit(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    OUT=bit_destuffing(IN)
    '''

    '''
    GBTX_I2CADDR=OUT[9]+OUT[10]*2+OUT[11]*4+OUT[12]*8+OUT[13]*16+OUT[14]*32+OUT[15]*64
    GBTX_RW=OUT[8]
    TXCHK=OUT[16]
    GBTX_LEN=0
    GBTX_ADDR=0
    GBTX_CMD=0

    for i in range(8):
        GBTX_CMD += OUT[16+i]*2**i
    for i in range(16):
        GBTX_LEN += OUT[24+i]*2**i
    for i in range(16):
        GBTX_ADDR += OUT[40+i]*2**i
    GBTX_DATA=range(GBTX_LEN)
    for i in range(GBTX_LEN):
        GBTX_DATA[i]=0
        for j in range(8):
            GBTX_DATA[i]+= OUT[56+8*i+j]*2**j
    GBTX_RXPARITY=0
    for i in range(8):
        GBTX_RXPARITY += OUT[56+8*GBTX_LEN+i]*2**i
    '''
    GBTX_RW=DATA[2]%2
    TXCHK=DATA[3]%2
    GBTX_I2CADDR=int(DATA[2]/2)
    GBTX_CMD=DATA[3]
    GBTX_LEN=DATA[4]+DATA[5]*256
    GBTX_ADDR=DATA[6]+DATA[7]*256
    GBTX_DATA=np.arange(GBTX_LEN)
    for i in range(GBTX_LEN):
        GBTX_DATA[i]=DATA[8+i]
    GBTX_RXPARITY=DATA[8+GBTX_LEN]    
        
    ALLDATA=np.arange(5+GBTX_LEN)
    ALLDATA[0]= GBTX_CMD
    ALLDATA[1]= GBTX_LEN%256
    ALLDATA[2]= int(GBTX_LEN/256)
    ALLDATA[3]= GBTX_ADDR%256
    ALLDATA[4]= int(GBTX_ADDR/256)
    for i in range(GBTX_LEN):
        ALLDATA[5+i]=GBTX_DATA[i]

    PARITY=parity_gen(ALLDATA[0:GBTX_LEN+5])

    if PARITY==GBTX_RXPARITY:
        RXCHK=1
    else:
        RXCHK=0


    return GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK
