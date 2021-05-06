

def takeTriggerData(GUI, measType):
    """Runs takeTriggerData script"""
    # Collect metadata
    GUI.runType = measType
    GUI.daqMode = 'trigger'
    GUI.daqADCSelect = '20'

    # Establish output file
    if not os.path.exists("Runs"):
        os.makedirs("Runs")
    if GUI.opened:
        GUI.incrementRunNumber()
        GUI.opened = False  
    outputDirectory = 'Runs'
    outputFile = "run"+str(GUI.runNumber).zfill(4)+".dat"
    stampedOutputFile = "run"+str(GUI.runNumber).zfill(4)+"-1.dat"
    outputPath = outputDirectory+"/"+outputFile
    outputPathStamped = outputDirectory+"/"+stampedOutputFile

    subprocess.call("python takeTriggerData.py -o "+outputPath+" -t "+GUI.daqMode+" -a "+GUI.daqADCSelect, shell=True)
    time.sleep(5)
    parseDataMod.main(GUI, outputPathStamped)
    saveBin = False
    if not saveBin:
        print("Removing "+outputPathStamped)
        subprocess.call("rm "+outputPathStamped, shell=True)

