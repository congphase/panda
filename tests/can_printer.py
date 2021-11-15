#!/usr/bin/env python3

import os
import sys
import time
from collections import defaultdict
import binascii
import _thread

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from python import Panda  # noqa: E402

def heartbeat_thread(p):
  while True:
    try:
      p.send_heartbeat()
      time.sleep(0.5)
    except Exception:
      continue

# fake
def sec_since_boot():
  return time.time()

def can_printer():
  p = Panda()
  #p.set_can_speed_kbps(0, 500)
  #p.set_can_data_speed_kbps(0, 2000)
  #p.set_safety_mode(Panda.SAFETY_SILENT)

  start = sec_since_boot()
  lp = sec_since_boot()
  msgs = defaultdict(list)
  canbus = int(os.getenv("CAN", "0"))
  canbus = 2
  while True:
    can_recv = p.can_recv()
    for address, _, dat, src in can_recv:
      if src == canbus and address < 944:
        msgs[address].append(dat)

    if sec_since_boot() - lp > 0.1:
      dd = chr(27) + "[2J"
      dd += "%5.2f\n" % (sec_since_boot() - start)
      for k, v in sorted(zip(list(msgs.keys()), [binascii.hexlify(x[-1]) for x in list(msgs.values())])):
        dd += "%s(%6d) %s\n" % ("%04X(%4d)" % (k, k), len(msgs[k]), v)
      print(dd)
      lp = sec_since_boot()

if __name__ == "__main__":
  can_printer()
