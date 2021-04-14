# Slice Testboard GUI - Setup #

1. If starting completely from scratch, begin by downloading FLX software from here: https://gitlab.cern.ch/atlas-tdaq-felix/software. (If needed, change flx_setup1.sh to point to the proper paths)

2. Configure the FLX with the proper firmware (it is currently located on flx-srv-atlas and you want the newest version), then reboot (soft reboot - a hard reboot will wipeout the firmware configuration you just did!). 

3. Create a conda virtual environment.  This only needs to be done once per installation instance of Python. Run the following commands in shell to generate the environment:
```
conda config --add channels conda-forge
conda create --name coluta python=3 pyserial pyqt=5.9.2 numpy matplotlib h5py
conda activate coluta
```
### If the computer is already setup but you just (soft) rebooted, start here! ### 
4. cd to the ~/FLX/slice-testboard/ directory on flx-srv-atlas and run `source flx_setup1.sh`. This will start the driver, start the FLX, and set up the FLX to send the clock and start to be ready to take data.

### If the computer is already on and configured, start here! ###
5. Activate the environment with `conda activate coluta`

6. Run the GUI with `python sliceBoard.py`

7. If you want to take data, run `python takeTriggerData.py` or use the **Take Trigger Data** button in the Data tab of the GUI.


# Slice Testboard GUI - Configuration #

1. To configure all chips on the board with their default configuration, press **Configure All** in the Control tab. This takes 4-5 minutes.

2. To configure only specific chips, choose the chip from the drop down menu on the Control tab, and press the corresponding **Configure** button. <br />
_Note_: lpgbt12 must be configured before any other chips on the lpgbt12 side of the board, and likewise for lpgbt13.

3. To write and read specific lpgbt registers, use the drop down menu on the Control tab to select an lpgbt. Enter the register to write/read in hex. If writing, also enter the value to write in hex. If you want to write the same value to more than one consecutive register, or read from multiple consecutive registers, enter the number of consecutive registers as a decimal. Press **Write to LpGBT** or **Read From LpGBT**. <br />
_Note_: If you are switching between data lpGBTs, you will need to do a master reset each time you switch. This can be done with the **Reset lpGBT12/13 I2C Control** buttons.  

4. To update a configuration, navigate to the chip using the LAUROC/ COLUTA/ lpGBT tabs. Change the configuration settings, then return to the Control tab and press **Send Updated Configurations**. 

### Configurations for taking Data ###
5. By default, COLUTA channels 1-6 come up in Serializer Test Mode, and channels 7-8 come up in normal mode. This can be changed in the COLUTA/Channel/DDPU tab. Additionally, in Channel 1 for each COLUTA there are **Turn On Serialier Mode** and **Turn Off Serializer Mode** buttons, which change serializer mode for all channels. 

6. For now, if you want to change between trigger mode and single ADC mode, you'll need to edit takeTriggerData.py directly. Comments in the file indicate which settings are needed for each mode.

# Slice Testboard Analysis #

### Pedestal Data ###

1. After a run is taken with the slice testboard, the data is stored on the FLX server. You can ssh in with `ssh -Y dawillia@flx-srv-atlas slice-testboard` (password is portmanteau of 2 universities). The data is stored in the directory `/home/dawillia/FLX/slice-testboard/Runs`. Many of the runs are also copied here on xenia for convenience: `/data/users/acs2325/slice_runs/` A list of good runs is kept here(https://docs.google.com/spreadsheets/d/1LRrg8CxLdXaRoX1FprGiC_ZAtnXlHQt8NTyy5Xv97Eo/edit#gid=0). The following code is meant to analyze Noise runs. Note that runs taken in 'single ADC mode' only contain 1 chip (8 channels) of data, so there are not many available channels in these runs to do collective analysis like noise coherence and correlation. Copy the run you want to analyze into the directory `slice-testboard/data/Raw/`. 

2. Convert the .hdf5 file containing the data from binary to decimal integer using the `convert.py` script ***Note*** this analysis may not work unless you have created the conda enviroment detailed above (see step 3 of 'Slice Testboard GUI - Setup'): 

```
cd slice-testboard/analysis
python convert.py 0243
```
The above code will convert run0243.hdf5 and store the result in `slice-testboard/data/Processed/0243/Pedestal_Data_Normal.hdf5`.

3. Edit the `main()` function of `PedAnalysis_slice.py` to include the plots you want to make, as well as the relevant channels. The functions which make these plots are all contained in `PedAnalysis_slice.py`. Output is saved in `slice-testboard/data/Processed/0243/Plots`. Typical plots for a pedestal analysis include raw waveforms, fitted baseline pedestals, coherent noise plots, and a noise correlation matrix in both hi and lo gain.

```
python PedAnalysis_slice.py 0243
```

