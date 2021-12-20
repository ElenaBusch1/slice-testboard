#Interface Module for Slow Control Database

import sqlite3

#This will give you the slow control data given a coluta and phase. The relevant fields can be found in line 5 of this function
def colutaSlow(database, coluta, phase):
	conn = sqlite3.connect(database)
	c = conn.cursor()
	c.execute(f"SELECT * FROM COLUTA WHERE COLUTA = {coluta} AND PHASE = {phase}") 
	data = c.fetchall()[0]
	data_dictionary = {"coluta": data[0], "phase": data[1], "LPGBTPhaseX": convert(data[2]), "inv640": convert(data[3]), "delay640": convert(data[4])}
	conn.commit()
	conn.close()
	return data_dictionary



#This will give you the slow control data given a lpgbt and ChnCntr. The relevant fields can be found in line 5 of this function
def lpgbtSlow(database, lpgbt, ChnCntr):
	conn = sqlite3.connect(database)
	c = conn.cursor()
	c.execute(f"SELECT * FROM LPGBT WHERE LPGBT = {lpgbt} AND CHNCNTR = {ChnCntr}") 
	data = c.fetchall()[0]
	data_dictionary = {"lpgbt": data[0], "ChnCntr": data[1], "xPhaseSelect": convert(data[2]), "PS0Config": convert(data[3]), "PS1Config": convert(data[4]), "PS2Config": convert(data[5]), "PS3Config": convert(data[6]), "EPCLK2ChnCntrH": convert(data[7]), "EPCLK2ChnCntrL": convert(data[8]), "EPCLK0ChnCntrH": convert(data[9]), "EPCLK0ChnCntrL": convert(data[10])}
	conn.commit()
	conn.close()
	return data_dictionary

#This is for retrieving binary information
def convert(bin_number):
	if bin_number == "N/A":
		return bin_number
	else:
		return bin(int(bin_number, 2))



#Slow Control Database is meant to be created only once, after which not much changes are expected to be made
#The code below is for writing into the database
"""
#SlowControlDatabaseCreator

import sqlite3
conn = sqlite3.connect('slowControl.db')
c = conn.cursor()

# Select either "COLUTA" or "LPGBT"
tableDesignation = "NONE"
coluta = 20
lpgbt = 16												


#This is to write to the COLUTA file
if tableDesignation == "COLUTA":
	colutaValues = True
	c.execute(f"CREATE TABLE if not exists {tableDesignation} (COLUTA SMALLINT(20), PHASE SMALLINT(20), LPGBTPhase VARCHAR(20), INV640 VARCHAR(20), DELAY640 VARCHAR(20))")
else:
	colutaValues = False
if colutaValues:
	#Enter these values as strings for each coluta config file
	#Phase 1
	LPGBTPhase1 = "0010"
	#Phase 2
	LPGBTPhase2 = "0010"
	#Phase 3
	LPGBTPhase3 = "0010"
	#Phase 4
	LPGBTPhase4 = "0010"
	#Phase 5
	LPGBTPhase5 = "0001"
	#Phase 6
	LPGBTPhase6 = "0001"
	#Phase 7
	LPGBTPhase7 = "0010"
	#Phase 8
	LPGBTPhase8 = "0010"
	#Global
	inv640 = "0"
	delay640 = "110"

	LPGBTPhaseList = [LPGBTPhase1, LPGBTPhase2, LPGBTPhase3, LPGBTPhase4, LPGBTPhase5, LPGBTPhase6, LPGBTPhase7, LPGBTPhase8]
	phaseList = [1, 2, 3, 4, 5, 6, 7, 8]

	for phase in phaseList:
		index = phase - 1
		LPGBTPhaseX = LPGBTPhaseList[index]
		c.execute(f"INSERT INTO {tableDesignation} VALUES ({coluta}, {phase}, '{LPGBTPhaseX}', '{inv640}', '{delay640}');")
	print("Coluta added")

if tableDesignation == "LPGBT":
	lpgbtValues = True
	c.execute(f"CREATE TABLE if not exists {tableDesignation} (LPGBT SMALLINT(20), CHNCNTR SMALLINT(20), XPHASESELECT VARCHAR(20), PS0CONFIG VARCHAR(20), PS1CONFIG VARCHAR(20), PS2CONFIG VARCHAR(20), PS3CONFIG VARCHAR(20), EPCLK2CHNCNTRH VARCHAR(20), EPCLK2CHNCNTRL VARCHAR(20), EPCLK0CHNCNTRH VARCHAR(20), EPCLK0CHNCNTRL VARCHAR(20))")
else:
	lpgbtValues = False


if lpgbtValues:
	#Enter these values as strings for each coluta config file
	#ChnCntr0
	xPhaseSelect0 = "1100"
	#ChnCntr2
	xPhaseSelect2 = "1100"
	#ChnCntr10
	xPhaseSelect10 = "0101"
	#ChnCntr12
	xPhaseSelect12 = "0101"
	#ChnCntr20
	xPhaseSelect20 = "0110"
	#ChnCntr22
	xPhaseSelect22 = "0111"
	#ChnCntr30
	xPhaseSelect30 = "1000"
	#ChnCntr32
	xPhaseSelect32 = "1000"
	#ChnCntr40
	xPhaseSelect40 = "0110"
	#ChnCntr42
	xPhaseSelect42 = "0110"
	#ChnCntr50
	xPhaseSelect50 = "1100"
	#ChnCntr52
	xPhaseSelect52 = "1100"
	#chnCntr60
	xPhaseSelect60 = "0111"
	#chnCntr62
	xPhaseSelect62 = "0111"	
	#PS0Config
	PS0Config = "00100001"
	#PS0Config
	PS1Config = "01111101"
	#PS0Config
	PS2Config = "00100001"
	#PS0Config
	PS3Config = "01111101"	
	#EPCLK2ChnCntrH
	EPCLK2ChnCntrH = "N/A"
	#EPCLK2ChnCntrH
	EPCLK2ChnCntrL = "N/A"
	#EPCLK2ChnCntrH
	EPCLK0ChnCntrH = "01100001"
	#EPCLK2ChnCntrH
	EPCLK0ChnCntrL = "N/A"


	xPhaseSelectList = [xPhaseSelect0, xPhaseSelect2, xPhaseSelect10, xPhaseSelect12, xPhaseSelect20, xPhaseSelect22, xPhaseSelect30, xPhaseSelect32, xPhaseSelect40, xPhaseSelect42, xPhaseSelect50, xPhaseSelect52, xPhaseSelect60, xPhaseSelect62]
	ChnCntrList = [0, 2, 10, 12, 20, 22, 30, 32, 40, 42, 50, 52, 60, 62]


	for index in range(len(ChnCntrList)):
		ChnCntr = ChnCntrList[index]
		xPhaseSelect = xPhaseSelectList[index]
		c.execute(f"INSERT INTO {tableDesignation} VALUES ({lpgbt}, {ChnCntr}, '{xPhaseSelect}', '{PS0Config}', '{PS1Config}', '{PS2Config}', '{PS3Config}', '{EPCLK2ChnCntrH}', '{EPCLK2ChnCntrL}', '{EPCLK0ChnCntrH}', '{EPCLK0ChnCntrL}');")
	print("Done with lpgbt")


# Commit the changes
conn.commit()

# Close our connection
conn.close()

"""
