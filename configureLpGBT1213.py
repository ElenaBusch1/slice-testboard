import serial
import time
import serial.tools.list_ports as LP
import sys
import argparse
from platform import system


def findPort():
    manufacturer = 'Devantech Ltd.'
    description = 'USB_ISS_'
    platform = system()
    device = None
    if platform == 'Windows' or platform == 'Linux':
        ports = LP.comports()
        if ports is None:
            print('No USB found for clock chip')
            sys.exit(1)

    elif platform == 'Darwin': # or platform == 'Linux':
        ports = LP.grep(description)
        if ports is None:
            print('No USB found for clock chip')
            sys.exit(1)

    else:
        print(f"{platform} not supported, exiting... ")
        sys.exit(1)

    for port in ports:
        if port is None: continue
        if port.manufacturer == 'FTDI': continue
        if port.manufacturer == manufacturer:
            device = port.device

    if device is None:
        print('No USB found')
        sys.exit(1)

    return device


def setupSerial(port, baudrate=9600, parity='N', stopbits=1, timeout=2, bytesize=8):
    port = serial.Serial(port=port,
                         baudrate=baudrate,
                         parity=parity,
                         stopbits=stopbits,
                         timeout=timeout,
                         bytesize=bytesize)

    return port


def writeToUSBISS(port, message):
    # hexMessage = [int(m, 16) for m in message]
    # BAMessage = bytearray(hexMessage)
    BAMessage = bytearray(message)
    inputString = byteArrayToHex(BAMessage)
    print('{0} <- {1}'.format(port.name, inputString))
    port.write(BAMessage)
    return True


def closePort(port):
    port.close()


def byteArrayToString(inputByteArray):
    """Convert raw data readout to a python string object."""
    # outputString = ''
    # for byte in inputByteArray:
    #     outputString += '{0:08b}'.format(byte)
    outputString = ' '.join([f"{byte:08b}" for byte in inputByteArray])
    return outputString


def byteArrayToHex(inputByteArray):
    # outputString = ''
    # for byte in inputByteArray:
    #     outputString += ' {0:02x}'.format(byte)
    outputString = ' '.join([f"{byte:02x}" for byte in inputByteArray])
    return outputString


def readFromUSBISS(port):
    outputarray = bytearray()
    time.sleep(0.5)
    while len(outputarray) < port.in_waiting:
        output = port.read(port.in_waiting)
        for b in output:
            outputarray.append(b)
    outputString = byteArrayToHex(outputarray)
    print('{0} -> {1}'.format(port.name, outputString))
    # return outputString
    return [int(outputByte) for outputByte in outputarray]


def u16_to_bytes(val):
    byte1 = (val >> 8) & 0xff
    byte0 = (val >> 0) & 0xff
    return byte1, byte0


def writeToLpGBT(port, lpgbtAddr, regAddr, data):
    """Write to lpGBT via USB-ISS i2c interface"""
    addrW = (lpgbtAddr << 1) | 0  # for writing

    regAddrHigh, regAddrLow = u16_to_bytes(regAddr)

    timeout = time.time() + 5
    while True:
        writeMessage = [0x57, 0x01, 0x30 + (2 + len(data)), addrW, regAddrLow, regAddrHigh, *data, 0x03]
        #print(writeMessage)
        writeToUSBISS(port, writeMessage)
        status = readFromUSBISS(port)
        if status[0] == 0xff:
            return True
        if time.time() > timeout:
            break

    return False


def readFromLpGBT(port, lpgbtAddr, regAddr, nBytesToRead):
    """Read from lpGBT via USB-ISS i2c interface"""
    addrW = (lpgbtAddr << 1) | 0  # for writing
    addrR = (lpgbtAddr << 1) | 1  # for reading

    regAddrHigh, regAddrLow = u16_to_bytes(regAddr)

    timeout = time.time() + 5
    while True:
        if nBytesToRead > 1:
            writeMessage = [0x57, 0x01, 0x32, addrW, regAddrLow, regAddrHigh, 0x02, 0x30, addrR, 0x20 + (nBytesToRead - 2), 0x04, 0x20, 0x03]
        else:
            writeMessage = [0x57, 0x01, 0x32, addrW, regAddrLow, regAddrHigh, 0x02, 0x30, addrR, 0x04, 0x20, 0x03]
        writeToUSBISS(port, writeMessage)
        status = readFromUSBISS(port)
        if status[0] == 0xff:
            return status[2:]
        if time.time() > timeout:
            break

    return []

