#!/bin/bash

usage() {
    echo "Usage: $0 <smallest_rate> <highest_rate> <num_nodes> <num_runs>"
    echo "  smallest_rate    : The smallest rate to use for the benchmark"
    echo "  highest_rate     : The highest rate to use for the benchmark"
    echo "  num_nodes        : The number of nodes to use in the benchmark"
    echo "  num_runs         : The number of benchmark runs"
    exit 1
}

if [ $# -ne 4 ]; then
    usage
fi

smallest_rate=$1
highest_rate=$2
num_nodes=$3
num_runs=$4

python run-test.py $smallest_rate $highest_rate $num_nodes $num_runs 

sed -i "s/Faults: 0 nodes/Faults: 1 nodes/g" results/bench-1-*

# Clone the repository if it does not already exist
if [ ! -d "hotstuff" ]; then
    git clone https://github.com/asonnino/hotstuff.git
fi

cd hotstuff/benchmark

cp ../../run-vanilla-local.py .

python run-vanilla-local.py $smallest_rate $highest_rate $num_nodes $num_runs

cp results/* ../../results

cd ../..

rm -rf hotstuff
