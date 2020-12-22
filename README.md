# Slice Testboard GUI #

1. If starting completely from scratch, begin by downloading FLX software from here: https://gitlab.cern.ch/atlas-tdaq-felix/software. (If needed, change flx_setup1.sh to point to the proper paths)

2. Configure the FLX with the proper firmware (it is currently located on flx-srv-atlas and you want the newest version), then reboot (soft reboot - a hard reboot will wipeout the firmware configuration you just did!). 

### If the computer is already setup but you just (soft) rebooted, start here! ### 
3. cd to the ~/FLX/slice-testboard/ directory on flx-srv-atlas and run `source flx_setup1.sh`. This will start the driver, start the FLX, and set up the FLX to send the clock and start to be ready to take data.

### If the computer is already on and configured, start here! ###
4. Run the GUI with `python sliceBoard.py`

5. If you want to take data, run `python takeTriggerData.py`
