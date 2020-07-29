import time

def readFromChip(GUI, port, nBytes):
    pass


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
    except Exception:
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
