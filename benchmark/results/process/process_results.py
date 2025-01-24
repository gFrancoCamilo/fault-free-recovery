import numpy as np
import scipy.stats as st
import matplotlib as mpl
mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = r'\usepackage{libertine}'
import matplotlib.pyplot as plt
plt.style.use('seaborn-colorblind')
import os
import re


def import_files(txrate):
    prefixed = [filename for filename in os.listdir('.') if filename.startswith("result-") and filename.endswith(str(txrate))]
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
    return ((original_mean, err_original), (our_mean,err_our))

def print_stat (original, our, stat):
    print("------------------------------------");
    print(" Results for stat: {}".format(stat));
    print("------------------------------------");
    print("Original:{} +/- {:.1f}".format(original[0], original[1]));
    print("Our: {} +/- {:.1f}".format(our[0], our[1]));
    print("------------------------------------");
    print("\n\n")

def plot_stats(mean_original, err_original, mean_our, err_our):

    x = [i for i in range(10000,70000,10000)]

    original_err = [err_original, err_original]
    plt.errorbar(x, mean_original, yerr=original_err, ls = 'solid', label='Hotstuff', lw=2)
    our_err = [err_our, err_our]
    plt.errorbar(x, mean_our, yerr=our_err, ls = 'dashed', label='Our approach', lw=2)

    #ax = plt.gca()
    #ax.set_xticklabels(['10,000', '20,000', '30,000', '40,000', '50,000', '60,000'])
    plt.ylabel('Laatency (ms)', fontsize=20);
    plt.xlabel('Transaction rate (tps)', fontsize=20);
    plt.yticks(fontsize=20)
    plt.xticks(fontsize=20)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))
    ax.xaxis.set_major_formatter(mpl.ticker.StrMethodFormatter('{x:,.0f}'))

    plt.legend(bbox_to_anchor=(0, 1.02, 1, 0.2), loc="lower left",
                mode="expand", borderaxespad=0, ncol=2, fontsize=18)

    plt.tight_layout()
    plt.grid()
    plt.savefig('e2e-latency-rate.pdf', dpi=600)

def main():

    mean_plot_our = []
    err_plot_our = []
    mean_plot_original = []
    err_plot_original = []

    for i in range(10,70,10):
        files = import_files(i)
        #stats = ['consensus-tps','consensus-bps','consensus-latency','e2e-tps','e2e-bps','e2e-latency']
        print(files)
        stats = ['e2e-latency']
        original_results = []
        our_results = []
        for stat in stats:
            result = []
            for file in files:
                result.append(int(get_stat(file, stat)))
            print(result)
            original_result = result[:len(result)//2]
            our_results = result[len(result)//2:]
            ((original_mean, err_original), (our_mean, err_our)) = results_to_stats(original_result, our_results, stat)
            mean_plot_original.append(original_mean);
            mean_plot_our.append(our_mean);
            err_plot_our.append(err_our);
            err_plot_original.append(err_original)
    #plot_stats(mean_plot_original, err_plot_original, mean_plot_our, err_plot_our)


main()
