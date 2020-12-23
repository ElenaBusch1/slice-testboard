# Slice Testboard GUI - Setup #

1. If starting completely from scratch, begin by downloading FLX software from here: https://gitlab.cern.ch/atlas-tdaq-felix/software. (If needed, change flx_setup1.sh to point to the proper paths)

2. Configure the FLX with the proper firmware (it is currently located on flx-srv-atlas and you want the newest version), then reboot (soft reboot - a hard reboot will wipeout the firmware configuration you just did!). 

### If the computer is already setup but you just (soft) rebooted, start here! ### 
3. cd to the ~/FLX/slice-testboard/ directory on flx-srv-atlas and run `source flx_setup1.sh`. This will start the driver, start the FLX, and set up the FLX to send the clock and start to be ready to take data.

### If the computer is already on and configured, start here! ###
4. Activate the environment with `conda activate coluta`

5. Run the GUI with `python sliceBoard.py`

6. If you want to take data, run `python takeTriggerData.py` or use the **Take Trigger Data** button in the Data tab of the GUI.


# Slice Testboard GUI - Configuration #

1. To configure all chips on the board with their default configuration, press **Configure All** in the Control tab. This takes 4-5 minutes.

2. To configure only specific chips, choose the chip from the drop down menu on the Control tab, and press the corresponding **Configure** button. 
_Note_: lpgbt12 must be configured before any other chips on the lpgbt12 side of the board, and likewise for lpgbt13.

3. To write and read specific lpgbt registers, use the drop down menu on the Control tab to select an lpgbt. Enter the register to write/read in hex. If writing, also enter the value to write in hex. If you want to write the same value to more than one consecutive register, or read from multiple consecutive registers, enter the number of consecutive registers as a decimal. Press **Write to LpGBT** or **Read From LpGBT**. 
_Note_: If you are switching between data lpGBTs, you will need to do a master reset each time you switch. This can be done with the _Reset lpGBT12/13 I2C Control_ buttons.  

4. To update a configuration, navigate to the chip using the LAUROC/ COLUTA/ lpGBT tabs. Change the configuration settings, then return to the Control tab and press **Send Updated Configurations**. 

## Configurations for taking Data ##
5. By default, COLUTA channels 1-6 come up in Serializer Test Mode, and channels 7-8 come up in normal mode. This can be changed in the COLUTA/Channel/DDPU tab. Additionally, in Channel 1 for each COLUTA there are **Turn On Serialier Mode** and **Turn Off Serializer Mode** buttons, which change serializer mode for all channels. 

6. For now, if you want to change between trigger mode and single ADC mode, you'll need to edit takeTriggerData.py directly. Comments in the file indicate which settings are needed for each mode.