def colutaRegWriteTest(port, lpgbtAddr):
    while True:
        #wr 0x0f9 20  SCl, 8 bytes, 200kHz
        writeToLpGBT(port, lpgbtAddr, 0x0f9, [0x20])
        #wr 0x0fd 0   write control register command
        writeToLpGBT(port, lpgbtAddr, 0x0fd, [0x0])

        #wr 0x0f9 1
        writeToLpGBT(port, lpgbtAddr, 0x0f9, [0x1])
        #wr 0x0fa 2
        writeToLpGBT(port, lpgbtAddr, 0x0fa, [0x2])
        #wr 0x0fb 3
        writeToLpGBT(port, lpgbtAddr, 0x0fb, [0x3])
        #wr 0x0fc 4
        writeToLpGBT(port, lpgbtAddr, 0x0fc, [0x4])
        #wr 0x0fd 8   get 4 bytes command
        writeToLpGBT(port, lpgbtAddr, 0x0fd, [0x8])

        #wr 0x0f9 5
        writeToLpGBT(port, lpgbtAddr, 0x0f9, [0x5])
        #wr 0x0fa 6
        writeToLpGBT(port, lpgbtAddr, 0x0fa, [0x6])
        #wr 0x0fb 7
        writeToLpGBT(port, lpgbtAddr, 0x0fb, [0x7])
        #wr 0x0fc 8
        writeToLpGBT(port, lpgbtAddr, 0x0fc, [0x8])
        #wr 0x0fd 9  get 4 bytes command
        writeToLpGBT(port, lpgbtAddr, 0x0fd, [0x9])

        #wr 0x0f8 50  7 bits of address
        writeToLpGBT(port, lpgbtAddr, 0x0f8, [0x40])
        #wr 0x0f7 07  3 bits of address
        writeToLpGBT(port, lpgbtAddr, 0x0f7, [0x00])
        #wr 0x0fd 0E  10bit address write command
        writeToLpGBT(port, lpgbtAddr, 0x0fd, [0xE])
    return

def uplinkDataTest(port, lpgbtAddr):

    #0x118 is the EC data pattern -> do we need this?
    #For lpgbt 14   
    # writeToLpGBT(port, lpgbtAddr, 0x12d, [0xff])
    # writeToLpGBT(port, lpgbtAddr, 0x118, [0x01])
    # writeToLpGBT(port, lpgbtAddr, 0x119, [0x09])
    # writeToLpGBT(port, lpgbtAddr, 0x11a, [0x09])
    # writeToLpGBT(port, lpgbtAddr, 0x11b, [0x09])
    # writeToLpGBT(port, lpgbtAddr, 0x11c, [0x01])
    # writeToLpGBT(port, lpgbtAddr, 0x119, [0xaa])

    # For lpgbt 12/13
    writeToLpGBT(port, lpgbtAddr, 0x118, [0x0C]) #011 00 000 
    writeToLpGBT(port, lpgbtAddr, 0x119, [0x24]) #00 011 011
    writeToLpGBT(port, lpgbtAddr, 0x11a, [0x24]) #00 011 011
    writeToLpGBT(port, lpgbtAddr, 0x11b, [0x24]) #00 011 011
    writeToLpGBT(port, lpgbtAddr, 0x11c, [0x04]) #00 000 011
    writeToLpGBT(port, lpgbtAddr, 0x11d, [0xFF])

    writeToLpGBT(port, lpgbtAddr, 0x11e, [0xaa])
    writeToLpGBT(port, lpgbtAddr, 0x11f, [0x55])
    writeToLpGBT(port, lpgbtAddr, 0x120, [0xaa])
    writeToLpGBT(port, lpgbtAddr, 0x121, [0x55])

    #to write consecutively
    #writeToLpGBT(port, lpgbtAddr, 0x118, [0x0c, 0x24, 0x24, 0x24, 0x04, 0xff])
    # writeToLpGBT(port, lpgbtAddr, 0x118, [0x08, 0x12, 0x12, 0x12, 0x02, 0xff])
    #writeToLpGBT(port, lpgbtAddr, 0x11e, [0xaa, 0xaa, 0xaa, 0xaa])
    #writeToLpGBT(port, lpgbtAddr, 0x132, [0x02])
    #readFromLpGBT(port, lpgbtAddr, 0x118, 10)
    #readFromLpGBT(port, lpgbtAddr, 0x132, 1)


