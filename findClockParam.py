import numpy as np
import h5py
import json
from tabulate import tabulate
from termcolor import colored

def readInHDF5(f, coluta):
    try:
        datafile = h5py.File(f, "r")
        d = datafile.get(coluta)
        data = []
        for ch in ["Channel" + str(i) for i in range(1,9)]:
            arr = np.array(d[ch])
            data.append(arr)
        print(colored(f"Reading {f} for {coluta}...", "green"))
        return(data)
    except:
        print(colored(f"Could not read {f} for {coluta}", "red"))
        return(None)
    
    """print(f"reading {f}...")
    datafile = h5py.File(f,'r')
    d = datafile.get(coluta)
    data = []
    for ch in ['Channel'+str(i) for i in range(1,9)]:
        arr = np.array(d[ch])
        data.append(arr)
    return data"""

def getHorizontalScore(A,x,y):
    val = A[y][x]
    if val < 0:
        score = 0
        return score
    
    ## What was the motivation for this algorithm?

    ## moving right
    x1 = (x+1)%16
    rightScore = 0
    while A[y][x1] == val and rightScore < 15:
       rightScore += 1
       x1 = (x1+1)%16

    ## moving left
    x2 = x-1
    leftScore = 0
    while A[y][x2] == val and leftScore < 15: 
       leftScore += 1
       x2 -= 1 #Why isn't this mod 16 like others?
    
    horizontalScore = leftScore + rightScore - abs(leftScore-rightScore)
    if horizontalScore > 15: horizontalScore = 15

    ## moving down
    y1 = (y+1)%16
    downScore = 0
    while A[y1][x] == val and downScore < 15:
        downScore += 1
        y1 = (y1+1)%16
   
    ## moving up
    y2 = y-1
    upScore = 0
    while A[y2][x] == val and upScore < 15:
        upScore += 1
        y2 = (y2-1)%16
    
    verticalScore = upScore + downScore - abs(downScore - upScore)
    if verticalScore > 15: verticalScore = 15

    return int((verticalScore**0.5*horizontalScore)) #- abs(verticalScore - horizontalScore)


def scoreMap(X):
    result = []
    for y in range(0,16):
        result.append([])
        for x in range(0,16):
            score = getHorizontalScore(X,x,y)
            result[y].append(score)
    arr = np.array(result)
    #print(arr)
    return arr

def table(values, row, col):
    val = []
    val.append(["xPhaseSelect -> \n INV/DELAY640 "] + [f"{i}\n" for i in range(16)])
    #val = []
    for i in range(values.shape[0]):
        strRow = []
        for j in range(values[i].shape[0]):
            x = values[i][j]
            if i == row and j == col: strRow.append("*" + str(x) + "*")
            else: strRow.append(str(x))
        val.append(strRow)
    t = tabulate(val, headers = "firstrow", showindex = "always", tablefmt = "psql")
    return(t)

def writeToTable(coluta, maps, data):
    coords = {}

    yscores = [np.array([np.max(row) for row in chmap]) for chmap in maps]
    yArr = np.transpose(np.array(yscores))
    rowscores = [np.prod(tab) for tab in yArr]
    row = np.argmax(rowscores)

    with open(f"clockParams/{coluta}ClockParams.txt", "w") as f:
        f.write("Setting format: (XPhaseSelect, Global INV/DELAY640, lpGBT Phase) \n")
        for i, chmap in enumerate(maps):
            scanResults = data[i]
            col = np.argmax(chmap[row])
            val = scanResults[row][col]
            coord = (col, row, val)
            
            f.write("-------------\n")
            f.write(coluta.upper() + f" - Channel {i+1} \n")
            f.write("Clock Scan Result \n")
            f.write(table(scanResults, row, col))
            f.write("\n \n")
            f.write("Score Map \n")
            f.write(table(chmap, row, col))
            f.write("\n \n")
            f.write("Best Setting: " + str(coord))
            f.write("\n \n")

            coords[f"ch{i+1}"] = coord
     
    return(coords)

def config(results):
    """
    Writes config files for passed coluta. Results is a list of tuples
    """
    try:
        import configparser
    except:
        print("You need the configparser package...")
    
    with open("config/lpGBT_colutaMap.json", "r") as f:
        mapping = json.load(f)

    ## COLUTA config file 
    config = configparser.ConfigParser(delimiters = ":")
    config.optionxform = str    

    for coluta in results.keys():
        for i, ch in enumerate(results[coluta].keys()):
            config[f"Phase{i+1}"] = {"Total": "4", "LPGBTPhase": str(bin(results[coluta][ch][2])[2:].zfill(4))}
        config["Global"] = {"INV640": "0", "DELAY640": str(bin(results[coluta][ch][1])[2:].zfill(3))}
        with open("clock_configs/" + coluta.upper() + ".cfg", "w") as f:
            config.write(f)
    
    ## lpGBT config files   
    for lpgbt in mapping.keys():
        config = configparser.ConfigParser(delimiters = ":")
        config.optionxform = str
        config.read("config/" + lpgbt.replace("gbt", "GBT") + ".cfg")
        for coluta in mapping[lpgbt].keys():
            if coluta in results.keys():
                print(colored("Updating " + lpgbt.replace("gbt", "GBT") + " settings...", "green"))
                for ch in results[coluta].keys():
                    config.set("ChnCntr" + mapping[lpgbt][coluta][ch], "XPhaseSelect", str(bin(results[coluta][ch][0])[2:].zfill(4)))
            else:
                continue
        with open("clock_configs/" + lpgbt.replace("gbt", "GBT") + ".cfg", "w") as f:
            config.write(f)
         
def findParams():
    colutas = ["coluta" + str(i) for i in range(13,21)]
    results = {}
    for coluta in colutas:
        data = readInHDF5("clockScanBoard634Repeat.hdf5", coluta)
        if data == None: continue
        
        maps = [scoreMap(X) for X in data] #Map for each channel
        coords = writeToTable(coluta, maps, data)
        results[coluta] = coords

    return(results)

if __name__ == "__main__":
    results = findParams()
    config(results)
