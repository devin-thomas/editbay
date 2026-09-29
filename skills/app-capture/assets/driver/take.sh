#!/bin/bash
# Record one scripted take: the simulator's screen (HEVC) while xcodebuild runs one UI test.
# Usage: ./take.sh <udid> <NAME> <TestClass/testMethod>
# Writes ../takes/NAME.mov, NAME.clock (wall time of "Recording started"), NAME.events (EVT lines), NAME.xcodebuild.log.
# Notes: the recorder cannot write to some external volumes (permission error), so it records to $TMPDIR and moves;
# a failed UI test can leave xcodebuild collecting diagnostics for minutes, hence the watchdog.
set -u
cd "$(dirname "$0")"
UDID="$1"; NAME="$2"; TEST="$3"
OUT=../takes; mkdir -p "$OUT"
RAW="${TMPDIR:-/tmp}/performer-raw"; mkdir -p "$RAW"
DD="${TMPDIR:-/tmp}/performer-dd"
python3 -c "import time;print('rec.launch', repr(time.time()))" > "$OUT/$NAME.clock"
xcrun simctl io "$UDID" recordVideo --codec hevc --force "$RAW/$NAME.mov" 2> >(while IFS= read -r l; do python3 -c "import time,sys;print('rec', repr(time.time()), sys.argv[1])" "$l"; done >> "$OUT/$NAME.clock") &
RPID=$!
sleep 2
xcodebuild test -project Performer.xcodeproj -scheme Performer -destination "id=$UDID" -derivedDataPath "$DD" -only-testing:"PerformerUITests/$TEST" > "$OUT/$NAME.xcodebuild.log" 2>&1 &
XPID=$!
for i in $(seq 1 ${LIMIT:-150}); do kill -0 $XPID 2>/dev/null || break; grep -q "Test Suite 'Selected tests' \(passed\|failed\)" "$OUT/$NAME.xcodebuild.log" && { sleep 2; break; }; sleep 1; done
kill $XPID 2>/dev/null; wait $XPID 2>/dev/null
sleep 1
kill -INT $RPID 2>/dev/null; pkill -INT -f "recordVideo --codec hevc --force $RAW/$NAME.mov" 2>/dev/null
sleep 3
mv "$RAW/$NAME.mov" "$OUT/$NAME.mov"
grep -h "EVT " "$OUT/$NAME.xcodebuild.log" | sed 's/^.*EVT /EVT /' | sort -u -k2,2 > "$OUT/$NAME.events"
grep -E "TEST (SUCCEEDED|FAILED)|Selected tests' (passed|failed)" "$OUT/$NAME.xcodebuild.log" | tail -1
