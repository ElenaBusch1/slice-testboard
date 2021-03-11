for name in 23 24 25 26 27 28 29 30; do

    mv ./../data/Raw/run00${name}.hdf5 ./../data/Raw/${name}_testped.hdf5
    python convert.py ${name}
    python PedAnalysis_slice.py ${name}
done
