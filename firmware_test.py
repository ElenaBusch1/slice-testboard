first_reg = f'{0x0E0:012b}'
dataBitsToSend = f'001{first_reg[:5]}'  #header1
dataBitsToSend += f'{first_reg[5:]}0'   #header2

data = '00000010'   #write 0x02 to 0x0E0
wordCount = 1

wordCountByte2, wordCountByte1 = u16_to_bytes(wordCount)
dataBitsToSend += f'{wordCountByte1:08b}'  #nword[7:0]
dataBitsToSend += f'{wordCountByte2:08b}'  #nword[15:8]
dataBitsToSend += data

self.LpGBT_IC_write(wordCount, dataBitsToSend)


def LpGBT_IC_write(self, nwords, data)
    wordBlock = ''.join([data[i:i+8] for i in range(0, len(data), 8)][::-1])

    self.status45.sendFifoAOperation(operation=1,counter=(len(data)//8),address=7)
    serialMod.writeToChip(self,'45',wordBlock)
    self.status45.sendStartControlOperation(operation=1,address=7)
    self.status45.send()  