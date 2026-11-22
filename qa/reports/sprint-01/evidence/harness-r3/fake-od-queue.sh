#!/bin/sh
# fake od: serves next line from queue file $FAKE_OD_Q (each line = decimal bytes)
q=$FAKE_OD_Q
case "${FAKE_OD_MODE:-queue}" in
 fail) exit 1;;
 failpartial) echo "1 2 3"; exit 1;;
 empty) exit 0;;
 garbage) echo "abc def"; exit 0;;
 short) echo " 1 2 3 4"; exit 0;;
 long) python3 -c 'print(*range(33))'; exit 0;;
 big) python3 -c 'print(*([256]*32))'; exit 0;;
 neg) python3 -c 'print(*([-1]*32))'; exit 0;;
 const) python3 -c 'print(*([7]*32))'; exit 0;;
 slow) sleep 3; python3 -c 'print(*range(32))'; exit 0;;
esac
n=$(cat "$q.n" 2>/dev/null || echo 0); n=$((n+1)); echo $n > "$q.n"
sed -n "${n}p" "$q"
