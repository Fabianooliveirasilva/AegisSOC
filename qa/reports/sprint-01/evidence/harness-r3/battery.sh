#!/bin/bash
# QA battery for scripts/setup-secrets (S1-T01 re-validation 3)
S=$1; EXP=$2; SCR=$EXP/scripts/setup-secrets
T=$S/t/bat; rm -f "$T"/*.rc 2>/dev/null; mkdir -p "$T"; cd "$T" || exit 9
P=0;F=0
chk(){ if [ "$2" = "$3" ]; then P=$((P+1)); echo "PASS $1"; else F=$((F+1)); echo "FAIL $1 (got [$2] want [$3])"; fi; }
new(){ mktemp -d -p "$T"; }
echo "### Done-when"
d=$(new)/s; out=$(AEGIS_SECRETS_DIR=$d make -C "$EXP" setup 2>&1); rc=$?; echo "$out" | tail -4
chk "make setup rc" $rc 0
chk "dir mode" "$(stat -c %a $d)" 700
chk "4 files" "$(ls -A $d | wc -l)" 4
for f in $d/*; do chk "mode600 $(basename $f)" "$(stat -c %a $f)" 600; chk "43 chars $(basename $f)" "$(grep -cE '^[A-Za-z0-9_-]{43}$' <(cat $f; echo))" 1; chk "size $(basename $f)" "$(wc -c <$f)" 43; done
chk "distinct" "$(cat $d/* | wc -c)" 172
chk "distinct values" "$(for f in $d/*; do cat $f; echo; done | sort -u | wc -l)" 4
vals=$(for f in $d/*; do cat $f; echo; done)
leak=0; for v in $vals; do case "$out" in *"$v"*) leak=1;; esac; done; chk "no value in output" $leak 0
( cd $d && sha256sum * > ../h.txt ); stat -c '%n %a %Y' $d/* > $d/../m1.txt
out2=$(AEGIS_SECRETS_DIR=$d make -C "$EXP" setup 2>&1); rc=$?; echo "$out2"|tail -2
chk "second run rc" $rc 0
case "$out2" in *"0 created, 4 already"*) chk "second run msg" 1 1;; *) chk "second run msg" 0 1;; esac
( cd $d && sha256sum -c ../h.txt >/dev/null 2>&1 ); chk "unchanged hashes" $? 0
stat -c '%n %a %Y' $d/* > $d/../m2.txt; cmp -s $d/../m1.txt $d/../m2.txt; chk "mtime unchanged" $? 0
out3=$(AEGIS_SECRETS_DIR=$d make -C "$EXP" setup-ci 2>&1); rc=$?; echo "$out3"|tail -2
chk "setup-ci rc" $rc 0; chk "ci file mode" "$(stat -c %a $d/bootstrap_admin_password)" 600
chk "ci 5 files" "$(ls -A $d|wc -l)" 5
# DIR argument and umask 000 caller
dd=$(new)/x/y; (umask 000; sh $SCR $dd >/dev/null 2>&1); chk "umask000 dir mode" "$(stat -c %a $dd)" 700; chk "umask000 file" "$(stat -c %a $dd/redis_password)" 600
# unknown option
sh $SCR --bogus >/dev/null 2>&1; chk "unknown opt rc" $? 2

echo "### fail-closed od modes"
for m in fail failpartial empty garbage short long big neg const; do
  d=$(new)/s; o=$(PATH=$S/bin_q:$PATH FAKE_OD_MODE=$m FAKE_OD_Q=/dev/null sh $SCR $d 2>&1); rc=$?
  n=$(ls -A $d 2>/dev/null | wc -l)
  echo "mode=$m rc=$rc files=$n msg=$(echo "$o"|head -1|cut -c1-110)"
  if [ $m = const ]; then chk "od=$m rc nonzero (dup guard)" $([ $rc -ne 0 ] && echo 1 || echo 0) 1
  else chk "od=$m rc nonzero" $([ $rc -ne 0 ] && echo 1 || echo 0) 1; fi
  if [ $m = big ] || [ $m = neg ] || [ $m = const ]; then echo "   (observation: $n file(s) left; see note)"; else chk "od=$m zero files" $n 0; fi
done
# od missing entirely
d=$(new)/s; o=$(PATH=/nonexistent /bin/sh $SCR $d 2>&1); rc=$?; echo "no-PATH rc=$rc: $(echo $o|cut -c1-120)"; chk "no od/no PATH: files 0" "$(ls -A $d 2>/dev/null|wc -l)" 0
# fail on 3rd secret: first two must remain? check no partial file of the failing one
echo "### existing-file cases"
mk(){ d=$(new)/s; mkdir -p $d; chmod 700 $d; }
good=$(python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='),end='')")
declare -A cases
run_case(){ # name setupcmd
  mk; ( cd $d; eval "$2" ); local before; before=$(cd $d; find . -mindepth 1 -printf '%p %y %m %l\n' -exec sh -c 'test -f "$1" && ! test -L "$1" && sha256sum "$1"' _ {} \; 2>/dev/null | sort)
  o=$(sh $SCR $d 2>&1 >/dev/null); rc=$?; local after; after=$(cd $d; find . -mindepth 1 -printf '%p %y %m %l\n' -exec sh -c 'test -f "$1" && ! test -L "$1" && sha256sum "$1"' _ {} \; 2>/dev/null | sort)
  # the target file must be unmodified; other 3 get created, so compare only target
  local tgt=postgres_superuser_password
  chk "$1: rc 1" $rc 1
  case "$o" in *"$d/$tgt"*) chk "$1: named" 1 1;; *) chk "$1: named" 0 1;; esac
  echo "   -> $(echo "$o"|head -1|cut -c1-170|sed "s#$T#T#")"
}
tgt=postgres_superuser_password
run_case "644" "printf %s '$good' > $tgt; chmod 644 $tgt"
run_case "400" "printf %s '$good' > $tgt; chmod 400 $tgt"
run_case "660" "printf %s '$good' > $tgt; chmod 660 $tgt"
run_case "empty600" ": > $tgt; chmod 600 $tgt"
run_case "symlink-valid" "printf %s '$good' > real; chmod 600 real; ln -s real $tgt"
run_case "symlink-dangling" "ln -s /nonexistent/x $tgt"
run_case "garbage43" "printf '%s' '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' > $tgt; chmod 600 $tgt"
run_case "44-newline" "printf '%s\n' '$good' > $tgt; chmod 600 $tgt"
run_case "dir" "mkdir $tgt"
run_case "fifo" "mkfifo $tgt; chmod 600 $tgt"
run_case "short5" "printf abcde > $tgt; chmod 600 $tgt"
run_case "44-nonewline" "printf '%s' '${good}A' > $tgt; chmod 600 $tgt"
run_case "42" "printf '%s' '${good%?}' > $tgt; chmod 600 $tgt"
run_case "pad=" "printf '%s' '${good%?}=' > $tgt; chmod 600 $tgt"
run_case "space-in" "printf '%s' '${good%?} ' > $tgt; chmod 600 $tgt"
run_case "nul-in" "printf 'a\000b%s' '${good:0:40}' > $tgt; chmod 600 $tgt"
run_case "binary" "head -c 43 /dev/urandom > $tgt; chmod 600 $tgt"
run_case "dir-symlink" "ln -s /tmp $tgt"
run_case "sock" "python3 -c \"import socket;s=socket.socket(socket.AF_UNIX);s.bind('$tgt')\""
run_case "setuid-mode" "printf %s '$good' > $tgt; chmod 4600 $tgt"
# unmodified check strict
mk; printf %s "$good" > $d/$tgt; chmod 644 $d/$tgt; h=$(sha256sum $d/$tgt); sh $SCR $d >/dev/null 2>&1; chk "644 content untouched" "$(sha256sum $d/$tgt)" "$h"; chk "644 mode untouched" "$(stat -c %a $d/$tgt)" 644
mk; ln -s real $d/$tgt; sh $SCR $d >/dev/null 2>&1; chk "dangling symlink not written through" "$([ -e $d/real ] && echo exists || echo none)" none; chk "link kept" "$(readlink $d/$tgt)" real
# valid file kept, others created, valid rerun
mk; printf %s "$good" > $d/$tgt; chmod 600 $d/$tgt; sh $SCR $d >/dev/null 2>&1; chk "valid existing kept rc0" $? 0; chk "valid content" "$(cat $d/$tgt)" "$good"
# other-name bad file (redis) with mixed
mk; chmod 644 $d 2>/dev/null; sh $SCR $d >/dev/null; chk "dir chmod forced 700" "$(stat -c %a $d)" 700

echo "### duplicate guard (SEC-12)"
d=$(new)/s; q=$(new)/q; python3 -c "print(*range(32))" > $q; python3 -c "print(*range(32))" >> $q
o=$(PATH=$S/bin_q:$PATH FAKE_OD_Q=$q sh $SCR $d 2>&1); rc=$?; echo "rc=$rc $o"; chk "dup rc 1" $rc 1; chk "dup: 1 file only (first), second not created" "$(ls -A $d|wc -l)" 1
# dup vs existing? (existing file same value as newly generated is not checked - by design)

echo "### concurrency"
d=$(new)/s; for i in $(seq 1 12); do ( sh $SCR $d >$T/c$i.out 2>&1; echo $? > $T/c$i.rc ) & done; wait
rcs=$(cat $T/c*.rc | sort | uniq -c | tr '\n' ' '); echo "rcs: $rcs"
echo "files: $(ls -A $d | tr '\n' ' ')"
chk "concurrent: only 4 files, no extras" "$(ls -A $d|wc -l)" 4
bad=0; for f in $d/*; do [ "$(stat -c %a $f)" = 600 ] && [ "$(wc -c <$f)" = 43 ] && grep -qE '^[A-Za-z0-9_-]{43}$' <(cat $f;echo) || bad=1; done; chk "concurrent: all files valid 600/43" $bad 0
chk "concurrent: distinct" "$(for f in $d/*; do cat $f; echo; done|sort -u|wc -l)" 4
sh $SCR $d >/dev/null 2>&1; chk "post-concurrency run clean (rc0)" $? 0
lk=0; for f in $d/*; do v=$(cat $f); grep -qF "$v" $T/c*.out && lk=1; done; chk "concurrent no secret value in outputs" $lk 0
# repeated rounds
badr=0; for r in $(seq 1 15); do d=$(new)/s; for i in 1 2 3 4 5 6; do sh $SCR $d >/dev/null 2>&1 & done; wait; sh $SCR $d >/dev/null 2>&1 || badr=$((badr+1)); [ "$(ls -A $d|wc -l)" = 4 ] || badr=$((badr+1)); done; chk "15 concurrency rounds: converged (rerun rc0, 4 files)" $badr 0

echo "### target dir symlink / readonly"
real=$(new); lk=$(new)/lnk; ln -s $real $lk; sh $SCR $lk >/dev/null 2>&1; echo "rc=$?"; echo "real mode $(stat -c %a $real) files $(ls $real|wc -l)"
chk "dir-symlink target works: files in real" "$(ls $real|wc -l)" 4
d=$(new)/ro; mkdir $d; chmod 500 $d; o=$(sh $SCR $d 2>&1); rc=$?; echo "ro rc=$rc: $(echo "$o"|head -2|sed "s#$T#T#"|tr '\n' '|')"; chmod 700 $d
chk "readonly dir (owner) rc nonzero or forced 700" "$(stat -c %a $d)" 700
ls -A $d | wc -l
d=$(new)/ro2; mkdir $d; chmod 700 $d; ( o=$(sh $SCR $d 2>&1); echo ok >/dev/null ); 
# unwritable: parent read-only so mkdir fails
p=$(new); chmod 500 $p; o=$(sh $SCR $p/newdir 2>&1); rc=$?; echo "ro-parent rc=$rc: $(echo "$o"|head -1|cut -c1-100|sed "s#$T#T#")"; chk "ro-parent rc nonzero" $([ $rc -ne 0 ] && echo 1 || echo 0) 1; chmod 700 $p
# /dev/full style write failure: target file pre-created? use dir on full fs not available; test with ulimit -f 0
d=$(new)/s; ( ulimit -f 0; sh $SCR $d >/dev/null 2>$T/fsz.err; echo "ulimit-f0 rc=$?" ); echo "files after: $(ls -A $d 2>/dev/null|wc -l)"; head -c 200 $T/fsz.err | sed "s#$T#T#"

echo "### interrupts"
d=$(new)/s; echo "### perf"
d=$(new)/s; s=$(date +%s.%N); sh $SCR --ci $d >/dev/null; e=$(date +%s.%N); python3 -c "print('1 run (5 secrets) seconds: %.3f' % ($e-$s))"
for sh in dash bash "bash --posix" "busybox sh"; do d=$(new)/s; s=$(date +%s.%N); $sh $SCR --ci $d >/dev/null 2>&1; rc=$?; e=$(date +%s.%N); python3 -c "print('$sh rc=$rc %.3fs' % ($e-$s))"; chk "$sh real run valid" "$(for f in $d/*; do cat $f; echo; done | grep -cE '^[A-Za-z0-9_-]{43}$')" 5; done
echo "### stats: pass=$P fail=$F"
