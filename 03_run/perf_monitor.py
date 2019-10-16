#!/usr/bin/env python3

import argparse
import glob
import os
import random
import re
import sys
import subprocess
import time

class Issue(Exception):
    def __init__(self, msg):
        self.msg = msg

def writer(outfilename, also_stdout):
    outfile = open(outfilename, 'a')

    def write(fmt, *args):
        line = fmt % args
        if also_stdout:
            print(line)
        print(line, file=outfile)
        outfile.flush()

    return write

def qq(s):
    if '"' in s or '\\' in s:
        raise("Oops")
    return '"' + s + '"'

def run(db, queryfile):
    # We assume $PATH is already set for all MonetDB binary files
    # /usr/bin/env searches the PATH for us
    cmd = ['/usr/bin/env', "mclient", '-tperformance', '-fraw', '-d', db, queryfile]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (res, err) = p.communicate()
    except subprocess.CalledProcessError as e:
        print("Query %s triggered an exception:" % queryfile, file=sys.stderr)
        raise e
    
    # Look for something like this: clk: 1297.253 ms
    pattern = re.compile(rb'^clk:\s*(\d+\.\d+)\s*ms\s*$', re.M)
    m = pattern.search(err)
    if not m:
        max = 100
        snippet = err if len(err) <= max else "..." + err[-max:]
        raise Issue("Query %s failed: %r" % (queryfile, snippet))
    return float(m.group(1))

def main(args):
    config = args.name or args.db

    outfilename = config + ".csv"
    if args.output:
        if os.path.isdir(args.output):
            outfilename = os.path.join(args.output, outfilename)
        else:
            outfilename = args.output
    if os.path.exists(outfilename):
        print("Output file %s already exists", outfilename, file=sys.stderr)
        sys.exit(1)
    write = writer(outfilename, not args.silent)
    write("config,seqno,query,exec time,deviation,devpercnt")

    queries = sorted(glob.glob('??.sql'))
    if not queries:
        raise Issue("No queries found")

    # TODO: execute the queries 5 times and compute average as their "normal" exec. times.
    seq = 0
    base_performance = {}
    for q in queries:
        qtimes = []
        for i in range(5):
            qtimes.append(run(args.db, q))
        qtimes.remove(max(qtimes))
        base_performance[q] = sum(qtimes)/len(qtimes)
        # also write this normal time to the output file
        name = "q"+os.path.splitext(os.path.basename(q))[0]
        write("%s,%d,%s,%.2f,%.2f,%.2f%%", qq(config), seq, qq(name), base_performance[q], 0,0)

    # Now the monitoring part
    rnd = random.Random(0)
    done = False
    deadline = time.time() + (args.duration or float("inf"))
    patience = args.patience or 0
    wait = patience
    alert = 0
    while not done:
        seq += 1
        rnd.shuffle(queries)   # randomise query exec.
        for q in queries:
            qtime = run(args.db, q)
            name = "q"+os.path.splitext(os.path.basename(q))[0]
            dev = qtime-base_performance[q]
            devpercnt = dev/base_performance[q]
            devpercnt += random.randint(1,25)/100
            write("%s,%d,%s,%.2f,%.2f,%.2f%%", qq(config), seq, qq(name), qtime, dev, devpercnt)
            if devpercnt > 0.25 and alert == 0:
                wait -= 1
                if wait == 0:
                    alert = 1
                    print("=================> set performance alert!")
            else:
                if devpercnt < 0.25 and alert == 1:
                    wait += 1
                    if wait == patience:
                        alert = 0
                        print("=================> reset performance alert!")
            print("=================> patience: ", wait)

        # we always finish executing a full query set
        if time.time() >= deadline:
            done = True
            break

    print("DONE! Output written to ", outfilename)
    return 0

parser = argparse.ArgumentParser(description='Repeatedly run benchmark queries and monitor the query performance')
parser.add_argument('db',
                    help='Database name')
parser.add_argument('--name', '-n',
                    help='Config name, used to label the results, defaults to database name')
parser.add_argument('--duration', '-d', type=int,
                    help='After this many seconds no new query set is started, 0 or omitted: to continue indefinitely.')
parser.add_argument('--output', '-o',
                    help='File or directory to write output to, defaults to ./<CONFIG>.csv')
parser.add_argument('--silent', action='store_true',
                    help='Do not write the results to stdout')
parser.add_argument('--patience', '-p', type=int,
                    help='Wait for how many degraded queries before giving performance alert, 0: immediately.')

if __name__ == "__main__":
    try:
        args = parser.parse_args()
        status = main(args)
        sys.exit(status or 0)
    except Issue as e:
        print("An error occurred:", e.msg, file=sys.stderr)
        sys.exit(1)