#!/bin/bash

NUMBER=10
FILENAME="./results-check/15nodes/results-our"
#FILENAME="./test/results-base"

for ((network_delay=10; network_delay<140; network_delay+=10)); do
	echo "tx size is now ${network_delay}"
	
	#echo "Changing line in reliable_sender.rs"
	#sed -i 's/gen_range(0,.*/gen_range(0,'${network_delay}');/' ../network/src/reliable_sender.rs

	#echo "Changing line in simple_sender.rs"
	#sed -i 's/gen_range(0,.*/gen_range(0,'${network_delay}');/' ../network/src/simple_sender.rs
	#echo "Changing input rate"
	#sed -i "s/'rate':.*/'rate': "${network_delay}"_000,/" fabfile.py

	#echo "Changing tx size"
	#sed -i "s/'tx_size':.*/'tx_size': "${network_delay}",/" fabfile.py
	echo "Changing network delay"
	sed -i 's/"network_delay".*/"network_delay": '${network_delay}',/g' ./benchmark/.network_params.json
	#python3 get-results.py
	
	for i in $(seq 0 1 9); do
		echo "Running test number ${i}"
		fab localmal &> ${FILENAME}-run-${i}-delay-${network_delay}
	done
done
