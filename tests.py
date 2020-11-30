    def silly_reg_test(self):
        lpgbtI2CAddr = int(self.chips["lpgbt12"].i2cAddress,2)
        dataI2CAddr = int(self.chips["lpgbt10"].i2cAddress,2)
        register = 0x062
        data = [21]
        self.i2cDataLpgbtWriteOneReg(lpgbtI2CAddr, dataI2CAddr, register, data)
        #self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, register, data)
        register = 0x082
        data = [22]
        self.i2cDataLpgbtWriteOneReg(lpgbtI2CAddr, dataI2CAddr, register, data)
        #self.i2cDataLpgbtWrite(lpgbtI2CAddr, dataI2CAddr, register, data)
        register = 0x062
        self.i2cDataLpgbtRead(lpgbtI2CAddr, dataI2CAddr, register, 4)

        print("READ STATUS REGS")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x174, 4)
        print("SINGLE READ REG")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x178, 1)
        print("MULTI READ REG")
        readFromLpGBT(self.i2cPort, lpgbtI2CAddr, 0x179, 16)

    def test_lpgbt9config_loop(self):
        print("START lpGBT14 config loop")
        while True:
            self.i2cControlLpGBT("lpgbt14")
            #self.i2cDataLpGBT("lpgbt9")

    def test(self):
        """General purpose test function"""
        # with open("tmp.txt", 'a') as f:
        #     for (chipName, chipConfig) in self.chips.items():
        #         f.write(chipName + "\n")
        #         for (sectionName, section) in chipConfig.items():
        #             f.write(f"{sectionName}: {section.bits}\n")
        #             for (settingName, setting) in section.items():
        #                 f.write(f"{settingName}: {setting}\n")
        #             f.write("\n")
        #         f.write("\n")

        #erialMod.flushBuffer(self, "45")
        #elf.status45.readbackStatus()
        #ime.sleep(0.1)
        #erialMod.readFromChip(self, "45", 6)
        #elf.status45.send()

        #dataBlock = 'F0EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0DFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0BFBEBDBCBBBAB9B8B7B6B5B4B3B2B1B0AFAEADACABAAA9A8A7A6A5A4A3A2A1A09F9E9D9C9B9A999897969594939291908F8E8D8C8B8A898887868584838281807F7E7D7C7B7A797877767574737271706F6E6D6C6B6A696867666564636261605F5E5D5C5B5A595857565554535251504F4E4D4C4B4A494847464544434241403F3E3D3C3B3A393837363534333231302F2E2D2C2B2A292827262524232221201F1E1D1C1B1A191817161514131211110F0E0D0C0B0A09080706050403020100F00000'
        dataBlock = 'F0EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0DFDEDDDCDBDAD9D8D7D6D5D4D3D2D1D0CFCECDCCCBCAC9C8C7C6C5C4C3C2C1C0BFBEBDBCBBBAB9B8B7B6B5B4B3B2B1B0AFAEADACABAAA9A8A7A6A5A4A3A2A1A09F9E9D9C9B9A999897969594939291908F8E8D8C8B8A898887868584838281807F7E7D7C7B7A797877767574737271706F6E6D6C6B6A696867666564636261600090C000'
        dataBitsToSend = ''
        for word in [dataBlock[i:i+2] for i in range(0, len(dataBlock), 2)]:
            val = int(word,16)
            #if val < 96:
            #    continue
            print(word,val)
            dataBitsToSend += f'{val:08b}'

        self.LpGBT_IC_write(None, dataBitsToSend)

    def lpgbt_test(self):

        chip = self.chips["lpgbt14"]

        i2cAddr = f'{0xE0:08b}'
        first_reg = f'{0x5D:012b}'
        #first_reg = f'{0x052:012b}'
        dataBitsToSend = f'000{first_reg[:5]}'
        dataBitsToSend += f'{first_reg[5:]}0'

        data = ''.join([f'{0Xaa:08b}' for i in range(1,96)])
        #data = '00000010'
        #data += '00000011'
        #data += '00000100'
        wordCount = len(data)

        wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        dataBitsToSend += f'{wordCountByte1:08b}'
        dataBitsToSend += f'{wordCountByte2:08b}'
        dataBitsToSend += data

        #data4 = ''.join(['00000000', '00010000', '00000000', '00010000', '00000000', '00000000', '00000000', '00000000', '00000000', '00010000'])
        #data11 = ''.join(['00001000', '00000000', '00001000', '00000000', '00000000', '00000000', '00000000', '00000000', '00001000', '00000000'])

        while True:
             #readFromLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x062, 1)
             writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x062, [0x21])
        #    writeToLpGBT(self.i2cPort, int(chip.i2cAddress, 2), 0x0fd, [0x02])

        #self.LpGBT_IC_write(dataBitsToSend)

        #dataBitsToSend4 = f'000{first_reg[:5]}' + f'{first_reg[5:]}0' + f'{wordCountByte1:08b}' + f'{wordCountByte2:08b}' + data4
        #dataBitsToSend11 = f'000{first_reg[:5]}' + f'{first_reg[5:]}0' + f'{wordCountByte1:08b}' + f'{wordCountByte2:08b}' + data11

        #self.LpGBT_IC_write(i2cAddr, dataBitsToSend4)
        #self.LpGBT_IC_write(i2cAddr, dataBitsToSend11)

    def configure_clocks_test(self):
        i2cAddr = f'{0XE0:08b}'
        #i2cAddr =

        #regAddrs = [0x06c, 0x06d, 0x07c, 0x07d, ]

        regAddr  = [0x06c, 0x07c, 0x080, 0x084, 0x088, 0x08c, 0x090, 0x094, 0x09c, 0x0ec]
        regDataA = [0x19,  0x19,  0x19,  0x00,  0x19,  0x19,  0x19,  0x19,  0x19,  0x00]
        regDataB = [0x73,  0x73,  0x73,  0x00,  0x73,  0x73,  0x73,  0x73,  0x73,  0x00]
        regDataC = [0x00,  0x19,  0x00,  0x19,  0x19,  0x19,  0x00,  0x00,  0x00,  0x00]
        regDataD = [0x00,  0x73,  0x00,  0x73,  0x73,  0x73,  0x00,  0x00,  0x00,  0x07]

        #regDataA = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataB = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataC = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]
        #regDataD = [0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00,  0x00]


        for i in range(len(regAddr)):
            addr = regAddr[i]
            first_reg = f'{addr:012b}'
            dataBitsToSend = f'000{first_reg[:5]}'
            dataBitsToSend += f'{first_reg[5:]}0'

            data = ''.join([f'{regDataA[i]:08b}', f'{regDataB[i]:08b}', f'{regDataC[i]:08b}', f'{regDataD[i]:08b}'])

            wordCount = len(data)//8

            wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
            dataBitsToSend += f'{wordCountByte1:08b}'
            dataBitsToSend += f'{wordCountByte2:08b}'
            dataBitsToSend += data

            self.LpGBT_IC_write(dataBitsToSend)

        #while True:
        #    self.LpGBT_IC_write(i2cAddr, dataBitsToSend)


    def write_uplink_test(self):

        chip = self.chips['lpgbt14']
        configureLpGBT1213.uplinkDataTest(self.i2cPort, int(chip.i2cAddress, 2))


        # dummy = f'{0XE0:08b}'

        # first_reg = f'{0x118:012b}'
        # dataBitsToSend = f'000{first_reg[:5]}'
        # dataBitsToSend += f'{first_reg[5:]}0'  

        # #data = ''.join(['00000000', '00000000', '00000000', '00000000', '00000000', '00000000', '00000001', '00000010', '00000011', '00000100'])
        # dataValues = [0x0c, 0x24, 0x24, 0x24, 0x04, 0xff]
        # data = ''.join([f'{val:08b}' for val in dataValues])
        # #data = '00000111'
        # #data = f'{}
        # #data += '00000000'
        # wordCount = len(data)//8
        # #wordCount = len(data)//8

        # wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
        # dataBitsToSend += f'{wordCountByte1:08b}'
        # dataBitsToSend += f'{wordCountByte2:08b}'
        # dataBitsToSend += data  

        # self.LpGBT_IC_write(dataBitsToSend)        

        # sec_reg = f'{0x121:012b}'
        # dataBitsToSend2 = f'000{sec_reg[:5]}'
        # dataBitsToSend2 += f'{sec_reg[5:]}0'  

        # data2 = '00000001'

        # wordCount2 = len(data2)
        # wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount2)
        # dataBitsToSend2 += f'{wordCountByte1:08b}'
        # dataBitsToSend2 += f'{wordCountByte2:08b}'
        # dataBitsToSend2 += data2  


    def coluta_config_test(self):

        i2cAddr = f'{0xE0:08b}'

        wordCount = 16
        data =  '11111010' +\
                '11011000' +\
                '10001010' +\
                '11010111' +\
                '01110110' +\
                '10111001' +\
                '10000100' +\
                '00000100' +\
                '00000000' +\
                '00011111' +\
                '11000010' +\
                '10100000' +\
                '00000100' +\
                '01000000' +\
                '01000001' +\
                '00010100'

        self.sendCOLUTAConfigs('coluta13', wordCount, data)

    def collectColutaConfigs(self):

        with open("coluta_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('coluta') == -1:
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                i2cM = f'{int(chipConfig.i2cMaster):02b}'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                #i2cAddr = f'{int(chipConfig.i2cAddress,0):010b}'
                i2cAddr = '0'+chipConfig.i2cAddress
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_{i2cAddr[:3]}  #chip_controlLpGBT_i2cMaster_i2cAddr[9:7]\n')
                f.write(f'{i2cAddr[3:11]}_0 #i2cAddr[6:0]_r/w\n')

                wordCount = 0;
                dataBits = ''
                for (sectionName, section) in chipConfig.items():
                    # data = self.chips[chipname][sectionname].bits
                    data = self.colutaI2CWriteControl(chipName, sectionName)
                    datawords = [data[8*i:8*(i+1)] for i in range(len(data)//8)]
                    localWordCount = len(datawords)
                    dataBits += (chipName + ", " + sectionName + ": " + str(localWordCount) + " words\n")
                    for word in datawords:
                        dataBits += f'{word}\n'
                        wordCount += 1
                    dataBits += '\n'



                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords {wordCount}\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')

    def collectLaurocConfigs(self):

        with open("lauroc_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('lauroc') == -1:
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                i2cM = f'{int(chipConfig.i2cMaster):02b}'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                #i2cAddr = f'{int(chipConfig.i2cAddress,0):010b}'
                i2cAddr = '000'+ chipConfig.i2cAddress
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_{i2cAddr[:3]}  #chip_controlLpGBT_i2cMaster_i2cAddr[9:7]\n')
                f.write(f'{i2cAddr[3:]}_0 #i2cAddr[6:0]_r/w\n')

                dataBits = ''
                wordCount = 1
                for (sectionName, section) in chipConfig.items():
                    data = self.chips[chipName][sectionName].bits
                    addr = int(self.chips[chipName][sectionName].address,0)
                    dataBits += f'{data}\n'
                    if wordCount == 1:
                        registerAddr = addr
                    wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords {wordCount}\n')
                f.write(f'{registerAddr:08b}  #first address\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')

    def collectDataLpgbtConfigs(self):

        with open("data_lpgbt_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if chipName.find('lpgbt') == -1:
                    continue
                if (chipName.find('lpgbt12') != -1 or chipName.find('lpgbt13') != -1):
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                try:
                    i2cM = f'{int(chipConfig.i2cMaster):02b}'
                except:
                    i2cM = 'EC'
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'
                f.write(f'{chipType}_{controlLpGBTbit}_{i2cM}_000  #chipType_controlLpGBT_i2CMaster_000\n')
                f.write(f'{chipConfig.i2cAddress}_0 #i2cAddr_r/w\n')

                dataBits = ''
                wordCount = 2
                for (sectionName, section) in chipConfig.items():
                    data = self.chips[chipName][sectionName].bits
                    addr = int(self.chips[chipName][sectionName].address,0)
                    dataBits += f'{data}\n'
                    if wordCount == 2:
                        registerAddr = addr
                    wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                f.write(f'{wordCountByte1:08b}  #datawords[7:0] {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords[15:8] {wordCount}\n')

                addr2, addr1 = u16_to_bytes(registerAddr)
                f.write(f'{addr1:08b}  #first address [7:0]\n')
                f.write(f'{addr2:08b}  #first address [15:8]\n')
                #if chipName.find('lpgbt') != -1:

                f.write(dataBits)
                f.write('\n')

    def collectControlLpgbtConfigs(self):

        with open("control_lpgbt_configs.txt", 'w') as f:
            for (chipName, chipConfig) in self.chips.items():
                if (chipName != 'lpgbt12' and chipName != 'lpgbt13'):
                    continue
                f.write(chipName + "\n")
                chipType = f'{int(chipConfig.chipType):02b}'
                controlLpGBT = chipConfig.lpgbtMaster
                controlLpGBTbit = '0'
                if (controlLpGBT == '13'):
                    controlLpGBTbit = '1'

                dataBits = ''
                wordCount = 0
                for (sectionName, section) in chipConfig.items():
                    if section.updated:
                        data = self.chips[chipName][sectionName].bits
                        addr = int(self.chips[chipName][sectionName].address,0)
                        dataBits += f'{data}\n'
                        if wordCount == 0:
                            #registerAddr = addr
                            registerAddr = 0x1ce
                        wordCount += 1

                wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
                full_addr = f'{registerAddr:012b}'

                f.write(f'{chipType}_{controlLpGBTbit}_{full_addr[:5]}  #chipType_controlLpGBT_1stReg[11:7]\n')
                f.write(f'{full_addr[5:]}_0 #1stReg[6:0]_r/w\n')

                f.write(f'{wordCountByte1:08b}  #datawords[7:0] {wordCount}\n')
                f.write(f'{wordCountByte2:08b}  #datawords[15:8] {wordCount}\n')
                #if chipName.find('lpgbt') != -1:
                
      
