import os, time
import argparse

#os.system("fpepo 0x66d0 0x102")


#Parse arguments 
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outputfile", default = "output.dat", type=str, nargs='+',
                   help="name of output file to write to")
parser.add_argument("-t", "--type", default = "trigger", type=str, nargs='+',
                   help="DAQ Mode: trigger or singleADC")
parser.add_argument("-a", "--adc", default = "7", type=int, nargs='+',
                   help="select adc for singleADC mode. 4 = ADC17, 7 = ADC20")
args = parser.parse_args()
output = args.outputfile[0]
mode = args.type[0]
adc = args.adc[0]

# Trigger mode
if mode == 'trigger':
    os.system("fpepo 0x66d0 0x100") #trigger mode
# Single ADC mode
elif mode == 'singleADC'
    os.system("fpepo 0x66f0 0x07") #select ADC, see flx-adc-mapping.txt 
    os.system("fpepo 0x66d0 "+f"{adc:#0{5}x}") #single adc mode
else:
    print("DAQ Mode not recognized. \n Exiting...")
    return

#Take data
os.system("fpepo 0x66e0 0x7f0000")
cmd = "fdaq -T -t 2 -C "+output+" &"
os.system(cmd)
time.sleep(0.1)
if mode == 'trigger':
    os.system("fpepo 0x66d0 0x102") #for trigger mode
elif mode == 'singleADC':
    os.system("fpepo 0x66d0 0x02") #for single adc mode
