import time
import serialMod

def i2cWrite(chip, section):
    pass


def i2cReadLpGBT(GUI,
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
    serialMod.flushBuffer(GUI)
    GUI.status.sendFifoAOperation(1, nByte, 0)
    serialResult = serialMod.writeToChip(GUI, 'A', bitsToSend)
    GUI.status.sendI2Ccommand()
    GUI.status.send()

    nWordsExpected = 1
    # Read the I2C ouput
    serialMod.flushBuffer(GUI)
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
