import serial
import time
import serial.tools.list_ports as LP
import sys
import argparse
from platform import system

from configureLpGBT1213 import *

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
    writeMessage = [0x5a, 0x02, 0x40, 0x01, 0x37]
    writeToUSBISS(port, writeMessage)
    readFromUSBISS(port)

    # Check for existence of device with given i2c address
    writeMessage = [0x58, lpgbtAddr << 1]
    writeToUSBISS(port, writeMessage)
    result = readFromUSBISS(port)
    if len(result) != 1 :
      print("COULD NOT FIND LPGBT, EXITING")
      return None
    if result[0] != 1 :
      print("COULD NOT FIND LPGBT, EXITING")
      return None
    print( "IDENTIFIED lpGBT", pArgs.lpgbtNum )

    #lpGBT12 specific commands
    if pArgs.lpgbtNum == 12 :
      #set lpGBT12 GPIO15 ON to set lpGBT11 SC_I2C to 1
      #set 0x052 MSB to 1
      writeToLpGBT(port, lpgbtAddr, 0x052, [0x80])
      #set 0x054 MSB to 1
      writeToLpGBT(port, lpgbtAddr, 0x054, [0x80])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x052, 1)
      print("REG",0x052,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x054, 1)
      print("REG",0x054,"\tVAL",readBack)

      #set lpGBT12 ECLK24 ON to provide 40MHz to lPGBT11
      #set 0x09c to 0x21
      writeToLpGBT(port, lpgbtAddr, 0x09C, [0x21])
      #set 0x09D to 0x7C
      writeToLpGBT(port, lpgbtAddr, 0x09D, [0x7C])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x09C, 1)
      print("REG",0x09C,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x09D, 1)
      print("REG",0x09D,"\tVAL",readBack)

      #enable DCDC_EN_LPGBT_B via lpGBT12 GPIO4
      #set 0x053 to 0x10
      writeToLpGBT(port, lpgbtAddr, 0x053, [0x10])
      #set 0x055 to 0x10
      writeToLpGBT(port, lpgbtAddr, 0x055, [0x10])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x053, 1)
      print("REG",0x053,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x055, 1)
      print("REG",0x055,"\tVAL",readBack)

    #lpGBT13 specific commands
    if pArgs.lpgbtNum == 13 :
      #set lpGBT13 GPIO15 ON to set lpGBT14 SC_I2C to 1
      #set 0x052 MSB to 1
      writeToLpGBT(port, lpgbtAddr, 0x052, [0x80])
      #set 0x054 MSB to 1
      writeToLpGBT(port, lpgbtAddr, 0x054, [0x80])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x052, 1)
      print("REG",0x052,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x054, 1)
      print("REG",0x054,"\tVAL",readBack)

      #set lpGBT13 ECLK8 ON to provide 40MHz to lPGBT14
      #set 0x07c to 0x21
      writeToLpGBT(port, lpgbtAddr, 0x07C, [0x21])
      #set 0x07D to 0x7C
      writeToLpGBT(port, lpgbtAddr, 0x07D, [0x7C])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x07C, 1)
      print("REG",0x07C,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x07D, 1)
      print("REG",0x07D,"\tVAL",readBack)

      #enable DCDC_EN_LPGBT_A via lpGBT13 GPIO4
      #set 0x053 to 0x10
      writeToLpGBT(port, lpgbtAddr, 0x053, [0x10])
      #set 0x055 to 0x10
      writeToLpGBT(port, lpgbtAddr, 0x055, [0x10])
      readBack = readFromLpGBT(port, lpgbtAddr, 0x053, 1)
      print("REG",0x053,"\tVAL",readBack)
      readBack = readFromLpGBT(port, lpgbtAddr, 0x055, 1)
      print("REG",0x055,"\tVAL",readBack)


    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script for configuring the lpGBT and "
                                                 "blowing its E-Fuses via USB-ISS Module")
    parser.add_argument('lpgbtNum', metavar="lpGBT Number", type=int,
                        help='Which control lpGBT to configure (must be 12 or 13)')
    args = parser.parse_args()

    main(args)
