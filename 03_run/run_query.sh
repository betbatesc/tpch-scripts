#!/usr/bin/env bash
# @betbatesc

usage() {
    echo "Usage: $0 --db <db> [--output <file>]"
    echo "Run a customized query and report timing"
    echo ""
    echo "Options:"
    echo "  -d, --db <db>         The database"
    echo "  -o, --output <file>   Where to append output, Default=query_timing.csv"
    echo "  -p, --port <port>     Port number where the server is listening"
    echo "  -q, --query <query>   Query to be run on the database"
    echo "  -v, --verbose         More output"
    echo "  -h, --help            This message"
}

dbname=
port=50010
output=
query=

while [ "$#" -gt 0 ]
do
    case "$1" in
        -d|--db)
            dbname=$2
            shift
            shift
            ;;
        -p|--port)
            port=$2
            shift
            shift
            ;;
        -o|--output)
            output=$2
            shift
            shift
            ;;
        -q|--query)
            query=$2
            shift
            shift
            ;;
        -v|--verbose)
            set -x
            set -v
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "$0: unkown argument $1"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$dbname" ]; then
    usage
    exit 1
fi

if [ -z "$output" ]; then
    output="query_timing.csv"
fi

if [ -z "$query" ]; then
    query="select * from nation;"
fi

TIMEFORMAT="%R"

today=$(date +%Y-%m-%d)

echo "### Free memory before the run: ###" | tee -a "$output"
echo "$(free -h)" | tee -a "$output"

echo "# Database, Query, Time" | tee -a "$output"

echo "Running query: $query"

echo "$query" > "/tmp/query"

s=$(date +%s.%N)
mclient -d "$dbname" -p "$port" -f raw -w 80 -i < "/tmp/query" 2>&1 >/dev/null
x=$(date +%s.%N)

elapsed=$(echo "scale=4; $x - $s" | bc)

echo "$dbname, $query, $elapsed" | tee -a "$output"



