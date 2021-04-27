# Based on code available at:
# https://github.com/simpway/HDLC-ICEC/blob/master/HDLC_ICEC_LIB_CK.py
# https://github.com/simpway/HDLC-ICEC/blob/master/software/ICOP.py
#
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

import time
import sys
import os
import subprocess
from typing import List
import numpy as np
from time import  sleep
from pyFlxlpGBT import  * 

# First, instantiate a lpGBTManager to handle communication with the FLX Card 
# For example, card 0 , setting verbosity level to INFO 

manager = lpGBTManager(cardnr=0,verbose="INFO")
manager.ReadFEB2Registers()
manager.InitializeFEB2()
#from HDLC_ICEC_LIB_CK_ANALOG_TB import IC_PACKING
#from HDLC_ICEC_LIB_CK_ANALOG_TB import IC_DEPACKING

VERBOSE = False
READBACK = False
DEBUG = False

REG_IC_CONTROL=0x6640

REG_IC_1_TX_DATA_0=0x6650
REG_IC_1_TX_DATA_1=0x6660
REG_IC_1_TX_DATA_2=0x6670
REG_IC_1_TX_DATA_3=0x6680

REG_IC_2_TX_DATA_0=0x6690
REG_IC_2_TX_DATA_1=0x66a0
REG_IC_2_TX_DATA_2=0x66b0
REG_IC_2_TX_DATA_3=0x66c0

REG_EC_1_TX_DATA_0=0x6720
REG_EC_1_TX_DATA_1=0x6730
REG_EC_1_TX_DATA_2=0x6740
REG_EC_1_TX_DATA_3=0x6750

REG_EC_2_TX_DATA_0=0x6760
REG_EC_2_TX_DATA_1=0x6770
REG_EC_2_TX_DATA_2=0x6780
REG_EC_2_TX_DATA_3=0x6790

REG_IC_1_RX_DATA_0=0x7850
REG_IC_1_RX_DATA_1=0x7860
REG_IC_1_RX_DATA_2=0x7870
REG_IC_1_RX_DATA_3=0x7880

REG_IC_2_RX_DATA_0=0x7890
REG_IC_2_RX_DATA_1=0x78a0
REG_IC_2_RX_DATA_2=0x78b0
REG_IC_2_RX_DATA_3=0x78c0

REG_EC_1_RX_DATA_0=0x78d0
REG_EC_1_RX_DATA_1=0x78e0
REG_EC_1_RX_DATA_2=0x78f0
REG_EC_1_RX_DATA_3=0x7900

REG_EC_2_RX_DATA_0=0x7910
REG_EC_2_RX_DATA_1=0x7920
REG_EC_2_RX_DATA_2=0x7930
REG_EC_2_RX_DATA_3=0x7940

REG_ICEC_TRIG = 0x6640

REG_ICECBUSY = 0x6a80

REG_FECERROR = 0x6750
REG_BITERROR_RESET = 0x5410

REG_IC_STATUS = 0x7840


