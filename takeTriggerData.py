import os, time

#os.system("fpepo 0x66d0 0x102")

# Trigger mode
os.system("fpepo 0x66d0 0x100") #trigger mode
# Single ADC mode
#os.system("fpepo 0x66f0 0x02") #adc20 
#os.system("fpepo 0x66d0 0x00") #single adc mode

#Take data
os.system("fpepo 0x66e0 0x7f0000")
cmd = "fdaq -T -t 2 -C alldata7.dat &"
os.system(cmd)
time.sleep(0.1)
os.system("fpepo 0x66d0 0x102")
