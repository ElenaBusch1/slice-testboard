import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit

def make_4x4_hist(all_data,asic_num,input_dir = "pp"):

    ASIC = "ASIC" + str(asic_num)
    if input_dir == "pp": title = "Peak-Peak Crosstalk Amplitude [%]" 
    elif input_dir == "OFC": title = "OFC Application to Crosstalk [%]" 
    else: return "please specify either ~pp~ or ~OFC~ as input"

    channels = ["5","6","7","8"]

    '''
    all_data = []
    for channel in channels:
        
        f = open("/data2/users/acs2325/coluta_runs/" + input_dir + "/ch_" + channel + ".txt","r")

        for line in f.readlines():

            data = line.split(", ")
            data = data[:-1]
            data = [np.round(float(x),5) for x in data] 
            print(channel,data)

        all_data.append(data)
 
    f.close()
    '''


   
    all_data = np.asarray(all_data)

    print(np.shape(all_data))
    fig, ax = plt.subplots()
    im = ax.imshow(all_data, cmap = "Blues")
 
    #plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
    #     rotation_mode="anchor")

    ax.set_xticks(np.arange(len(channels)))
    ax.set_yticks(np.arange(len(channels)))
    ax.set_xticklabels(channels)
    ax.set_yticklabels(channels)

    for i in range(len(channels)):
      for j in range(len(channels)):
        if i == j: color = "w"
        else: color = "k"
        text = ax.text(j, i, all_data[i, j],
                       ha="center", va="center", color=color)

    for edge, spine in ax.spines.items():
        spine.set_visible(False)
    #fig.colorbar(im)
    ax.set_title(title)
    #ax.set_ylim([-0.5,3.5])
    #ax.set_xlim([-0.5,3.5])
    ax.set_xticks(np.arange(len(channels)+1)-.5, minor=True)
    ax.set_yticks(np.arange(len(channels)+1)-.5, minor=True)
    ax.grid(which = "minor", color="w", linestyle='-', linewidth=3)
    ax.set_ylabel("Pulsed Channel")
    ax.set_xlabel("Crosstalk Channel")
    fig.tight_layout()
    plt.savefig("/nevis/kolya/home/acs2325/colutaanalysis/PDRPlots/xtalk/" +  ASIC + "/" + input_dir  + "_4x4_rounded.pdf")
    plt.close()
    plt.clf()


    return


all_data = [[100.0, 0.01, 0.007, 0.004],\
[0.01, 100.0, 0.007, 0.007],\
[0.002, 0.004, 100.0, 0.006],\
[0.002, 0.003, 0.003, 100.0]]
make_4x4_hist(all_data,10,"pp")

all_data = [[100.0, 0.0002, 0.001, 0.002],\
[0.0004, 100.0, 0.002, 0.002],\
[0.0001, 0.0001, 100.0, 0.002],\
[0.0001, 0.0008, 0.0002, 100.0]]

make_4x4_hist(all_data,10,"OFC")

all_data = [[100.0, 0.01, 0.007, 0.004],\
[0.01, 100.0, 0.007, 0.004],\
[0.003, 0.004, 100.0, 0.004],\
[0.003, 0.003, 0.004, 100.0]]
make_4x4_hist(all_data,12,"pp")

all_data = [[100.0, 6e-5, 0.002, 0.001],\
[0.0008, 100.0, 0.002, 0.001],\
[0.0002, 7e-5, 100.0, 0.002],\
[0.0004, 0.0003, 0.0009, 100.0]]
make_4x4_hist(all_data,12,"OFC")
