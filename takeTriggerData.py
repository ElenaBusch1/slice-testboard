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
parser.add_argument("-s", "--sec", default = "2", type=int, nargs='+',
                   help="number of seconds for fdaq to acquire data")
args = parser.parse_args()
output = args.outputfile[0]
mode = args.type[0]
adc = args.adc[0]
if isinstance(args.sec, list) == True :
  sec = args.sec[0]
else:
  sec = args.sec

# Trigger mode
if mode == 'trigger':
    os.system("fpepo 0x66d0 0x100") #trigger mode
# Single ADC mode
elif mode == 'singleADC':
    os.system("fpepo 0x66f0 "+f"{adc:#0{4}x}") #select ADC, see flx-adc-mapping.txt 
    os.system("fpepo 0x66d0 0x000") #single adc mode
else:
    print("DAQ Mode not recognized. \n Exiting...")
    exit()

#Take data
os.system("fpepo 0x66e0 0x7f0000")
#cmd = "fdaq -T -t 2 -C "+output+" &"
cmd = "fdaq -T -t "+str(sec)+" -C "+output+" &"
os.system(cmd)
time.sleep(0.1)
if mode == 'trigger':
    os.system("fpepo 0x66d0 0x102") #for trigger mode
elif mode == 'singleADC':
    os.system("fpepo 0x66d0 0x02") #for single adc mode
