// board enforces
//   in-state
//      accel set/resume
//   out-state
//      cancel button
//      accel rising edge
//      brake rising edge
//      brake > 0mph

#define FORD_WHEEL_SPEED              (0x217)
#define FORD_STEERING_BUTTONS         (0x83)
#define FORD_CRUISE_STATUS            (0x165)
#define FORD_ENGINE_DATA              (0x204)
#define FORD_LKA_CONTROL              (0x3CA)
#define FORD_LKA_UI                   (0x3D8)
#define FORD_PARKAID_DATA             (0x3A8)
#define FORD_ENG_VEHICLE_SP_THROTTLE  (0x202)
#define FORD_BRAKE_SYS_FEATURES       (0x415)

const struct lookup_t FORD_LOOKUP_ANGLE_RATE_UP = {
  {2., 7., 17.},
  {5., .8, .15}
};

const struct lookup_t FORD_LOOKUP_ANGLE_RATE_DOWN = {
  {2., 7., 17.},
  {5., 3.5, 0.4}
};

const int FORD_DEG_TO_CAN = 10;

static int ford_rx_hook(CAN_FIFOMailBox_TypeDef *to_push)
{
  int bus = GET_BUS(to_push);
  int addr = GET_ADDR(to_push);

  if (bus == 0)
  {
    if (addr == FORD_BRAKE_SYS_FEATURES)
    {
      vehicle_speed = ((GET_BYTE(to_push, 0) << 8) | (GET_BYTE(to_push, 1))) * 0.01 / 3.6;
    }

    if (addr == FORD_CRUISE_STATUS)
    {
      int cruise_state = (GET_BYTE(to_push, 1) & 0x7);
      bool cruise_engaged = (cruise_state != 0) && (cruise_state != 3);

      if (cruise_engaged && !cruise_engaged_prev)
      {
        controls_allowed = 1;
      }

      if (!cruise_engaged)
      {
        controls_allowed = 0;
      }

      cruise_engaged_prev = cruise_engaged;
    }
  }

  return 1;
}

// all commands: just steering
// if controls_allowed and no pedals pressed
//     allow all commands up to limit
// else
//     block all commands that produce actuation

static int ford_tx_hook(CAN_FIFOMailBox_TypeDef *to_send)
{
  return 1;
  int tx = 1;
  int addr = GET_ADDR(to_send);
  bool violation = false;

  if (relay_malfunction)
  {
    tx = 0;
  }

  if (addr == FORD_PARKAID_DATA)
  {
    // Steering control: (0.1 * val) - 1000 in deg.
    // We use 1/10 deg as a unit here
    int raw_angle_can = (((GET_BYTE(to_send, 2) & 0x7F) << 8) | GET_BYTE(to_send, 3));
    int desired_angle = raw_angle_can - 10000;
    bool steer_enabled = (GET_BYTE(to_send, 2) >> 7);

    // Rate limit check
    if (controls_allowed && steer_enabled)
    {
      float delta_angle_float;
      delta_angle_float = (interpolate(FORD_LOOKUP_ANGLE_RATE_UP, vehicle_speed) * FORD_DEG_TO_CAN);
      int delta_angle_up = (int)(delta_angle_float) + 1;
      delta_angle_float =  (interpolate(FORD_LOOKUP_ANGLE_RATE_DOWN, vehicle_speed) * FORD_DEG_TO_CAN);
      int delta_angle_down = (int)(delta_angle_float) + 1;
      int highest_desired_angle = desired_angle_last + ((desired_angle_last > 0) ? delta_angle_up : delta_angle_down);
      int lowest_desired_angle = desired_angle_last - ((desired_angle_last >= 0) ? delta_angle_down : delta_angle_up);
      violation |= max_limit_check(desired_angle, highest_desired_angle, lowest_desired_angle);
    }

    desired_angle_last = desired_angle;

    if (!controls_allowed && steer_enabled)
    {
      violation = true;
    }
  }

  if (violation)
  {
    tx = 0;
    controls_allowed = 0;
  }
  return tx;
}

static int ford_fwd_hook(int bus_num, CAN_FIFOMailBox_TypeDef *to_fwd)
{
  int bus_fwd = -1;
  int addr = GET_ADDR(to_fwd);

  if (!relay_malfunction)
  {
    if ((bus_num == 0) && (addr != FORD_ENG_VEHICLE_SP_THROTTLE) && 
        (addr != FORD_PARKAID_DATA) && (addr != FORD_BRAKE_SYS_FEATURES))
    {
      bus_fwd = 2;
    } 
    else if ((bus_num == 2) && (addr != FORD_LKA_CONTROL) && (addr != FORD_LKA_UI))
    {
      bus_fwd = 0;
    }
  }

  return bus_fwd;
}

const safety_hooks ford_hooks = {
  .init = nooutput_init,
  .rx = ford_rx_hook,
  .tx = ford_tx_hook,
  .tx_lin = nooutput_tx_lin_hook,
  .fwd = ford_fwd_hook,
};