'''
def configureLpGBT(port, lpgbtAddr, regAddr, data):
    """Configure the lpGBT via the USB-ISS Module using its I2C interface"""
    addrW = (lpgbtAddr << 1) | 0  # for writing
    addrR = (lpgbtAddr << 1) | 1  # for reading

    # Assemble i2c command and send it to USB-ISS module
    regAddrHigh, regAddrLow = u16_to_bytes(regAddr)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, len(data), *data]
    writeMessage = [0x57, 0x01, 0x30 + (2 + len(data)), addrW, regAddrLow, regAddrHigh, *data, 0x03]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Do an i2c read of just written registers
    # writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, len(data)]
    # writeMessage = [0x57, 0x01, 0x32, addrW, regAddrLow, regAddrHigh, 0x02, 0x30, addrR, 0x20 + (len(data) - 1), 0x03]
    # writeToUSBISS(port, writeMessage)
    # readFromUSBISS(port)

    # timeout = time.time() + 5
    # while True:
    #     # writeMessage = [0x57, 0x01, 0x30 + (2 + len(data)), addrW, regAddrLow, regAddrHigh, *data, 0x03]
    #     # writeToUSBISS(port, writeMessage)
    #     # readFromUSBISS(port)

    #     # writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, len(data)]
    #     writeMessage = [0x57, 0x01, 0x32, addrW, regAddrLow, regAddrHigh, 0x02, 0x30, addrR, 0x20 + (len(data) - 1), 0x03]
    #     writeToUSBISS(port, writeMessage)
    #     status = readFromUSBISS(port)

    #     if status[0] == 0xff:
    #         if status[2:] == data:
    #             return True

    #     if time.time() > timeout:
    #         break
    # return False
'''
def configureLpGBT(port, lpgbtAddr, regAddr, data):
    print('Writing to ', hex(regAddr))
    writeStatus = writeToLpGBT(port, lpgbtAddr, regAddr, data)
    if not writeStatus: 
        print("Failed to write to lpGBT")
        return False
    else:
        # while True:
        #     time.sleep(0.5) 
        readBack = readFromLpGBT(port, lpgbtAddr, regAddr, len(data))

    if readBack == data:
        print("Successfully readback what was written!")
        return True
    else: 
        print("Readback does not agree with what was written")
        return False


