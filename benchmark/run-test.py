import subprocess
import sys
import os

def modify_and_run(smallest_rate, highest_rate, num_nodes, num_runs):
    if not os.path.exists("results"):
        os.makedirs("results")
    for rate in range(smallest_rate, highest_rate + 1, 10_000):
        with open("fabfile.py", "r") as file:
            lines = file.readlines()

        with open("fabfile.py", "w") as file:
            for line in lines:
                if "'rate':" in line:
                    file.write(f"        'rate': {rate},\n")
                elif "'nodes':" in line:
                    file.write(f"        'nodes': {num_nodes},\n")
                else:
                    file.write(line)

        # Run the benchmark for the specified number of runs
        for run in range(1, num_runs + 1):
            output_file = f"results/bench-1-{num_nodes}-{rate}-512.txt"
            with open(output_file, "a") as f:
                # Run the localmal task using Fabric
                result = subprocess.run(
                    ["fab", "localmal"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                print(f"Running experiment number {run} with rate {rate}\n")
                f.write(result.stdout)

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python script.py <smallest_rate> <highest_rate> <num_nodes> <num_runs>")
        sys.exit(1)

    smallest_rate = int(sys.argv[1])
    highest_rate = int(sys.argv[2])
    num_nodes = int(sys.argv[3])
    num_runs = int(sys.argv[4])

    modify_and_run(smallest_rate, highest_rate, num_nodes, num_runs)
