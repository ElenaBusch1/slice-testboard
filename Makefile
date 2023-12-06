export LATOURNETT=1

export FICE_LATS=1

# Path to LATOURNETT
export LATOURNETT_PATH=/data/users/nchevill/atlas-lar-be-firmware/LATOURNETT/fw_dev
export FW_CONTROL_PATH=$(LATOURNETT_PATH)/firmware_control

# Add necessary paths to python modules
export PYTHONPATH:=$(FW_CONTROL_PATH)/firmware_control:$(FW_CONTROL_PATH)/system_test:$(FW_CONTROL_PATH)/system_database:$(FW_CONTROL_PATH)/contexts:$(PYTHONPATH)

# Release path
export RELEASE_PATH=$(LATOURNETT_PATH)/release

#export LD_LIBRARY_PATH=/opt/cactus/lib:/usr/local/lib:$(LD_LIBRARY_PATH)
#export PATH=/opt/cactus/bin:$(PATH)

gui:
	python3 sliceBoard.py
