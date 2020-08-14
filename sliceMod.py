import time
import serialMod

#######################################################################
# Functions for communicating via IC frame

def parity_gen(DATAALL):
    PARITY = 0
    for word in DATAALL:
        PARITY = PARITY ^ int(word, 2)
    return PARITY


def LpGBT_IC_REGWRRD(GUI, port, reg_addr, data):
    # write to I2C, then reads back

    status = getattr(GUI, "status" + port)
    status.send()

    dpWriteAddress = '000000000001'  # 12
    wordCount = f'{88:08b}'  # 8
    downlinkSignalOperation = '11'  # 2
    playOutFlag = '1'  # 1
    playCount = '00001'  # 5
    # overhead = 28
    word1 = f'{0x7E:08b}'  # frame delimter
    word2 = f'{0x00:08b}'  # reserved
    word3 = f'{0xE0:08b}'  # I2C address of LpGBT
    word4 = f'{0x01:08b}'  # command
    word5 = f'{0x01:08b}'  # number words
    word6 = f'{0x00:08b}'
    word7 = f'{(reg_addr & 0xFF):08b}'  # reg addr low
    word8 = f'{(reg_addr // 0xFF):08b}'  # reg addr high
    word9 = f'{data:08b}'  # data to write

    # Parity check
    bitsToCheck = [word4, word5, word6, word7, word8, word9]
    parity = parity_gen(bitsToCheck)
    # print("parity: ")
    # print(parity)
    word10 = f'{parity:08b}'  # parity

    word11 = f'{0x7E:08b}'  # frame delimiter

    # Everything except frame delimiters so bitstuffing can be done
    wordsToStuff = word2[::-1] + \
                   word3[::-1] + \
                   word4[::-1] + \
                   word5[::-1] + \
                   word6[::-1] + \
                   word7[::-1] + \
                   word8[::-1] + \
                   word9[::-1] + \
                   word10[::-1]
    # Add a 0 anytime five 1s appear consecutively
    words2to10 = wordsToStuff.replace('11111', '111110')

    wordBlock = word1[::-1] + \
                words2to10 + \
                word11[::-1]
    #
    lpgbtControlBits = dpWriteAddress[::-1] + \
                       wordCount[::-1] + \
                       downlinkSignalOperation[::-1] + \
                       playOutFlag[::-1] + \
                       playCount[::-1] + \
                       wordBlock

    dataBitsToSend = lpgbtControlBits.ljust(280, '1')

    new_dataBitsToSend = []
    for num in range(35):
        new_dataBitsToSend.append(dataBitsToSend[0 + num * 8:8 + num * 8][::-1])
        # print(num,"\t",dataBitsToSend[0+num*8:8+num*8][::-1]) #correct
    dataBitsToSend = "".join(new_dataBitsToSend)

    status.sendFifoAOperation(operation=1, counter=35, address=7)
    serialMod.writeToChip(GUI, port, dataBitsToSend)
    status.sendStartControlOperation(operation=1, address=7)
    status.send()


def LpGBT_IC_REGRD(GUI, port, reg_addr):
    # read I2C register

    status = getattr(GUI, "status" + port)
    status.send()

    dpWriteAddress = '000000000001'  # 12
    wordCount = f'{80:08b}'  # 8
    downlinkSignalOperation = '11'  # 2
    playOutFlag = '1'  # 1
    playCount = '00001'  # 5
    # overhead = 28
    word1 = f'{int(0x7E):08b}'  # frame delimiter
    word2 = f'{int(0x00):08b}'  # reserved
    word3 = f'{int(0xE1):08b}'  # I2C address of LpGBT
    word4 = f'{int(0x01):08b}'  # command
    word5 = f'{int(0x01):08b}'  # number words
    word6 = f'{int(0x00):08b}'
    word7 = f'{(reg_addr & 0xFF):08b}'  # reg addr low
    word8 = f'{(reg_addr // 0xFF):08b}'  # reg addr high
    # word9 = #NO DATA TO WRITE

    # Parity check
    bitsToCheck = [word4, word5, word6, word7, word8]
    parity = parity_gen(bitsToCheck)
    print("parity: ")
    print(parity)

    word10 = f'{parity:08b}'  # parity
    word11 = f'{int(0x7E):08b}'  # frame delimiter

    # Everything except frame delimiters so bitstuffing can be done
    wordsToStuff = word2[::-1] + \
                   word3[::-1] + \
                   word4[::-1] + \
                   word5[::-1] + \
                   word6[::-1] + \
                   word7[::-1] + \
                   word8[::-1] + \
                   word10[::-1]
    # Add a 0 anytime five 1s appear consecutively
    words2to10 = wordsToStuff.replace('11111', '111110')

    # reverse order of each 8 bit word
    wordBlock = word1[::-1] + \
                words2to10 + \
                word11[::-1]

    # combine control bits
    lpgbtControlBits = dpWriteAddress[::-1] + \
                       wordCount[::-1] + \
                       downlinkSignalOperation[::-1] + \
                       playOutFlag[::-1] + \
                       playCount[::-1] + \
                       wordBlock

    dataBitsToSend = lpgbtControlBits.ljust(280, '1')

    print(dataBitsToSend)
    new_dataBitsToSend = []
    for num in range(35):
        new_dataBitsToSend.append(dataBitsToSend[0 + num * 8:8 + num * 8][::-1])
        # print(num, "\t", dataBitsToSend[0 + num * 8:8 + num * 8][::-1])  # correct
    dataBitsToSend = "".join(new_dataBitsToSend)

    status.sendFifoAOperation(operation=1, counter=35, address=7)
    serialMod.writeToChip(GUI, 'In', dataBitsToSend)
    status.sendStartControlOperation(operation=1, address=7)
    status.send()


