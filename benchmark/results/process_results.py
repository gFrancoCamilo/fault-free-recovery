import numpy as np
import scipy.stats as st
import matplotlib as mpl
mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = r'\usepackage{libertine}'
import matplotlib.pyplot as plt
import os
import re


def import_files():
    prefixed = [filename for filename in os.listdir('.') if filename.startswith("result-")]
    prefixed.sort()
    return prefixed

def get_stat(filename, stat):
    with open(filename, 'r') as f:
        file_content = f.read()
        match stat:
            case "consensus-tps":
                match_string = re.search(r"Consensus TPS:\s(.*) tx/s", file_content)
                return match_string.group(1).replace(",","")
            case "consensus-bps":
                match_string = re.search(r"Consensus BPS:\s(.*) B/s", file_content)
                return match_string.group(1).replace(",","")
            case "consensus-latency":
                match_string = re.search(r"End-to-end latency:\s(.*) ms", file_content)
                return match_string.group(1).replace(",","")
            case "e2e-tps":
                match_string = re.search(r"End-to-end TPS:\s(.*) tx/s", file_content)
                return match_string.group(1).replace(",","")
            case "e2e-bps":
                match_string = re.search(r"End-to-end BPS:\s(.*) B/s", file_content)
                return match_string.group(1).replace(",","")
            case "e2e-latency":
                match_string = re.search(r"End-to-end latency:\s(.*) ms", file_content)
                return match_string.group(1).replace(",","")

def results_to_stats(original, our, stat):
    original_mean = np.mean(original)
    our_mean = np.mean(our)

    err_original = 1.96*np.std(original)/np.sqrt(10)
    err_our = 1.96*np.std(our)/np.sqrt(10)
    print_stat((original_mean, err_original), (our_mean, err_our), stat)

def print_stat (original, our, stat):
    print("------------------------------------");
    print(" Results for stat: {}".format(stat));
    print("------------------------------------");
    print("Original:{} +/- {:.1f}".format(original[0], original[1]));
    print("Our: {} +/- {:.1f}".format(our[0], our[1]));
    print("------------------------------------");
    print("\n\n")

def main():
    files = import_files()
    original_results = []
    our_results = []
    #stats = ['consensus-tps','consensus-bps','consensus-latency','e2e-tps','e2e-bps','e2e-latency']
    stats = ['consensus-tps']
    for stat in stats:
        result = []
        for file in files:
            result.append(int(get_stat(file, stat)))
        original_result = result[len(result)//2:]
        our_results = result[:len(result)//2]
        results_to_stats(original_result, our_results, stat)


main()
