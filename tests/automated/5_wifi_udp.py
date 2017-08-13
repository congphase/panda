from __future__ import print_function
import sys
import time
from helpers import time_many_sends
from panda import Panda, PandaWifiStreaming
from nose.tools import timed, assert_equal, assert_less, assert_greater

def test_udp_doesnt_drop():
  p = Panda()
  p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
  p.set_can_loopback(True)

  pwifi = PandaWifiStreaming()
  pwifi.can_recv()

  for msg_count in [1, 100]:
    for i in range({1: 0x80, 100: 0x10}[msg_count]):
      pwifi.kick()

      speed = 500
      p.set_can_speed_kbps(0, speed)
      comp_kbps = time_many_sends(p, 0, pwifi, msg_count=msg_count, msg_id=0x100+i)
      saturation_pct = (comp_kbps/speed) * 100.0

      if msg_count == 1:
        sys.stdout.write(".")
        sys.stdout.flush()
      else:
        print("UDP WIFI loopback %d messages at speed %d, comp speed is %.2f, percent %.2f" % (msg_count, speed, comp_kbps, saturation_pct))
        assert_greater(saturation_pct, 60)
        assert_less(saturation_pct, 100)
    print("")



