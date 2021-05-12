#!/bin/bash
#copy runs to a designated directory
#raw=/nevis/kolya/home/kpark/slice-testboard/data/Raw
#CHANGE $user
#currently only works for trigger data; might not work for single adc 
echo "make sure to 1) change the user variable within the bash script 2) run the command - conda activate coluta before running it"
user=kpark
echo $1
if [ $1 == "-y" ]; then ped_bool=true
elif [ $1 == "-n" ];then ped_bool=false 
else echo "ERROR: type in -y for running PedAnalysis again or -n for not running it ex) bash ./bash_file_name.sh -y" &&exit #whether to run PedAnalysis_slice.py again 
fi
echo ped_bool
ana=/nevis/kolya/home/$user/slice-testboard/analysis
raw=/nevis/kolya/home/$user/slice-testboard/data/Raw
pro=/nevis/kolya/home/$user/slice-testboard/data/Processed
www=/nevis/kolya/home/$user/WWW/TestBoard/NoiseResults

run_temp=0000
html_temp_sum=/nevis/kolya/home/acs2325/WWW/TestBoard/NoiseResults/run${run_temp}_summary.html
html_temp_cha=/nevis/kolya/home/acs2325/WWW/TestBoard/NoiseResults/run${run_temp}_all.html

read -r -p "Enter run numbers (write in 4 digits ex) 0558 instead of 558). " -a runs
#-n for not overwriting files
for run in "${runs[@]}";do
	cp -n /nevis/xenia2/data/users/jgonski/FLX/slice-testboard/Runs/run${run}.hdf5 ${raw}
	
done

#run convert.py and PedAnalysis_slice.py
#note you have to ensure that channels are in decimal with '10#' even if it might have a zero in front of it ex) 010 = 10 not 8 in octal
cp -n /nevis/kolya/home/acs2325/WWW/mystyle.css $www/../../
echo $www/../../
#conda activate coluta
 

#checks if processed files exist 
for run in "${runs[@]}";do
	cd $ana
	shopt -s nullglob dotglob
	if [ ! -f $pro/run${run}/Data_Normal.hdf5 ];then  echo 'needs converting' #check if it's already converted
		if (($((10#$run)) < 509));then python convert.py run$run 1
		elif(($((10#$run)) >=509 )); then python convert.py run$run
		else echo "ERROR: wrong run number"
		fi
	else echo "the run$run is already converted"
	fi 
	
	plot_f=($pro/run${run}/Plots/*)
		#change this to == not !=
	if (( ${#plot_f[@]} == 0 || $ped_bool==true )); 	
	then echo "running PedAnalysis_slice.py" && python PedAnalysis_slice.py run$run
	else echo "At least one plot already exists: Make sure all plots are already made."
        fi


	cd $www
	mkdir -p $www/run${run}
	#make sure the file name starts with small r not big R
	#possible errors: DRE-Hi_mu_runrun0558.png contains 2 of the term run so currently, we fixed html but in future, we should look into changing PedAnalysis_slice.py	
	plo=$pro/run${run}/Plots/*
	cp -r ${plo}  $www/run${run}
	html_sum=$www/run${run}_summary.html
	html_cha=$www/run${run}_all.html
	cp $html_temp_sum $html_sum
	sed -i -e "s/${run_temp}/${run}/g" ${html_sum} || echo "ERROR: html cannot been updated"
	cp $html_temp_cha $html_cha
	sed -i -e "s/${run_temp}/${run}/g" ${html_cha} || echo "ERROR: html cannot been updated"
done

echo "end of the bash script"

#unset runs

