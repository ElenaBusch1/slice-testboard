#!/bin/bash
#copy runs to a designated directory
#raw=/nevis/kolya/home/kpark/slice-testboard/data/Raw
#change user 
user=kpark
ana=/nevis/kolya/home/$user/slice-testboard/analysis
raw=/nevis/kolya/home/$user/practice
pro=/nevis/kolya/home/$user/slice-testboard/data/Processed
www=/nevis/kolya/home/$user/WWW/TestBoard/NoiseResults

run_old=0461
html_temp=/nevis/kolya/home/kpark/WWW/TestBoard/NoiseResults/run${run_old}_NoiseResults.html
#html_temp=/nevis/kolya/home/acs2325/WWW/TestBoard/NoiseResults/header.html


read -r -p "Enter run numbers\n " -a runs
#-n for not overwriting files
for run in "${runs[@]}";do
	cp -n /nevis/xenia2/data/users/jgonski/FLX/slice-testboard/Runs/run${run}.hdf5 ${raw}
	
done

#run convert.py and PedAnalysis_slice.py
#note you have to ensure that channels are in decimal with '10#' even if it might have a zero in front of it ex) 010 = 10 not 8 in octal
cd $ana
#conda activate coluta
#to run this, you should already have 
mkdir -p $www

for run in "${runs[@]}";do
		
	if (($((10#$run)) < 509));then python convert.py run$run
	elif(($((10#$run)) >=509 )); then python convert.py run$run
	else echo "ERROR: wrong run number"
	fi 
	
	python PedAnalysis_slice.py run$run  
	
	cd $www
	mkdir -p $www/Run_${run}
	#make sure the file name starts with small r not big R
	
	plo=$pro/run${run}/Plots/*
	cp -r ${plo}  $www/Run_${run}
	html_new=$www/run${run}_NoiseResults.html
	cp $html_temp $html_new
	sed -i -e "s/${run_old}/${run}/g" ${html_new} || echo "ERROR: html cannot been updated"

done

#unset runs
	