#######################################################################
# Functions for communicating via I2C

def i2cWrite(chip, section):
    pass


def i2cReadLpGBT(GUI,
                 port,
                 i2cWR='010',
                 NSTP='0',
                 i2cRD='100',
                 STP='1',
                 lpgbtAddress='1110000',
                 wrBit='0',
                 rdBit='1',
                 lpgbtRegAddress=0x020):

    # if lpgbtRegAddress == -1:
    #     try:
    #         lpgbtRegAddress = int(GUI.controlLpGBTRegisterAddressBox.toPlainText())
    #     except Exception:
    #         GUI.showError('LpGBT: Invalid register address')
    #         return '00'
    lpgbtRegAddressStr = '{0:016b}'.format(lpgbtRegAddress)
    WB_terminator = '0'*8
    WB_dataBits = '0'*8
    WB_5 = lpgbtAddress+rdBit
    WB_4 = i2cRD+STP+'0010'
    WB_3 = lpgbtRegAddressStr[0:8]  # [15:8] in testbench, i.e. MSBs
    WB_2 = lpgbtRegAddressStr[8:16]  # [7:0] in testbench, i.e. LSBs
    WB_1 = lpgbtAddress+wrBit
    WB_0 = i2cWR+NSTP+'0011'

    bitsToSend = WB_0+WB_1+WB_2+WB_3+WB_4+WB_5+WB_dataBits+WB_terminator
    bitsReverse = [bitsToSend[i:i+8] for i in range(0, len(bitsToSend), 8)][::-1]
    bitsToSend = ''.join(bitsReverse)

    nBits = len(bitsToSend)
    nByte = int(nBits/8)  # should be 8
    GUI.status.send()
    serialMod.flushBuffer(GUI, port)
    GUI.status.sendFifoAOperation(1, nByte, 0)
    serialResult = serialMod.writeToChip(GUI, 'A', bitsToSend)
    GUI.status.sendI2Ccommand()
    GUI.status.send()

    nWordsExpected = 1
    # Read the I2C ouput
    serialMod.flushBuffer(GUI, port)
    GUI.status.sendFifoAOperation(2, nWordsExpected, 0)
    time.sleep(0.01)  # Wait for the buffer to fill
    i2cOutput = serialMod.readFromChip(GUI, 'A', 8)  # Need to think about nBytes argument for readFromChip()
    # Read the relevant bytes
    if type(i2cOutput) is not bool:
        # i2cOutput = i2cOutput[:8]
        i2cOutput = i2cOutput[:1]
    else:
        i2cOutput = bytearray(0)
    GUI.status.send()
    # Convert the bytes into bits and turn into a string
    # return byteArrayToString(i2cOutput)
    return ["{:02x}".format(x) for x in i2cOutput]


def i2cWriteLpGBT(GUI,
                  i2cWR='010',
                  STP='1',
                  lpgbtAddress='1110000',
                  wrBit='0',
                  lpgbtRegAddress=-1,
                  dataWord='11001000'):

    # if lpgbtRegAddress == -1:
    #     try:
    #         lpgbtRegAddress = int(GUI.controlLpGBTRegisterAddressBox.toPlainText())
    #         dataWord = GUI.controlLpGBTRegisterValueBox.toPlainText()
    #     except Exception:
    #         GUI.showError('LpGBT: Invalid register address')
    #         return '00'
    if len(dataWord) == 0 or len(dataWord) > 8:
        GUI.showError('LpGBT: Setting overflow! Max value 8 bits')
        return False

    lpgbtRegAddressStr = '{0:016b}'.format(lpgbtRegAddress)
    wbTerminator = '0' * 8
    dataBits = dataWord
    wbByte3 = lpgbtRegAddressStr[0:8]  # [15:8] in testbench, i.e. MSBs
    wbByte2 = lpgbtRegAddressStr[8:16]  # [7:0] in testbench, i.e. LSBs
    wbByte1 = lpgbtAddress + wrBit
    wbByte0 = i2cWR + STP + '0100'

    bitsToSend = wbTerminator + dataBits + wbByte3 + wbByte2 + wbByte1 + wbByte0
    nByte = int(len(bitsToSend) / 8)  # should be 6
    GUI.status.send()
    GUI.status.sendFifoAOperation(1, nByte, 0)
    serialResult = serialMod.writeToChip(GUI, 'A', bitsToSend)
    GUI.status.sendI2Ccommand()

    return serialResult
