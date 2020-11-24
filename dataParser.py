import configparser
import os
import numpy
import h5py
import csv
from collections import defaultdict

### Helper functions ###
def isSequence(arg):
    """Determines if arg is a sequence. See https://stackoverflow.com/questions/1835018/"""
    return (not hasattr(arg, "strip") and
            (hasattr(arg, "__getitem__") or
             hasattr(arg, "__iter__")))

def stringRoll(words, shift):
    """Takes the list of strings that is our raw data (words) and rolls it.
    This is necessary when the data from the various COLUTA channels does not line up"""
    if not isSequence(words):
        print('stringRoll input is not an array')
        return words
    split_words = [list(word) for word in words]
    rolled_words = numpy.roll(split_words, shift)
    new_words = [''.join(rolled_word) for rolled_word in rolled_words]

    # You could do this in a one line list comp too:
    # new_words = [''.join(rolled_word) for rolled_word in numpy.roll([list(word) for word in words],shift)]

    return new_words


class dataParser:

    def __init__(self, GUI, configFile):
        self.configFile = configFile
        self.output_directory = "./data_files/"
        self.GUI = GUI

        self.updatedConfigs = {}
        self.configurations = []

        self.setupConfigurations()

        self.runNumber = 1
        self.outputDirectory = self.output_directory + 'Run_' + str(self.runNumber).zfill(4) + '/'
        # Check if the output directory exists, if not, create the directory
        while os.path.exists(self.outputDirectory):
            self.runNumber += 1
            self.outputDirectory = self.output_directory + 'Run_' + str(self.runNumber).zfill(4) + '/'
        os.makedirs(self.outputDirectory)

        # Make dicts for each COLUTA and keep track of file number for channel
        data_groups = [x.strip() for x in getattr(self, "general").getSetting("data_chips")]
        print(data_groups)
        for group in data_groups:
            setattr(self, group + "DecimalDict", defaultdict(list))
            setattr(self, group + "BinaryDict", defaultdict(list))
            for channel in [x.strip() for x in getattr(self, group).getSetting("data_channels")]:
                setattr(self, group + channel + "_fileNumber", 0)


    def setupConfigurations(self):
        """Set up the parser settings for each data source"""
        config = configparser.ConfigParser()
        config.optionxform = str

        if not os.path.isfile(self.configFile):
            self.GUI.showError('DATA PARSER: Configuration file not found')

        config.read(self.configFile)
        categoryDict = dict(config.items('Categories'))

        for categoryName in categoryDict:
            categoryTemplate = categoryDict[categoryName]
            self.readConfigFile(categoryName, categoryTemplate)
            self.configurations.append(categoryName)


    def readConfigFile(self, categoryName, categoryTemplate):
        """Read sections of the config file"""
        config = configparser.ConfigParser()
        config.optionxform = str

        config.read(self.configFile)

        if not config.has_section(categoryTemplate):
            if not config.sections():
                self.GUI.showError('DATA PARSER: Error reading config file. No sections found')
            else:
                self.GUI.showError(f'DATA PARSER: Error reading {categoryTemplate} section')

        configItems = dict(config.items(categoryTemplate))
        setting = Setting(configItems)
        setattr(self, categoryName, setting)


    def parseData(self, nSamplesToParse, dataFromChip):
        bitsPerMeasurement = int(getattr(self, "general").getSetting("word_length"))
        dataChunks = [dataFromChip[i:i+bitsPerMeasurement] for i in range(0, len(dataFromChip), bitsPerMeasurement)]
        for group in getattr(self, "general").getSetting("data_chips"):
            getattr(self, group + "BinaryDict").clear()
            getattr(self, group + "DecimalDict").clear()
        self.parseADC(dataChunks[:nSamplesToParse])


    def parseADC(self, binaryData):
        """Parse and sort binary ADC data into data groups"""
        words = getattr(self, "general").getSetting("data_words")

        bitsPerSample = int(getattr(self, 'rootGroup').settings['total_bits'])
        #print(bitsPerSample)

        # Group the binaryList into 32-bit long words
        dataSamples = [sample[i:i+bitsPerSample] for sample in binaryData for i in range(0, len(sample), bitsPerSample)]
        #print(dataSamples)
        # TODO: This needs to be updated once we know how the data coming out of the VTRx+3/6 is formatted
        # The data from the lpGBT is packaged into 8 32-bit words called "groups"
        # In testboard v1.1, we are sending data in groups 1, 2, and 3 (groups are 0-indexed)
        # Within each group there are two channels. The mapping of where each channel is
        #  stored within each group is listed in dataConfig.cfg. This mapping can change
        #  between testboard revisions, but should be the same within a given revision
        for samples in zip(*[dataSamples[i::8] for i in range(8)]):  # take all 8 lpGBT output words
            samples = samples[3:7]  # but only keeps words 1, 2, and 3; where are data is
            #print(samples)
            # Verify that at least one sample isn't empty. May want to change all to any
            if all(sample == '0' * bitsPerSample for sample in samples): continue
            # Loop over words and their corresponding samples, and each channel within each word
            for (sample, word) in zip(samples, words):
                #print(sample, word)
                # Get the parser settings
                configDict = getattr(self, word).settings
                # Get the names of the subgroups, e.g. frame, channel1
                dataChips = configDict['data_chips']
                dataChannels = configDict['data_channels']
                # Get the bit positions for the data subgroups
                lsbList = configDict['lsb']
                msbList = configDict['msb']
                # Take a 16-bit sample and store it in its proper channel list
                for (chip, channel, lsb, msb) in zip(dataChips, dataChannels, lsbList, msbList):
                    #print(chip, channel, lsb, msb)
                    binaryDict = getattr(self, chip + 'BinaryDict')
                    decodedWord = sample[int(lsb):int(msb)]
                    binaryDict[channel].append(decodedWord)
                    #print("channel", channel)
                    #print("word", decodedWord)

        # A problem with the alignment of the data coming from the COLUTAs to the lpGBT can arise
        # The misalignment for each channel is (currently) determined via trial and error, then
        #  stored in dataConfig.cfg as the "roll" attribute
        # This loop rolls the data for each channel so that they are all properly aligned
        for word in words:
            configDict = getattr(self, word).settings
            dataChips = configDict['data_chips']
            dataChannels = configDict['data_channels']
            dataRoll = configDict['roll']
            for (chip, channel, roll) in zip(dataChips, dataChannels, dataRoll):
                binaryDict = getattr(self, chip + 'BinaryDict')
                decimalDict = getattr(self, chip + 'DecimalDict')
                binaryData = stringRoll(binaryDict[channel], int(roll))
                decimalData = [self.convertColutaBits(chip, channel, decodedWord) for decodedWord in binaryData]
                binaryDict[channel] = binaryData
                decimalDict[channel] = decimalData


    def getWeightsArray(self, group, channel, overflow=0):
        """gets the current ADC weights"""
        ch = channel[:2] + channel[-1]

        try:
            boxName = group + ch + 'ArithmeticModeBox'
            measurementMode = getattr(self.GUI, boxName).currentText()
            calibration = (measurementMode.replace(' ', '_')).lower()
            if overflow == 1 and calibration == 'normal_mode':
                weights = [0, 0, 4095, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            else:
                weights = getattr(self, "calibration").getSetting(calibration)

        except AttributeError:
            weights = getattr(self, "calibration").getSetting('raw_data')

        weightsArr = numpy.array(weights, dtype=int)

        return weightsArr


    def convertColutaBits(self, group, channel, binaryWord):
        """Convert COLUTA bits based on calibration mode selected"""
        wordArr = numpy.array(list(map(int, binaryWord)))
        weightsArr = self.getWeightsArray(group, channel, overflow=wordArr[2])
        decimalWord = numpy.sum(numpy.dot(wordArr, weightsArr))

        return decimalWord


    def writeDataToFile(self):
        """Write the data to its corresponding file"""
        for group in getattr(self, "general").getSetting("data_chips"):
            for channel in getattr(self, group).getSettings("data_channels"):

                fileNumber = getattr(self, group + channel + "_fileNumber")
                binaryData = getattr(self, group + "BinaryDict")
                decimalData = getattr(self, group + "DecimalDict")

                decimal_outFile = group.upper()+'_'+channel.upper()+'_'+str(fileNumber).zfill(4)+"_Decimal.txt"
                binary_outFile = group.upper()+'_'+channel.upper()+'_'+str(fileNumber).zfill(4)+"_Binary.txt"
                csv_outFile = group.upper()+'_'+channel.upper()+'_'+str(fileNumber).zfill(4)+"_Binary.csv"

                binaryFilePath = os.path.join(self.outputDirectory, binary_outFile)
                decimalFilePath = os.path.join(self.outputDirectory, decimal_outFile)
                csvFilePath = os.path.join(self.outputDirectory, csv_outFile)

                if self.GUI.pArgs.debug:
                    numpy.savetxt(binaryFilePath,
                                  binaryData[channel],
                                  fmt='%s',
                                  delimiter='\t',
                                  newline='\n')

                    numpy.savetxt(decimalFilePath,
                                  decimalData[channel],
                                  fmt='%s',
                                  delimiter='\t',
                                  newline='\n')

                with open(csvFilePath, 'w', newline='\n') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',')
                    writer.writerows(binaryData[channel])

                fileNumber += 1
                setattr(self, group + channel + '_fileNumber', fileNumber)


class Setting:
    def __init__(self, configDict):
        self.settings = {}
        for name, value in configDict.items():
            settingValue = [x.strip() for x in value.split(',')]
            if len(settingValue) > 1:
                self.settings[name] = settingValue
            else:
                self.settings[name] = settingValue[0]

    def getSetting(self, settingName):
        try:
            value = self.settings[settingName]
        except KeyError:
            print("Key Error: the device does not have the setting", settingName)
            value = None
        return value

    def setSetting(self, settingName, settingValue):
        try:
            self.settings[settingName] = settingValue
        except KeyError:
            print("Cannot update setting", settingName, "to value", settingValue)
