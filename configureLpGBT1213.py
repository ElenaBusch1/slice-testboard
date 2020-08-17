import serial, time
import serial.tools.list_ports as LP
import sys
from platform import system

def findPort():
    manufacturer = 'Devantech Ltd.'
    description = 'USB_ISS_'
    platform = system()
    device = None
    if platform == 'Windows':
        ports = LP.comports()
        if ports is None:
            print('No USB found for clock chip')
            sys.exit(1)

    elif platform == 'Darwin' or platform == 'Linux':
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
    print('{0} ->{1}'.format(port.name, outputString))
    return outputString


def u16_to_bytes(val):
    byte1 = (val >> 8) & 0xff
    byte0 = (val >> 0) & 0xff
    return byte1, byte0


def configureLpGBT(port, lpgbtAddr, regAddr, data):
    """Configure the lpGBT via the USB-ISS Module using its I2C interface"""
    addrW = (lpgbtAddr << 1) | 0 # for writing
    addrR = (lpgbtAddr << 1) | 1 # for reading

    # Assemble i2c command and send it to USB-ISS module
    regAddrHigh, regAddrLow = u16_to_bytes(regAddr)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, len(data), *data]
    writeToUSBISS(port, writeMessage)

    # Do an i2c read of just written registers
    writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, len(data)]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

def fuseLpGBT(port, lpgbtAddr, regAddr, data):
    """Blow the lpGBT E-Fuses"""
    addrW = (lpgbtAddr << 1) | 0 # for writing
    addrR = (lpgbtAddr << 1) | 1 # for reading

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
    regAddrHigh, regAddrLow = u16_to_bytes(FuseMagic)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xa3]
    writeToUSBISS(port, writeMessage)

    # 2. Set FuseBlowPulseLength to 12
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    writeToUSBISS(port, writeMessage)

    # 3. Load the internal address of the first register in the 4 register block
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowAddH)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x02, *u16_to_bytes(regAddr)]
    writeToUSBISS(port, writeMessage)

    # 4. Load 4 bytes to be written
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowDataA)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, len(data), *data]
    writeToUSBISS(port, writeMessage)

    # 5. Wait for VDDF2V5 to be on
    input("Press enter once VDDF2V5 is on...\n")

    # 6. Assert FuseBlow to initiate fuse blowing sequence
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc1]
    writeToUSBISS(port, writeMessage)

    # 7. Read FUSEStatus until FuseBlowDone bit is set
    timeout = time.time() + 5
    while True:
        regAddrHigh, regAddrLow = u16_to_bytes(FUSEStatus)
        writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, 0x01]
        writeToUSBISS(port, writeMessage)
        status = readFromUSBISS(port)

        if status == '02':
            break

        if time.time() > timeout:
            break

    # 8. Wait for VDDF2V5 to be off
    input("Press enter once VDDF2V5 if off...\n")

    # 9. Deassert FuseBlow
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    writeToUSBISS(port, writeMessage)

    print("!!!Reading E-Fuses!!!")

    # 1. Assert FuseRead
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc2]
    writeToUSBISS(port, writeMessage)

    # 2. Read FUSEStatus until FuseDataValid is set
    timeout = time.time() + 5
    while True:
        regAddrHigh, regAddrLow = u16_to_bytes(FUSEStatus)
        writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, 0x01]
        writeToUSBISS(port, writeMessage)
        status = readFromUSBISS(port)

        if status == '04':
            break

        if time.time() > timeout:
            break

    # 3. Load address of first register in block to read
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEBlowAddH)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x02, *u16_to_bytes(regAddr)]
    writeToUSBISS(port, writeMessage)

    # 4. Read values from currently selected 4-byte fuse block
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEValuesA)
    writeMessage = [0x56, addrR, regAddrHigh, regAddrLow, len(data)]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # 5. Deassert FuseRead
    regAddrHigh, regAddrLow = u16_to_bytes(FUSEControl)
    writeMessage = [0x56, addrW, regAddrHigh, regAddrLow, 0x01, 0xc0]
    writeToUSBISS(port, writeMessage)


def main():

    lpgbtAddr = 0b1110010

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
    writeMessage = [0x5a, 0x02, 0x71, 0x00, 0x9B]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Register addresses and data to be fused
    regAddr  = [0x01c, 0x020, 0x024, 0x028, 0x02c, 0x030, 0x034, 0x038, 0x06c, 0x070, 0x0ec]
    regDataA = [ 0x00,  0xc8,  0x55,  0x05,  0x88,  0x0a,  0x00,  0x00,  0x1c,  0x1b,  0x00]
    regDataB = [ 0x00,  0x38,  0x55,  0x1b,  0x89,  0x0a,  0x00,  0x20,  0x00,  0x00,  0x00]
    regDataC = [ 0x00,  0x44,  0x55,  0x00,  0x99,  0x0a,  0x00,  0x00,  0x1a,  0x19,  0x00]
    regDataD = [ 0x55,  0x55,  0x55,  0x00,  0x0a,  0x00,  0x00,  0x00,  0x00,  0x00,  0x06]

    for i in range(len(regAddr)):

        configureLpGBT(port, lpgbtAddr, regAddr[i], [regDataA[i], regDataB[i], regDataC[i], regDataD[i]])

        # while False:
        #     fuseLpGBT(port, lpgbtAddr, regAddr[i], [regDataA[i], regDataB[i], regDataC[i], regDataD[i]])

