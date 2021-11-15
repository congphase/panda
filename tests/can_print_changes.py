#!/usr/bin/env python3
import binascii
import sys
from collections import defaultdict
import os
from bitstring import BitArray

import secrets
import time
from common.realtime import sec_since_boot
import _thread

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from python import Panda  # noqa: E402

GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
ENDC = '\033[0m'

def heartbeat_thread(p):
  while True:
    try:
      p.send_heartbeat()
      time.sleep(0.5)
    except Exception:
      continue


def can_printer(read_bus=2):
  """Collects messages and prints when a new bit transition is observed.
  This is very useful to find signals based on user triggered actions, such as blinkers and seatbelt.
  Leave the script running until no new transitions are seen, then perform the action."""

  low_to_high = defaultdict(int)
  high_to_low = defaultdict(int)

  p = Panda()
  _thread.start_new_thread(heartbeat_thread, (p,))
  p.set_safety_mode(Panda.SAFETY_SILENT)
  p.set_power_save(False)

# Will be very slow!!!
  check_address = 437
  seen = ""
  counter = defaultdict(int)
  IGNORE_LIMIT = 20
  os.system('clear')

  while True:
    incoming = p.can_recv()
    #incoming = [[check_address, 0, secrets.token_bytes(20), read_bus],]
    for msg in incoming:
      address, unused, data, bus = msg
      if address == check_address and bus == read_bus:
        if not seen:
          seen = data
          continue
        out = defaultdict(str)
        is_out = False
        for x in range(len(data)):
          #if data[x] != seen[x]:
          left =(~BitArray(uint=data[x], length=8) | BitArray(uint=seen[x], length=8))
          right = ~(BitArray(uint=data[x], length=8) | ~BitArray(uint=seen[x], length=8))
          res = (~left | right).bin
          #print(f"byte {x} changed")
          for xi in range(len(res)):
            if counter[(x*8) + xi+1] > IGNORE_LIMIT:
              out[x] += f" {RED}X{ENDC}"
            elif res[xi] == '1':
              #print(f"bit {7-xi} in byte {x} changed")
              out[x] += f" {GREEN}1{ENDC}"
              counter[(x*8) + xi+1] += 1
              is_out = True
            else:
              out[x] += " 0"
        if is_out:
          for x in range(0, len(out), 8):
            header = ""
            bits = ""
            for y in range(0, min(len(out)-x, 8)):
              header += "|"+" "*7 + f"{x+y}"+ " "*(7 if (x+y) < 10 else 6)
              bits += out[x+y]
            print(header)
            print(bits, flush=True)
          print("#"*17*8)
        seen = data


  while 1:
    can_recv = p.can_recv()
    for x in can_recv:
      address, unused, data, bus = x
      if bus == read_bus:
        i = int.from_bytes(data, byteorder='big')

        l_h = low_to_high[address]
        h_l = high_to_low[address]

        change = None
        if (i | l_h) != l_h:
          low_to_high[address] = i | l_h
          change = "+"

        if (~i | h_l) != h_l:
          high_to_low[address] = ~i | h_l
          change = "-"

        if change:
          print(f"{sec_since_boot():.2f}\t{hex(address)} ({address})\t{change}{binascii.hexlify(data)}")


if __name__ == "__main__":
  if len(sys.argv) > 1:
    can_printer(int(sys.argv[1]))
  else:
    can_printer()
