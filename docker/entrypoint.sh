#!/bin/bash
set -eo pipefail  # stronger error handling than just 'set -e'

# start services and record the PID
supervisord -c /etc/supervisor/supervisord.conf &
supervisord_pid=$!

# trap SIGTERM and forward to supervisord
_term() {
  echo "Caught SIGTERM! Gracefully shutting down..."
  supervisorctl stop all
  kill -TERM $supervisord_pid 2>/dev/null
  wait $supervisord_pid
  exit 0
}
trap _term TERM

# monitor process health
while sleep 5
do
    if ! supervisorctl status uvicorn | grep -q RUNNING
    then
        echo "uvicorn process crashed"
        break
    fi

    # TODO: add async worker(s)

    if ! supervisorctl status nginx | grep -q RUNNING
    then
        echo "nginx process crashed"
        break
    fi
done

# cleanup if loop exits unexpectedly
kill -15 $supervisord_pid
wait $supervisord_pid
exit $?