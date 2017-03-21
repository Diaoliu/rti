#ifndef RSSI_APP_C_h
#define RSSI_APP_C_h

#define AM_RSSI 6
#define NODES 6
#define EVER ;;
#define NEW_PRINTF_SEMANTICS

typedef nx_struct link_msg
{
	nx_uint8_t id;
	/* map <src, rssi> */
	nx_uint16_t rssi[NODES];
} link_msg;

#endif