def icWriteToLpGBT(GBTX_I2CADDR: int, GBTX_ADDR: int, data_orig: List[int], ICEC_CHANNEL):

    if ICEC_CHANNEL == 0:  # should be connected to lpGBT12 
        REG_IC_TX_DATA_0 = REG_IC_1_TX_DATA_0
        REG_IC_TX_DATA_1 = REG_IC_1_TX_DATA_1
        REG_IC_TX_DATA_2 = REG_IC_1_TX_DATA_2
        REG_IC_TX_DATA_3 = REG_IC_1_TX_DATA_3
        REG_IC_RX_DATA_0 = REG_IC_1_RX_DATA_0
        REG_IC_RX_DATA_1 = REG_IC_1_RX_DATA_1
        REG_IC_RX_DATA_2 = REG_IC_1_RX_DATA_2
        REG_IC_RX_DATA_3 = REG_IC_1_RX_DATA_3
        ICEC_TRIG = 0x001
    elif ICEC_CHANNEL == 1:  # should be connected to lpGBT13 
        REG_IC_TX_DATA_0 = REG_IC_2_TX_DATA_0
        REG_IC_TX_DATA_1 = REG_IC_2_TX_DATA_1
        REG_IC_TX_DATA_2 = REG_IC_2_TX_DATA_2
        REG_IC_TX_DATA_3 = REG_IC_2_TX_DATA_3
        REG_IC_RX_DATA_0 = REG_IC_2_RX_DATA_0
        REG_IC_RX_DATA_1 = REG_IC_2_RX_DATA_1
        REG_IC_RX_DATA_2 = REG_IC_2_RX_DATA_2
        REG_IC_RX_DATA_3 = REG_IC_2_RX_DATA_3
        ICEC_TRIG = 0x002
    else:
        print("No valid ICEC_CHANNEL specified for IC Write")
        return

    GBTX_DATA=np.arange(16)    
    #new_data = ''.join(hex(val) for val in data_orig)
    GBTX_LEN = len(data_orig)
    GBTX_RW = 0

    for i in range(GBTX_LEN):
        #GBTX_DATA[i]=int(new_data[2*i:2*i+2],16)
        GBTX_DATA[i]=data_orig[i]
    
    # print("Data:", data_orig)
    #print("Writing",GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)
    [TXDATA0, TXDATA1, TXDATA2, TXDATA3]=IC_PACKING(GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)

    if VERBOSE:
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX DATA TO SENT: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
    if DEBUG:
        print("---------------Tx information------------------")
        print("Check the Rx packet")
        print("GBTX I2C ADDR: " + str(hex(GBTX_I2CADDR)))
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
        print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
        if GBTX_RW==0:
            print("GBTX DATA TO SEND: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
        print("-------------Tx packet--------------------------")

        print(hex(TXDATA0))
        print(hex(TXDATA1))
        print(hex(TXDATA2))
        print(hex(TXDATA3))

    reg_write64b(REG_IC_TX_DATA_0, TXDATA0)
    reg_write64b(REG_IC_TX_DATA_1, TXDATA1)
    reg_write64b(REG_IC_TX_DATA_2, TXDATA2)
    reg_write64b(REG_IC_TX_DATA_3, TXDATA3)

    # reg_write64b(REG_IC_CONTROL, 0x001)
    reg_write64b(REG_IC_CONTROL, ICEC_TRIG)
    reg_write64b(REG_IC_CONTROL, 0x000)
    
#     status = int(reg_read64b(REG_IC_STATUS))
#     while(status!=0):
#         sleep(0.01)
#         status = int(reg_read64b(REG_IC_STATUS))
#         print (status)


# """
    if READBACK:
        try:
            RXDATA0 = reg_read64b(REG_IC_RX_DATA_0)
            RXDATA1 = reg_read64b(REG_IC_RX_DATA_1)
            RXDATA2 = reg_read64b(REG_IC_RX_DATA_2)
            RXDATA3 = reg_read64b(REG_IC_RX_DATA_3)

            [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK] = IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
            print("GBTX READBACK REGISTER: " + str(hex(GBTX_ADDR)))
            print("GBTX DATA READBACK: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
        except Exception as e:
            print(f"Couldn't read back register {GBTX_ADDR:03x}")
            print(e)

    if DEBUG:
        try:
            RXDATA0=reg_read64b(REG_IC_RX_DATA_0)
            RXDATA1=reg_read64b(REG_IC_RX_DATA_1)
            RXDATA2=reg_read64b(REG_IC_RX_DATA_2)
            RXDATA3=reg_read64b(REG_IC_RX_DATA_3)


            print("-------------Rx packet--------------------------")
            print(hex(RXDATA0))
            print(hex(RXDATA1))
            print(hex(RXDATA2))
            print(hex(RXDATA3))


            [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
            print("-------------Check the Rx packet--------------------")
            print("GBTX DEVICE ADDR: " + str(hex(GBTX_I2CADDR)))
            print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
            print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
            print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
            print("GBTX DATA READBACK: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
            if GBTX_RW==0:
                print("GBTX TX PARITY CHECK, 1 means no error: " + str(TXCHK))
            print("GBTX RX PARITY CHECK, 1 means no error: " + str(RXCHK))
        except Exception as e:
            print(f"Couldn't read back register {GBTX_ADDR:03x}")
            print(e)
# """

def ecWriteToLpGBT(GBTX_I2CADDR: int, GBTX_ADDR: int, data_orig: List[int], ICEC_CHANNEL):

    if ICEC_CHANNEL == 0:  # should be connected to lpGBT12 
        REG_EC_TX_DATA_0 = REG_EC_1_TX_DATA_0
        REG_EC_TX_DATA_1 = REG_EC_1_TX_DATA_1
        REG_EC_TX_DATA_2 = REG_EC_1_TX_DATA_2
        REG_EC_TX_DATA_3 = REG_EC_1_TX_DATA_3
        REG_EC_RX_DATA_0 = REG_EC_1_RX_DATA_0
        REG_EC_RX_DATA_1 = REG_EC_1_RX_DATA_1
        REG_EC_RX_DATA_2 = REG_EC_1_RX_DATA_2
        REG_EC_RX_DATA_3 = REG_EC_1_RX_DATA_3
        ICEC_TRIG = 0x100
    elif ICEC_CHANNEL == 1:  # should be connected to lpGBT13 
        REG_EC_TX_DATA_0 = REG_EC_2_TX_DATA_0
        REG_EC_TX_DATA_1 = REG_EC_2_TX_DATA_1
        REG_EC_TX_DATA_2 = REG_EC_2_TX_DATA_2
        REG_EC_TX_DATA_3 = REG_EC_2_TX_DATA_3
        REG_EC_RX_DATA_0 = REG_EC_2_RX_DATA_0
        REG_EC_RX_DATA_1 = REG_EC_2_RX_DATA_1
        REG_EC_RX_DATA_2 = REG_EC_2_RX_DATA_2
        REG_EC_RX_DATA_3 = REG_EC_2_RX_DATA_3
        ICEC_TRIG = 0x200
    else:
        print("No valid ICEC_CHANNEL specified for EC Write")
        return

    GBTX_DATA=np.arange(16)    
    #new_data = ''.join(hex(val) for val in data_orig)
    GBTX_LEN = len(data_orig)
    GBTX_RW = 0

    for i in range(GBTX_LEN):
        #GBTX_DATA[i]=int(new_data[2*i:2*i+2],16)
        GBTX_DATA[i]=data_orig[i]
    
    # print("Data:", data_orig)
    #print("Writing",GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)
    [TXDATA0, TXDATA1, TXDATA2, TXDATA3]=IC_PACKING(GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)

    if VERBOSE:
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX DATA TO SENT: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
    if DEBUG:
        print("---------------Tx information------------------")
        print("Check the Rx packet")
        print("GBTX I2C ADDR: " + str(hex(GBTX_I2CADDR)))
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
        print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
        if GBTX_RW==0:
            print("GBTX DATA TO SENT: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
        print("-------------Tx packet--------------------------")

        print(hex(TXDATA0))
        print(hex(TXDATA1))
        print(hex(TXDATA2))
        print(hex(TXDATA3))

    reg_write64b(REG_EC_TX_DATA_0, TXDATA0)
    reg_write64b(REG_EC_TX_DATA_1, TXDATA1)
    reg_write64b(REG_EC_TX_DATA_2, TXDATA2)
    reg_write64b(REG_EC_TX_DATA_3, TXDATA3)

    # reg_write64b(REG_IC_CONTROL, 0x100)
    reg_write64b(REG_IC_CONTROL, ICEC_TRIG)
    reg_write64b(REG_IC_CONTROL, 0x000)
    
#     status = int(reg_read64b(REG_IC_STATUS))
#     while(status!=0):
#         sleep(0.01)
#         status = int(reg_read64b(REG_IC_STATUS))

# """
    if READBACK:
        try:
            RXDATA0=reg_read64b(REG_EC_RX_DATA_0)
            RXDATA1=reg_read64b(REG_EC_RX_DATA_1)
            RXDATA2=reg_read64b(REG_EC_RX_DATA_2)
            RXDATA3=reg_read64b(REG_EC_RX_DATA_3)

            [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
            print("GBTX READBACK REGISTER: " + str(hex(GBTX_ADDR)))
            print("GBTX DATA READBACK: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
        except Exception as e:
            print(f"Couldn't read back register {GBTX_ADDR:03x}")
            print(e)

    if DEBUG:
        try:
            RXDATA0=reg_read64b(REG_EC_RX_DATA_0)
            RXDATA1=reg_read64b(REG_EC_RX_DATA_1)
            RXDATA2=reg_read64b(REG_EC_RX_DATA_2)
            RXDATA3=reg_read64b(REG_EC_RX_DATA_3)


            print("-------------Rx packet--------------------------")
            print(hex(RXDATA0))
            print(hex(RXDATA1))
            print(hex(RXDATA2))
            print(hex(RXDATA3))


            [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
            print("-------------Check the Rx packet--------------------")
            # print("GBTX DEVICE ADDR: " + str(hex(GBTX_I2CADDR)))
            print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
            print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
            print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
            print("GBTX DATA READBACK: " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
            if GBTX_RW==0:
                print("GBTX TX PARITY CHECK, 1 means no error: " + str(TXCHK))
            print("GBTX RX PARITY CHECK, 1 means no error: " + str(RXCHK))
        except Exception as e:
            print(f"Couldn't read back register {GBTX_ADDR:03x}")
            print(e)
# """

def icReadLpGBT(GBTX_I2CADDR: int, GBTX_ADDR: int, GBTX_LEN: int, ICEC_CHANNEL):

    if ICEC_CHANNEL == 0:  # should be connected to lpGBT12 
        REG_IC_TX_DATA_0 = REG_IC_1_TX_DATA_0
        REG_IC_TX_DATA_1 = REG_IC_1_TX_DATA_1
        REG_IC_TX_DATA_2 = REG_IC_1_TX_DATA_2
        REG_IC_TX_DATA_3 = REG_IC_1_TX_DATA_3
        REG_IC_RX_DATA_0 = REG_IC_1_RX_DATA_0
        REG_IC_RX_DATA_1 = REG_IC_1_RX_DATA_1
        REG_IC_RX_DATA_2 = REG_IC_1_RX_DATA_2
        REG_IC_RX_DATA_3 = REG_IC_1_RX_DATA_3
        ICEC_TRIG = 0x001
    elif ICEC_CHANNEL == 1:  # should be connected to lpGBT13 
        REG_IC_TX_DATA_0 = REG_IC_2_TX_DATA_0
        REG_IC_TX_DATA_1 = REG_IC_2_TX_DATA_1
        REG_IC_TX_DATA_2 = REG_IC_2_TX_DATA_2
        REG_IC_TX_DATA_3 = REG_IC_2_TX_DATA_3
        REG_IC_RX_DATA_0 = REG_IC_2_RX_DATA_0
        REG_IC_RX_DATA_1 = REG_IC_2_RX_DATA_1
        REG_IC_RX_DATA_2 = REG_IC_2_RX_DATA_2
        REG_IC_RX_DATA_3 = REG_IC_2_RX_DATA_3
        ICEC_TRIG = 0x002
    else:
        print("No valid ICEC_CHANNEL specified for IC Read")
        return

    #GBTX_DATA=np.arange(16)    
    GBTX_DATA=[-1 for i in range(0,16)]    
    #new_data = ''.join(hex(val) for val in data_orig)
    GBTX_RW = 1

    #print("Writing",GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)
    [TXDATA0, TXDATA1, TXDATA2, TXDATA3]=IC_PACKING(GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)

    if DEBUG:
        print("---------------Tx information------------------")
        print("Check the Rx packet")
        print("GBTX I2C ADDR: " + str(hex(GBTX_I2CADDR)))
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
        print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
        if GBTX_RW==0:
           print("GBTX DATA TO SENT: " + str(GBTX_DATA[0:GBTX_LEN]))
        print("-------------Tx packet--------------------------")

        print(hex(TXDATA0))
        print(hex(TXDATA1))

    reg_write64b(REG_IC_TX_DATA_0, TXDATA0)
    reg_write64b(REG_IC_TX_DATA_1, TXDATA1)
    reg_write64b(REG_IC_TX_DATA_2, TXDATA2)
    reg_write64b(REG_IC_TX_DATA_3, TXDATA3)

    # reg_write64b(REG_IC_CONTROL, 0x001)
    reg_write64b(REG_IC_CONTROL, ICEC_TRIG)
    reg_write64b(REG_IC_CONTROL, 0x000)

    RXDATA0=reg_read64b(REG_IC_RX_DATA_0)
    RXDATA1=reg_read64b(REG_IC_RX_DATA_1)
    RXDATA2=reg_read64b(REG_IC_RX_DATA_2)
    RXDATA3=reg_read64b(REG_IC_RX_DATA_3)

    try:
        [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    except Exception as e:
        print(f"Couldn't read back register {GBTX_ADDR:03x}")
        print(e)

    if DEBUG:
        print("-------------Rx packet--------------------------")
        print(hex(RXDATA0))
        print(hex(RXDATA1))
        print(hex(RXDATA2))
        print(hex(RXDATA3))

        print("-------------Check the Rx packet--------------------")
        print("GBTX DEVICE ADDR: " + str(hex(GBTX_I2CADDR)))
        print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
        print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
        print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
        print("GBTX DATA READBACK: " + str(GBTX_DATA[0:GBTX_LEN]))
        if GBTX_RW==0:
           print("GBTX TX PARITY CHECK, 1 means no error: " + str(TXCHK))
        print("GBTX RX PARITY CHECK, 1 means no error: " + str(RXCHK))

    if VERBOSE:
        print("address", str(hex(GBTX_ADDR)), "read " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
    return GBTX_DATA[0:GBTX_LEN]

def ecReadLpGBT(GBTX_I2CADDR: int, GBTX_ADDR: int, GBTX_LEN: int, ICEC_CHANNEL):

    if ICEC_CHANNEL == 0:  # should be connected to lpGBT12 
        REG_EC_TX_DATA_0 = REG_EC_1_TX_DATA_0
        REG_EC_TX_DATA_1 = REG_EC_1_TX_DATA_1
        REG_EC_TX_DATA_2 = REG_EC_1_TX_DATA_2
        REG_EC_TX_DATA_3 = REG_EC_1_TX_DATA_3
        REG_EC_RX_DATA_0 = REG_EC_1_RX_DATA_0
        REG_EC_RX_DATA_1 = REG_EC_1_RX_DATA_1
        REG_EC_RX_DATA_2 = REG_EC_1_RX_DATA_2
        REG_EC_RX_DATA_3 = REG_EC_1_RX_DATA_3
        ICEC_TRIG = 0x100
    elif ICEC_CHANNEL == 1:  # should be connected to lpGBT13 
        REG_EC_TX_DATA_0 = REG_EC_2_TX_DATA_0
        REG_EC_TX_DATA_1 = REG_EC_2_TX_DATA_1
        REG_EC_TX_DATA_2 = REG_EC_2_TX_DATA_2
        REG_EC_TX_DATA_3 = REG_EC_2_TX_DATA_3
        REG_EC_RX_DATA_0 = REG_EC_2_RX_DATA_0
        REG_EC_RX_DATA_1 = REG_EC_2_RX_DATA_1
        REG_EC_RX_DATA_2 = REG_EC_2_RX_DATA_2
        REG_EC_RX_DATA_3 = REG_EC_2_RX_DATA_3
        ICEC_TRIG = 0x200
    else:
        print("No valid ICEC_CHANNEL specified for EC Write")
        return

    #GBTX_DATA=np.arange(16)    
    GBTX_DATA=[-1 for i in range(0,16)]    

    #new_data = ''.join(hex(val) for val in data_orig)
    GBTX_RW = 1

    #print("Writing",GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)
    [TXDATA0, TXDATA1, TXDATA2, TXDATA3]=IC_PACKING(GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)

    #print("---------------Tx information------------------")
    #print("Check the Rx packet")
    #print("GBTX I2C ADDR: " + str(hex(GBTX_I2CADDR)))
    #print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
    #print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
    #print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
    #if GBTX_RW==0:
    #   print("GBTX DATA TO SENT: " + str(GBTX_DATA[0:GBTX_LEN]))
    #print("-------------Tx packet--------------------------")

    #print(hex(TXDATA0))
    #print(hex(TXDATA1))

    reg_write64b(REG_EC_TX_DATA_0, TXDATA0)
    reg_write64b(REG_EC_TX_DATA_1, TXDATA1)
    reg_write64b(REG_EC_TX_DATA_2, TXDATA2)
    reg_write64b(REG_EC_TX_DATA_3, TXDATA3)

    # reg_write64b(REG_IC_CONTROL, 0x100)
    reg_write64b(REG_IC_CONTROL, ICEC_TRIG)
    reg_write64b(REG_IC_CONTROL, 0x000)

    RXDATA0=reg_read64b(REG_EC_RX_DATA_0)
    RXDATA1=reg_read64b(REG_EC_RX_DATA_1)
    RXDATA2=reg_read64b(REG_EC_RX_DATA_2)
    RXDATA3=reg_read64b(REG_EC_RX_DATA_3)

    #print("-------------Rx packet--------------------------")
    #print(hex(RXDATA0))
    #print(hex(RXDATA1))
    #print(hex(RXDATA2))
    #print(hex(RXDATA3))

    try:
        [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    except Exception as e:
        print(f"Couldn't read back register {GBTX_ADDR:03x}")
        print(e)

    #print("-------------Check the Rx packet--------------------")
    #print("GBTX DEVICE ADDR: " + str(hex(GBTX_I2CADDR)))
    #print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
    #print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
    #print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
    #print("GBTX DATA READBACK: " + str(GBTX_DATA[0:GBTX_LEN]))
    #if GBTX_RW==0:
    #   print("GBTX TX PARITY CHECK, 1 means no error: " + str(TXCHK))
    #print("GBTX RX PARITY CHECK, 1 means no error: " + str(RXCHK))

    #print("address", str(hex(GBTX_ADDR)), "read " + str(GBTX_DATA[0:GBTX_LEN]))
    if VERBOSE:
        print("address", str(hex(GBTX_ADDR)), "read " + str([hex(i) for i in GBTX_DATA[0:GBTX_LEN]]))
    return GBTX_DATA[0:GBTX_LEN]

################################################################

def reg_read64b(addr):
    #value = "%16lx"%(manager.ReadFEB2Register(addr))
    return manager.ReadFEB2Register(addr)
    #print(value)
    #return int(value)


def reg_write64b(addr,data):
    return_value = manager.WriteFEB2Register(addr,data)
    # print(return_value)


def DATA64b_gen(BITIN):
    DATA0 = 0
    DATA1 = 0
    DATA2 = 0
    DATA3 = 0
    #print("BITIN: ", BITIN)
    offset = 0
    for i in range(64):
        DATA0 |= int(BITIN[i + offset] << i)

    offset = 64
    for i in range(64):
        DATA1 |= int(BITIN[i + offset] << i)

    offset = 128
    for i in range(64):
        DATA2 |= int(BITIN[i + offset] << i)

    offset = 192
    for i in range(64):
        DATA3 |= int(BITIN[i + offset] << i)

    return DATA0, DATA1, DATA2, DATA3


def parity_gen(DATAALL):
    length=len(DATAALL)
    PARITY=0
    for i in range(length):
        PARITY=PARITY ^ DATAALL[i]

    return PARITY


def bit_stuffing_and_delimiter(IN):
    OUT = [0]*256
    num = 0
    k = 8
    OUT[0] = 0
    OUT[1] = 1
    OUT[2] = 1
    OUT[3] = 1
    OUT[4] = 1
    OUT[5] = 1
    OUT[6] = 1
    OUT[7] = 0
    for i in range(len(IN)):
        OUT[k] = IN[i]
        k += 1
        if IN[i] == 0:
            num = 0
        else:
            num += 1
            if num == 5:
                OUT[k] = 0
                k += 1
                num = 0

    OUT[k] = 0
    OUT[k+1] = 1
    OUT[k+2] = 1
    OUT[k+3] = 1
    OUT[k+4] = 1
    OUT[k+5] = 1
    OUT[k+6] = 1
    OUT[k+7] = 0

    for i in range(256 - k - 8):
        OUT[k + 8 + i] = 1

    return OUT


def bit_destuffing(IN):
    OUT = [0]*256
    k = 0
    num = 0
    for i in range(256 - 8):
        if IN[i+8] == 0:
            if num == 5 and list(IN[i + 8:i + 8 + 8]) != [0, 1, 1, 1, 1, 1, 1, 0]:
                #print("bit de-stuffing")
                num = 0
            else:
                num = 0
                OUT[k] = 0
                k += 1
        elif num == 6:
            #print("done")
            break
        else:
            num += 1
            OUT[k] = 1
            k += 1

    return OUT[0:k-6]


def byte2bit(DATA):
    IN = [0] * (len(DATA) * 8)
    for i in range(len(DATA)):
        for j in range(8):
            IN[i*8 + j] = (DATA[i] >> j) & 0x01

    return IN


def byte64tobit(RXDATA0, RXDATA1, RXDATA2, RXDATA3):
    IN = [0] * 256
    for (i, RXDATA) in enumerate([RXDATA0, RXDATA1, RXDATA2, RXDATA3]):
        for j in range(64):
            IN[(64 * i) + j] = (RXDATA >> j) & 0x01

    return IN


def IC_PACKING(I2CADDR, ADDR, GBT_LEN, RW, DATA):
    cal_len = 5
    byte_len = 8
    if RW == 0:
        cal_len += GBT_LEN
        byte_len += GBT_LEN

    ADDRL = ADDR & 0xff
    ADDRH = ADDR >> 8
    DATAALL = [0]*24
    if RW == 0:
        DATAALL[1] = (I2CADDR << 1) | 0
    else:
        DATAALL[1] = (I2CADDR << 1) | 1
    DATAALL[2] = 0x01
    DATAALL[3] = GBT_LEN & 0xff
    DATAALL[4] = GBT_LEN >> 8
    DATAALL[5] = ADDRL
    DATAALL[6] = ADDRH

    for i in range(GBT_LEN):
        DATAALL[7+i] = DATA[i]

    PARITY = parity_gen(DATAALL[2:2+cal_len])
    DATAALL[2+cal_len] = PARITY

    BITIN = byte2bit(DATAALL[0:byte_len])
    BITOUT = bit_stuffing_and_delimiter(BITIN)
    [DATA0, DATA1, DATA2, DATA3] = DATA64b_gen(BITOUT)

    return DATA0, DATA1, DATA2, DATA3


def IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3):

    IN = byte64tobit(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    # print(IN)
    OUT = bit_destuffing(IN)
    #print(OUT)

    GBTX_I2CADDR = 0
    for i in range(7):
        GBTX_I2CADDR += OUT[9 + i] << i
    GBTX_RW = OUT[8]
    TXCHK = OUT[16]

    GBTX_LEN = 0
    GBTX_ADDR = 0
    GBTX_CMD = 0

    for i in range(8):
        GBTX_CMD += OUT[16 + i] << i
    for i in range(16):
        # GBTX_LEN += OUT[24 + i] << i
        GBTX_LEN += OUT[24 + i]*2**i
    for i in range(16):
        GBTX_ADDR += OUT[40 + i] << i
    GBTX_DATA = [0]*GBTX_LEN
    #print(GBTX_LEN)
    #print(len(OUT))
    for i in range(GBTX_LEN):
        for j in range(8):
            GBTX_DATA[i] += OUT[56 + 8 * i + j] << j
                
    GBTX_RXPARITY = 0
    for i in range(8):
        GBTX_RXPARITY += OUT[56 + 8 * GBTX_LEN + i] << i
        
    ALLDATA = [0] * (5 + GBTX_LEN)
    ALLDATA[0] = GBTX_CMD
    ALLDATA[1] = GBTX_LEN & 0xff
    ALLDATA[2] = GBTX_LEN >> 8
    ALLDATA[3] = GBTX_ADDR & 0xff
    ALLDATA[4] = GBTX_ADDR >> 8
    for i in range(GBTX_LEN):
        ALLDATA[5 + i] = GBTX_DATA[i]

    PARITY = parity_gen(ALLDATA[0:GBTX_LEN+5])

    if PARITY == GBTX_RXPARITY:
        RXCHK = 1
    else:
        RXCHK = 0

    return GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK
