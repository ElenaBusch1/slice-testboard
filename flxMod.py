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

import subprocess
from typing import List

REG_ICEC_CHANSEL = 0x58c0
REG_TX_ICDATA_63to0 = 0x5900
REG_TX_ICDATA_127to64 = 0x5910
REG_TX_ICDATA_191to128 = 0x5920
REG_TX_ICDATA_255to192 = 0x5930
REG_ICEC_TRIG = 0x58b0

REG_RX_ICDATA_63to0 = 0x6a00
REG_RX_ICDATA_127to64 = 0x6a10
REG_RX_ICDATA_191to128 = 0x6a20
REG_RX_ICDATA_255to192 = 0x6a30
REG_ICECBUSY = 0x6a80

REG_FECERROR = 0x6750
REG_BITERROR_RESET = 0x5410


def icWriteToLpGBT(GBTX_I2CADDR: int, GBTX_ADDR: int, GBTX_DATA: List[int]):
    GBTX_LEN = len(GBTX_DATA)
    GBTX_RW = 0
    channel = 2
    [TXDATA0, TXDATA1, TXDATA2, TXDATA3] = IC_PACKING(GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA)

    print("---------------Tx information------------------")
    print("Check the Rx packet")
    print("TX GBT CHANNEL: " + str(channel))
    print("GBTX I2C ADDR: " + str(hex(GBTX_I2CADDR)))
    print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
    print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
    print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
    if GBTX_RW == 0:
        print("GBTX DATA TO SENT: " + str(GBTX_DATA[0:GBTX_LEN]))
    print("-------------Tx packet--------------------------")
    print(hex(TXDATA0))
    print(hex(TXDATA1))
    print(hex(TXDATA2))
    print(hex(TXDATA3))

    reg_write64b(REG_ICEC_CHANSEL, channel*257)

    reg_write64b(REG_TX_ICDATA_63to0, TXDATA0)
    reg_write64b(REG_TX_ICDATA_127to64, TXDATA1)
    reg_write64b(REG_TX_ICDATA_191to128, TXDATA2)
    reg_write64b(REG_TX_ICDATA_255to192, TXDATA3)

    reg_write64b(REG_ICEC_TRIG, 2**channel)
    reg_write64b(REG_ICEC_TRIG, 0x0)
    done=0
    BUSY_SIGNAL=int(reg_read64b(REG_ICECBUSY),16)
    reg_write64b(REG_BITERROR_RESET, 0x1)
    reg_write64b(REG_BITERROR_RESET, 0x0)
    FEC_ERROR=int(reg_read64b(REG_FECERROR),16)

    rxchannel = 0
    if int(BUSY_SIGNAL/(2**(channel)))%2 ==0 and int(FEC_ERROR/(2**(channel)))%2 ==0:
        done=1
        rxchannel=channel
        print("the same RX GBT channel get replied message")
    else:
        temp=BUSY_SIGNAL
        err_temp=FEC_ERROR

        for i in range(24):
            print(i)
            if temp%2==0 and err_temp%2==0 :
                rxchannel=i
                print("the RX GBT channel %d get replied message" % rxchannel)
                done=1
                break;
            else:
                temp=int(temp/2)
                err_temp=int(err_temp/2)
    if done==0:
        print("operation failed")


    reg_write64b(REG_ICEC_CHANSEL, rxchannel*257)

    RXDATA0=int(reg_read64b(REG_RX_ICDATA_63to0),16)
    RXDATA1=int(reg_read64b(REG_RX_ICDATA_127to64),16)
    RXDATA2=int(reg_read64b(REG_RX_ICDATA_191to128),16)
    RXDATA3=int(reg_read64b(REG_RX_ICDATA_255to192),16)
    '''
    RXDATA0=TXDATA0
    RXDATA1=TXDATA1
    RXDATA2=TXDATA2
    RXDATA3=TXDATA3
    '''
    print("-------------Rx packet--------------------------")
    print(hex(RXDATA0))
    print(hex(RXDATA1))
    print(hex(RXDATA2))
    print(hex(RXDATA3))


    [GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK]=IC_DEPACKING(RXDATA0, RXDATA1, RXDATA2, RXDATA3)
    print("-------------Check the Rx packet--------------------")
    print("RX GBT CHANNEL: " + str(rxchannel))
    print("GBTX DEVICE ADDR: " + str(hex(GBTX_I2CADDR)))
    print("GBTX REG ADDR: " + str(hex(GBTX_ADDR)))
    print("GBTX BYTES R/W LENGTH, 1 means 1 byte: " + str(GBTX_LEN))
    print("GBTX OPERATION TYPE, 1 means READ, 0 means WRITEandREAD: " + str(GBTX_RW))
    print("GBTX DATA READBACK: " + str(GBTX_DATA[0:GBTX_LEN]))
    if GBTX_RW==0:
        print("GBTX TX PARITY CHECK, 1 means no error: " + str(TXCHK))
    print("GBTX RX PARITY CHECK, 1 means no error: " + str(RXCHK))


def reg_read64b(addr):
    addr_str = hex(addr)
    process = subprocess.run(["fpepo", "-d", "0", "-b", "2", addr_str, "-r", "8"], capture_output=True)
    retvalue = process.stdout.decode("utf-8").split("\n")
    # print(retvalue)
    ret = f"{int(retvalue[0][6:], 16):016x}"
    return ret


def reg_write64b(addr, data):
    addr_str = hex(addr)
    data_str = hex(data)
    subprocess.run(["fpepo", "-d", "0", "-b", "2", "-n", "64", addr_str, data_str])


def DATA64b_gen(BITIN):
    DATA0 = 0
    DATA1 = 0
    DATA2 = 0
    DATA3 = 0

    offset = 0
    for i in range(64):
        DATA0 |= BITIN[i + offset] << i

    offset = 64
    for i in range(64):
        DATA1 |= BITIN[i + offset] << i

    offset = 128
    for i in range(64):
        DATA2 |= BITIN[i + offset] << i

    offset = 192
    for i in range(64):
        DATA3 |= BITIN[i + offset] << i

    return DATA0, DATA1, DATA2, DATA3


def parity_gen(DATAALL):
    PARITY = 0
    for word in DATAALL:
        PARITY ^= word

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
            if num == 5 and list(IN[i + 8:i + 8 + 8] != [0, 1, 1, 1, 1, 1, 1, 0]):
                print("bit de-stuffing")
                num = 0
            else:
                num = 0
                OUT[k] = 0
                k += 1
        elif num == 6:
            print("done")
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
    OUT = bit_destuffing(IN)

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
        GBTX_LEN += OUT[24 + i] << i
    for i in range(16):
        GBTX_ADDR += OUT[40 + i] << i
    GBTX_DATA = [0]*GBTX_LEN
    for i in range(GBTX_LEN):
        for j in range(8):
            GBTX_DATA += OUT[56 + 8 * i + j] << j
    GBTX_RXPARITY = 0
    for i in range(8):
        GBTX_RXPARITY += OUT[56 + 8 * GBTX_LEN + i] << i

    ALLDATA = [0] * (5 + GBTX_LEN)
    ALLDATA[0] = GBTX_CMD
    ALLDATA[1] = GBTX_LEN & 0xff
    ALLDATA[2] = GBTX_LEN << 8
    ALLDATA[3] = GBTX_ADDR & 0xff
    ALLDATA[4] = GBTX_ADDR << 8
    for i in range(GBTX_LEN):
        ALLDATA[5 + i] = GBTX_DATA[i]

    PARITY = parity_gen(ALLDATA[0:GBTX_LEN+5])

    if PARITY == GBTX_RXPARITY:
        RXCHK = 1
    else:
        RXCHK = 0

    return GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, GBTX_RW, GBTX_DATA, TXCHK, RXCHK
