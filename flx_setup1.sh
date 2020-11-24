# Start the FLX
cd /home/kchen/software/drivers_rcc/script
sudo ./drivers_flx_local start

# Initialize FLX
flx-init

cd /home/kchen/testboard/slice-testboard

#Enable 10 Ghz clock
fpepo 0x65a0 0xffffffffffff
fpepo 0x6580 0xffffffffffff

#Enable data transmission to PCIe
fpepo 0x66d0 0x102
fpepo 0x66f0 0x0
#Transmit 128 samples per event
#fpepo -d 2 0x66e0 0x7f0000

