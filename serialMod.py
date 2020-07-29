import serial
import serial.tools.list_ports as LP
from platform import system
import time
from PyQt5 import QtCore

def findPorts(GUI):
    """Finds the locations of the USB chip in a platform-independent way."""
    # Check which system is being used, and pass it to Qt
    platform = system()
    GUI.platform = platform
    # Description is something like 'SLICEBOARDAB' (for version 1 chip)
    description = GUI.description
    # We will create a list of ftdi devices, which are obtained in a different way
    # for each platform
    ftdiDevices = []
    if platform == 'Windows':
        ports = LP.comports()
        # If no ports found, then show the error and exit the script
        if ports is None:
            print('No ports found, exiting...')
            QtCore.QCoreApplication.instance().quit()
        # Windows sees the USB as a Serial COM port, so PySerial cannot see the
        # description of the USB. However, the manufacturer is still 'FTDI', so
        # we can at least find these ports. The only case where this might fail
        # is when more than one FTDI device is hooked up to the same computer.
        # This is handled with an exception, and the GUI refuses to connect.
        # Finally the last number of the serial number is A or B, which is the
        # channel identifier.
        for port in ports:
            if port is None: continue
            device = port.device
            manufac = port.manufacturer
            if manufac is not None and manufac != 'FTDI': continue
            channel = port.serial_number[:3] # Serial number configured to be "AB#xxxxxx"
            ftdiDevices.append((channel,device))
            GUI.serial_number = port.serial_number
    elif platform == 'Darwin' or platform == 'Linux':
        # OS X and Linux see the description of the USB, so we can grep for the
        # ports that match. If the ports' names end in 'A' and 'B', we add them.
        # If they end in '0' and '1', we change them to 'A' and 'B', respectively.
        ports = LP.grep(description)
        # If no ports found, then show the error and exit the script
        if ports is None:
            print('No ports found, exiting...')
            QtCore.QCoreApplication.instance().quit()

        for port in ports:
            if port is None: continue
            device = port.device
            description = port.description
            channel = description[-3:] # Configure a channel name
            ftdiDevices.append((channel,device))
            GUI.serial_number = port.description
    else:
        # Chrome OS is not supported :(
        print('Unknown platform {}'.format(platform))
        QtCore.QCoreApplication.instance().quit()
    nDevice = len(ftdiDevices)
    deviceDict = dict(ftdiDevices)
    # Ensure that only up to 2 USB ports are added.
    if nDevice > 2:
        GUI.showError(f"{nDevice} USB ports found matching {description}")
    # Finally, return the names of the ports
    return deviceDict


def setupSerials(GUI):
    """Sets up Serial objects for the GUI."""
    try:
        serial1 = serial.Serial( port     = GUI.port1,
                                 baudrate = GUI.baudrate,
                                 parity   = GUI.parity,
                                 stopbits = GUI.stopbits,
                                 bytesize = GUI.bytesize,
                                 timeout  = GUI.timeout,
                                 write_timeout = GUI.timeout )

        serial2 = serial.Serial( port     = GUI.port2,
                                 baudrate = GUI.baudrate,
                                 parity   = GUI.parity,
                                 stopbits = GUI.stopbits,
                                 bytesize = GUI.bytesize,
                                 timeout  = GUI.timeout,
                                 write_timeout = GUI.timeout )

        return serial1, serial2
    except:
        GUI.showError('Unable to connect to chip.')
        return None, None


def checkSerials(GUI):
    """Check validity of serial connections"""
    # For UNIX platforms, is serial.serialposix.Serial
    # For Windows platforms, is serial.serialwin32.Serial
    pf = GUI.platform
    if pf=='Windows':
        serialType = serial.serialwin32
    elif pf=='Darwin' or pf=='Linux':
        serialType = serial.serialposix
    else:
        GUI.showError(f'Unknown platform {pf}')
        return False

    print(type(GUI.serial1), type(GUI.serial2))
    isPortConnected1 = isinstance(GUI.serial1, serialType.Serial)
    isPortConnected2 = isinstance(GUI.serial2, serialType.Serial)

    if not (isPortConnected1 and isPortConnected2):
        GUI.showError('SERIALMOD: Handshaking procedure failed. Not connected.')

    return isPortConnected1, isPortConnected2


def readFromChip(GUI, port, nBytes):
    """Reads bytes from the chip."""
    # Check that positive number of bytes requested.
    if nBytes <= 0:
        GUI.showError('SERIALMOD: Non-positive number of bytes requested.')

    # Get the serial object corresponding to the correct channel
    fifo = GUI.serial

    # Debug statements
    if fifo is None:
        if GUI.pArgs.no_connect:
            print(f'{port} -> DATA DATA DATA DATA')
            return True
        else:
            GUI.showError(f'SERIALMOD: Port {port} not connected.')
            return False

    # Create output array and reset the buffers
    outputArray = bytearray()

    if fifo.in_waiting == 0:
        print(f'{port} ->', [f"{x:02x}" for x in outputArray])
        return outputArray

    maxReadAttempts = 250
    nTries = 0
    while len(outputArray) < nBytes and nTries < maxReadAttempts:
        nTries += 1
        output = fifo.read(fifo.in_waiting)
        for b in output:
            outputArray.append(b)

    if GUI.pArgs.debug:
        print(f'{port} ->', [f"{x:02x}" for x in outputArray])

    return outputArray


def writeToChip(GUI, port, message):
    """Writes a given message into the given port."""
    # Check message type and convert if necessary
    if isinstance(message, bytearray):
        BAMessage = message
    elif isinstance(message, list) and len(message) > 0:
        if isinstance(message[0], int) and all([0 <= i <= 255 for i in message]):
            BAMessage = bytearray(message)
        else:
            GUI.showError('SERIALMOD: Message is not of a supported type.')
            return False
    elif isinstance(message, str) and len(message) > 0:
        BAMessage = bytearray(int(message, 2).to_bytes(len(message) // 8, byteorder='big'))
    else:
        GUI.showError('SERIALMOD: Message is not of a supported type.')
        return False

    # Get the serial object corresponding to the correct channel
    try:
        fifo = GUI.serial
    except AttributeError:
        fifo = None

    # Debug statements
    messageList = []
    for byteMessage in BAMessage:
        messageList.append(format(byteMessage, "02x"))
    if GUI.pArgs.debug:
        print('{} <-'.format(port), " ".join(messageList))

    if fifo is None:
        if GUI.pArgs.no_connect:
            return True
        else:
            GUI.showError('SERIALMOD: Port {} not connected.'.format(port))
            return False

    time.sleep(0.1)
    nBytesWritten = fifo.write(BAMessage)
    time.sleep(0.01)
    assert nBytesWritten == len(BAMessage), f"SERIALMOD: wrote {nBytesWritten} bytes, had to write {len(BAMessage)} bytes"
    return True


def flushBuffer(GUI):
    """ Flush the serial buffer to get rid of junk data"""
    fifo = GUI.serial
    if fifo is not None:
        fifo.reset_input_buffer()
        fifo.reset_output_buffer()
