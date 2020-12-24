import os, time
import argparse

#os.system("fpepo 0x66d0 0x102")


#Parse arguments 
parser = argparse.ArgumentParser()
parser.add_argument("-o", "--outputfile", default = "output.dat", type=str, nargs='+',
                   help="name of output file to write to")
args = parser.parse_args()
output = args.outputfile[0]

# Trigger mode
os.system("fpepo 0x66d0 0x100") #trigger mode
# Single ADC mode
#os.system("fpepo 0x66f0 0x02") #adc20 
#os.system("fpepo 0x66d0 0x00") #single adc mode

#Take data
os.system("fpepo 0x66e0 0x7f0000")
cmd = "fdaq -T -t 2 -C data/"+output+" &"
os.system(cmd)
time.sleep(0.1)
os.system("fpepo 0x66d0 0x102")