def fuseLpGBT(port, lpgbtAddr, regAddr, data):
    """Blow the lpGBT E-Fuses"""
    addrW = (lpgbtAddr << 1) | 0  # for writing
    addrR = (lpgbtAddr << 1) | 1  # for reading

    # Read/Write Registers
    FUSEControl   = 0x109
    FUSEBlowDataA = 0x10a
    FUSEBlowDataB = 0x10b
    FUSEBlowDataC = 0x10c
    FUSEBlowDataD = 0x10d
    FUSEBlowAddH  = 0x10e
    FUSEBlowAddL  = 0x10f
    FuseMagic     = 0x110

    # Read Only Registers
    FUSEStatus  = 0x1a1
    FUSEValuesA = 0x1a2
    FUSEValuesB = 0x1a3
    FUSEValuesC = 0x1a4
    FUSEValuesD = 0x1a5

    if regAddr % 4 != 0:
        raise Exception(f"Incorrect address for burn bank! (address = {regAddr:03x}")

    print("!!!Writing E-Fuses!!!")

    # 1. Write magic number
    # regAddrHigh, regAddrLow = u16_to_bytes(FuseMagic)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xa3]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FuseMagic, [0xa3])

    # 2. Set FuseBlowPulseLength to 12
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEControl, [0xc0])

    # 3. Load the internal address of the first register in the 4 register block
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowAddH)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x02, *u16_to_bytes(regAddr)]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEBlowAddH, u16_to_bytes(regAddr))

    # 4. Load 4 bytes to be written
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowDataA)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, len(data), *data]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEBlowDataA, data)

    # 5. Wait for VDDF2V5 to be on
    input("Press enter once VDDF2V5 is on...\n")

    # 6. Assert FuseBlow to initiate fuse blowing sequence
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc1]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEControl, [0xc1])

    # 7. Read FUSEStatus until FuseBlowDone bit is set
    timeout = time.time() + 5
    while True:
        # regAddrHigh, regAddrLow = u16_to_bytes(FUSEStatus)
        # writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, 0x01]
        # writeToUSBISS(port, writeMessage)
        # status = readFromUSBISS(port)

        readback = readFromLpGBT(port, lpgbtAddr, FUSEStatus, 1)
        print(readback)

        if readback[0] == 0x02:
            break

        if time.time() > timeout:
            break

    # 8. Wait for VDDF2V5 to be off
    input("Press enter once VDDF2V5 if off...\n")

    # 9. Deassert FuseBlow
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEControl, [0xc0])

    print("!!!Reading E-Fuses!!!")

    # 1. Assert FuseRead
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc2]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEControl, [0xc2])

    # 2. Read FUSEStatus until FuseDataValid is set
    timeout = time.time() + 5
    while True:
        # regAddrHigh, regAddrLow = u16_to_bytes(FUSEStatus)
        # writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, 0x01]
        # writeToUSBISS(port, writeMessage)
        # status = readFromUSBISS(port)

        readback = readFromLpGBT(port, lpgbtAddr, FUSEStatus, 1)
        print(readback)

        if readback[0] == 0x04:
            break

        if time.time() > timeout:
            break

    # 3. Load address of first register in block to read
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowAddH)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x02, *u16_to_bytes(regAddr)]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEBlowAddH, u16_to_bytes(regAddr))

    # 4. Read values from currently selected 4-byte fuse block
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEValuesA)
    # writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, len(data)]
    # writeToUSBISS(port, writeMessage)
    # readFromUSBISS(port)
    readFromLpGBT(port, lpgbtAddr, FUSEValuesA, len(data))

    # 5. Deassert FuseRead
    # regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    # writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    # writeToUSBISS(port, writeMessage)
    writeToLpGBT(port, lpgbtAddr, FUSEControl, [0xc0])


