import sys
import os
from FirmwareControl import *


class LATOURNETT(object):
    def __init__(self):
        self.context = None
        self.latournett_id = 1

    def __GetFirmwareControl(self):
        if self.context is None:
            self.firmware_control = FirmwareControl()
            self.context = self.firmware_control.Run(args=['--configuration_path', '/data/users/nchevill/atlas-lar-be-firmware/LATOURNETT/fw_dev/firmware_control', '--release_path', '/data/users/nchevill/atlas-lar-be-firmware/LATOURNETT/fw_dev/release', '--context', '--fn_call', 'STM_Initialize', '--fn_args', f'{{"context": True, "latournett_ids": [{self.latournett_id}]}}'])
            if self.context is None:
                print('Could not create LATOURNETT firmware control')
                sys.exit(1)
            else:
                print(f'LATOURNETT: context={self.context}')

    def readFromLpGBT(self, GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, ICEC_CHANNEL):
        context = self.__GetFirmwareControl()
        data = self.context.latournett_ctx_0.LPGBT_IC_Read_RAM(lpgbt_link=ICEC_CHANNEL, lpgbt_address=GBTX_I2CADDR, memory_address=GBTX_ADDR, nb_data_bytes=GBTX_LEN, ic_n_ec=True)
        return data

    def ecReadFromLpGBT(self, GBTX_I2CADDR, GBTX_ADDR, GBTX_LEN, ICEC_CHANNEL):
        context = self.__GetFirmwareControl()
        data = self.context.latournett_ctx_0.LPGBT_IC_Read_RAM(lpgbt_link=ICEC_CHANNEL, lpgbt_address=GBTX_I2CADDR, memory_address=GBTX_ADDR, nb_data_bytes=GBTX_LEN, ic_n_ec=False)
        return data

    def writeToLpGBT(self, GBTX_I2CADDR, GBTX_ADDR, data_orig, ICEC_CHANNEL, ignore_replies):
        context = self.__GetFirmwareControl()
        result = self.context.latournett_ctx_0.LPGBT_IC_Write_RAM(lpgbt_link=ICEC_CHANNEL, lpgbt_address=GBTX_I2CADDR, memory_address=GBTX_ADDR, memory_bytes=data_orig, ic_n_ec=True, ignore_replies=ignore_replies)
        return result

    def ecWriteToLpGBT(self, GBTX_I2CADDR, GBTX_ADDR, data_orig, ICEC_CHANNEL, ignore_replies):
        context = self.__GetFirmwareControl()
        result = self.context.latournett_ctx_0.LPGBT_IC_Write_RAM(lpgbt_link=ICEC_CHANNEL, lpgbt_address=GBTX_I2CADDR, memory_address=GBTX_ADDR, memory_bytes=data_orig, ic_n_ec=False, ignore_replies=ignore_replies)
        return result

