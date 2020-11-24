import os, time

os.system("fpepo 0x66d0 0x100")
os.system("fpepo 0x66e0 0x7f0000")
cmd = "fdaq -T -t 2 /scratch/kchen/alldata1.dat &"
os.system(cmd)
time.sleep(0.1)
os.system("fpepo 0x66d0 0x102")