def main(pArgs):

    if pArgs.lpgbtNum == 12:
        lpgbtAddr = 0b1110010
    elif pArgs.lpgbtNum == 13:
        lpgbtAddr = 0b1110011
    else:
        print("No valid control lpGBT specified, exiting...")
        sys.exit(0)

    # Connect to USB-ISS Module
    portFound = findPort()
    port = setupSerial(portFound)

    # Initialize USB-ISS Module
    writeMessage = [0x5a, 0x01]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    writeMessage = [0x5a, 0x03]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Is this mode correct? Is the baudrate correct?
    # writeMessage = [ISS_CMD, ISS_MODE, I2C_MODE+SERIAL, baudrate divisor (h), baudrate divisor (l)]
    # writeMessage = [0x5a, 0x02, 0x60, 0x00, 0x9B]
    # writeMessage = [0x5a, 0x02, 0x60, 0x01, 0x37]
    # writeMessage = [0x5a, 0x02, 0x40, 0x00, 0x9B]
    writeMessage = [0x5a, 0x02, 0x40, 0x01, 0x37]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Check for existence of device with giben i2c address
    writeMessage = [0x58, lpgbtAddr << 1]
    # # writeMessage = [0x58, 0xd0]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Register addresses and data to be fused
    # regAddr  = [0x01c, 0x020, 0x024, 0x028, 0x02c, 0x030, 0x034, 0x038, 0x06c, 0x070, 0x0ec]
    # regDataA = [ 0x00,  0xc8,  0x55,  0x05,  0x88,  0x0a,  0x00,  0x00,  0x1c,  0x1b,  0x00]
    # regDataB = [ 0x00,  0x38,  0x55,  0x1b,  0x89,  0x0a,  0x00,  0x20,  0x00,  0x00,  0x00]
    # regDataC = [ 0x00,  0x44,  0x55,  0x00,  0x99,  0x0a,  0x00,  0x00,  0x1a,  0x19,  0x00]
    # regDataD = [ 0x55,  0x55,  0x55,  0x00,  0x0a,  0x00,  0x00,  0x00,  0x00,  0x00,  0x07]
  
    # regAddr  = [0x01c, 0x020, 0x024, 0x028, 0x02c, 0x030, 0x034, 0x038, 0x0ec] # 0x06c, 0x07c, 0x080, 0x084, 0x088, 0x08c, 0x090, 0x094, 0x09c, 0x0ec]
    # regDataA = [ 0x00,  0xc8,  0x55,  0x05,  0x88,  0x0a,  0x00,  0x00,  0x00] # 0x19,  0x19,  0x19,  0x00,  0x19,  0x19,  0x19,  0x19,  0x19,  0x00]
    # regDataB = [ 0x00,  0x38,  0x55,  0x1b,  0x89,  0x0a,  0x00,  0x20,  0x00] # 0x73,  0x73,  0x73,  0x00,  0x73,  0x73,  0x73,  0x73,  0x73,  0x00]
    # regDataC = [ 0x00,  0x44,  0x55,  0x00,  0x99,  0x0a,  0x00,  0x00,  0x00] # 0x00,  0x19,  0x00,  0x19,  0x19,  0x19,  0x00,  0x00,  0x00,  0x00]
    # regDataD = [ 0x55,  0x55,  0x55,  0x00,  0x0a,  0x00,  0x00,  0x00,  0x07] # 0x00,  0x73,  0x00,  0x73,  0x73,  0x73,  0x00,  0x00,  0x00,  0x07]

    #clocks
    regAddr  = [0x06c, 0x07c, 0x080, 0x084, 0x088, 0x08c, 0x090, 0x094, 0x09c, 0x0ec]
    regDataA = [0x19,  0x19,  0x19,  0x00,  0x19,  0x19,  0x19,  0x19,  0x19,  0x00]
    regDataB = [0x73,  0x73,  0x73,  0x00,  0x73,  0x73,  0x73,  0x73,  0x73,  0x00]
    regDataC = [0x00,  0x19,  0x00,  0x19,  0x19,  0x19,  0x00,  0x00,  0x00,  0x00]
    regDataD = [0x00,  0x73,  0x00,  0x73,  0x73,  0x73,  0x00,  0x00,  0x00,  0x07]


    #turn off parity
    print("Checking Parity")
    writeToLpGBT(port, lpgbtAddr, 0x03c, [0x01])
    readFromLpGBT(port, lpgbtAddr, 0x03c, 1)
    #writeToLpGBT(port, lpgbtAddr, 0x07c, [0x19, 0x73])
    #readFromLpGBT(port, lpgbtAddr, 0x0c0, 16)
    #readFromLpGBT(port, lpgbtAddr, 0x0cc, 1) 
    #writeToLpGBT(port, lpgbtAddr, 0x118, [0x00])
    #writeToLpGBT(port, lpgbtAddr, 0x121, [0x01])
    print("Reading 0x118")
    readFromLpGBT(port,lpgbtAddr,0x118, 6)

    #readFromLpGBT(port, lpgbtAddr, 0x0c4, 6)
    #print("Start1")
    #writeToLpGBT(port, lpgbtAddr, 0x12c, [0x00])
    #readFromLpGBT(port, lpgbtAddr, 0x12c, 1)
    #print("Start2")
    #writeToLpGBT(port, lpgbtAddr, 0x12c, [0x07])
    #readFromLpGBT(port, lpgbtAddr, 0x12c, 1)
    #time.sleep(0.1)
    #print("Start3")
    #writeToLpGBT(port, lpgbtAddr, 0x12c, [0x00])
    #readFromLpGBT(port, lpgbtAddr, 0x12c, 1)

    #for i in range(0x3D,0xF0,16):
    #    print('reading', hex(i))
    #    readFromLpGBT(port, lpgbtAddr, i, 16)
    #    time.sleep(0.1)


    uplinkDataTest(port, lpgbtAddr)

    ### Read back full 240 registers ###
    #for reg in range(0, 0x13c, 16):
    #    print(f"Beginning read at {reg:03x}")
    #    readFromLpGBT(port, lpgbtAddr, reg, 16)

    

    if pArgs.configure:
        #writeToLpGBT(port, lpgbtAddr, 0x12c, [0x07])
        #writeToLpGBT(port, lpgbtAddr, 0x12c, [0x00])
        # configureLpGBT(port, lpgbtAddr, 0x052, [0b00001000, 0b00010100])
        # configureLpGBT(port, lpgbtAddr, 0x054, [0b00001000, 0b00010100])
        # configureLpGBT(port, lpgbtAddr, 0x05a, [0b00001000, 0b00010100])
        #while True:
            #     configureLpGBT(port, lpgbtAddr, 0x06c, [0x19])
            #     configureLpGBT(port, lpgbtAddr, 0x07c, [0x19])
            #     configureLpGBT(port, lpgbtAddr, 0x07d, [0x73])
            #configureLpGBT(port, lpgbtAddr, 0x028, [0x05])
        # configureLpGBT(port, lpgbtAddr, 0x039, [0x20])
        #writeToLpGBT(port, lpgbtAddr, 0x024, [0x55])
        #while True:
        #    readFromLpGBT(port, lpgbtAddr, 0x024, 1)
        # while False:
         
        # print("Configuring lpGBT...")
        # for i in range(len(regAddr)):
        #     success = False
        #     counter = 0
        #     while not success and counter < 4:
        #         success = configureLpGBT(port, lpgbtAddr, regAddr[i], [regDataA[i], regDataB[i], regDataC[i], regDataD[i]])
        #         counter += 1

               
        # print("Configuring lpGBT...")
        # # # while True:
        # for i in range(len(regAddr)):
        #     configureLpGBT(port, lpgbtAddr, regAddr[i], [regDataA[i]])
        #     configureLpGBT(port, lpgbtAddr, regAddr[i]+1, [regDataB[i]])
        #     configureLpGBT(port, lpgbtAddr, regAddr[i]+2, [regDataC[i]])
        #     configureLpGBT(port, lpgbtAddr, regAddr[i]+3, [regDataD[i]])

        readFromLpGBT(port, lpgbtAddr, 0x1c7, 1)            
        
    elif pArgs.fuse:
        if input("Continue to blowing E-Fuses? (y/n) ") != 'y':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Beginning blowing E-Fuses")
            for i in range(len(regAddr)):
                fuseLpGBT(port, lpgbtAddr, regAddr[i], [regDataA[i], regDataB[i], regDataC[i], regDataD[i]])

    else:
        print("No action specified, exiting...")
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script for configuring the lpGBT and "
                                                 "blowing its E-Fuses via USB-ISS Module")
    parser.add_argument('lpgbtNum', metavar="lpGBT Number", type=int,
                        help='Which control lpGBT to configure (must be 12 or 13)')
    parser.add_argument('-c', '--configure', action='store_true', help='Configure the lpGBT via i2c.')
    parser.add_argument('-f', '--fuse', action='store_true', help='Blow the E-Fuses on the lpGBT.')
    args = parser.parse_args()

    main(args)
