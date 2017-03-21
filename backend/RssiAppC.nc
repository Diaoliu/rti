#include "RssiAppC.h"

configuration RssiAppC {}

implementation
{
  components RssiC, MainC;
  components PrintfC;
  components SerialStartC;
  components ActiveMessageC;
  components new TimerMilliC() as Timer;
  components CC2420ActiveMessageC;
  components new AMSenderC(AM_RSSI);
  components new AMReceiverC(AM_RSSI);

  RssiC.Boot -> MainC;
  RssiC.Timer -> Timer;
  RssiC.RadioControl -> ActiveMessageC;
  RssiC.Packet -> AMSenderC;
  RssiC.AMSend -> AMSenderC;
  RssiC.Receive -> AMReceiverC;
  RssiC.CC2420Packet -> CC2420ActiveMessageC;
}
