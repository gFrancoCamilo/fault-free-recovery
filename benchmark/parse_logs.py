from datetime import datetime
from glob import glob
from multiprocessing import Pool
from os.path import join
from re import findall, search
from statistics import mean
from collections import Counter
import sys
import matplotlib.pyplot as plt

from benchmark.utils import Print

def parse_nodes(log):
    if search(r'panic', log) is not None:
        raise Exception('Node(s) panicked')

    tmp = findall(r'\[(.*Z) .* Created B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    proposals = merge_results([tmp])

    tmp = findall(r'\[(.*Z) .* Committed B\d+ -> ([^ ]+=)', log)
    tmp = [(d, to_posix(t)) for t, d in tmp]
    commits = merge_results([tmp])

    tmp = findall(r'\[(.*Z) .* Sending new sync request to this.', log)
    tmp = [to_posix(t) for t in tmp]
    start_sync = tmp
    print('Start: ' + str(start_sync))

    tmp = findall(r'\[(.*Z) .* Updated Firewall, which now is.', log)
    tmp = [to_posix(t) for t in tmp]
    end_sync = tmp
    print('End: ' + str(end_sync))

    tmp = findall(r'Batch ([^ ]+) contains (\d+) B', log)
    sizes = {d: int(s) for d, s in tmp}

    return proposals, commits, sizes

def consensus_throughput(commits, proposals, sizes, size):
    if not commits:
        return 0, 0, 0
    start, end = min(proposals.values()), max(commits.values())
    duration = end - start
    bytes = sum(sizes.values())
    bps = bytes / duration
    tps = bps / size[0]
    return tps, bps, duration


def to_posix(string):
    x = datetime.fromisoformat(string.replace('Z', '+00:00'))
    return datetime.timestamp(x)

def log_filename(nodes):
    files = ['./logs/node-' + str(i) +'.log' for i in range(nodes)]
    return files

def merge_results(input):
    # Keep the earliest timestamp.
    merged = {}
    for x in input:
        for k, v in x:
            if not k in merged or merged[k] > v:
                merged[k] = v
    return merged

def count_commits_in_intervals(commits):
    if not commits:
        return {}

    interval_length = 5  # seconds
    interval_counts = {}

    for commit_time, _ in commits:
        interval_start = commit_time
        #interval_counts[interval_start] =

    return interval_counts


def main():
    if len(sys.argv) < 2:
        print("Please enter the number of nodes as arguments")
        print("USAGE: python3 parse_nodes.py <nodes>")
        return -1
    files = log_filename(int(sys.argv[1]))
    logs = []
    for file in files:
        with open(file, 'r') as f:
            logs += [f.read()]

    try:
        with Pool() as p:
            results = p.map(parse_nodes, logs)
    except (ValueError, IndexError) as e:
        raise Exception(f'Failed to parse node logs: {e}')

    proposals, commit, sizes \
        = zip(*results)

    #proposals, commits, sizes = parse_nodes(logs[0])
    commits = merge_results([x.items() for x in commit])
    counter = Counter(commits.values())

    test = [x.items() for x in commit]
    commit_two = merge_results([test[0], test[1]])
    print(commit_two)
    sizes_test = [x.items() for x in sizes]
    sizes_two = merge_results(sizes_test)

    counter_two = Counter(commit_two.values())
    commit_two = {k: v for k, v in sorted(commit_two.items(), key=lambda item: item[1])}
    execution_time = max(commit_two.values())-min(commit_two.values())
    min_time = min(commit_two.values())
    
    tps = []
    x = []
    for i in range(5,int(execution_time) + 5 + 5, 5):
        x.append(i)
        bps_accumulator = 0
        for key in commit_two:
            if commit_two[key] - min_time > i - 5 and commit_two[key] - min_time < i:
                bps_accumulator += sizes_two[key]
        tps.append(bps_accumulator/512)

    plt.plot(x, tps)
    ax = plt.gca()
    ax.set_xticklabels(['0', '[0,5]', '[5,10]', '[10,15]', '[15,20]', '[20,25]', '[25,30]', '[30,35]', '[35,40]'])
    plt.grid()
    plt.ylabel('Number of transactions')
    plt.xlabel('Time Interval (s)')
    plt.axvspan(25.5, 35, color='blue', alpha=0.15, lw=0)
    plt.savefig('tps_recovery.pdf')
    plt.clf()


    x, y = [], []
    for value in counter_two:
        x += [value]
        y += [counter_two[value]]

    x = [i-x[0] for i in x]
    print('x: ' + str(x))
    print('y: ' + str(y))
    plt.scatter(x,y)
    plt.grid()
    plt.ylabel('Number of commits')
    plt.xlabel('Time (s)')
    plt.axvspan(25.5, 34.5, color='blue', alpha=0.15, lw=0)
    plt.savefig('number_commits.pdf')

    return
    proposals = merge_results([x.items() for x in proposals])
    sizes = {
        k: v for x in sizes for k, v in x.items() if k in commits
    }

main()
