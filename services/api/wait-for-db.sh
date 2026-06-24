#!/bin/sh
# wait-for-db.sh

set -e

host="$1"
port="$2"
shift 2
cmd="$@"

until nc -z "$host" "$port"; do
  echo "Waiting for db at $host:$port..."
  sleep 1
done

echo "db is up - executing command"
exec $cmd
