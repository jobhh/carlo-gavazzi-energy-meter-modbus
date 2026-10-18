# Captured meters

Each JSON file here is a register dump from a real meter, saved with:

```bash
python script/query.py <target> --unit <id> --dump tests/captures/<name>.json
```

`tests/test_captures.py` replays every file through the library and checks
that independent registers agree: the phase powers add up to the system
power, the line voltages match the phase voltages, and the 64-bit counters
match their 32-bit copies. A wrong word order or scale breaks those checks.

Name a file after the model and firmware, such as `em540-pfc-fw4.3.2.json`.
The script writes `XX0000000000X` in place of the meter's serial number, and
a test fails for any capture that holds another one.
