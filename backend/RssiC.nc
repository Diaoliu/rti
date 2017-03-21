#include "printf.h"
#include "RssiAppC.h"

module RssiC
{
	uses
	{
		interface Boot;
		interface Timer<TMilli> as Timer;
		interface Packet;
		interface AMSend;
		interface Receive;
		interface SplitControl as RadioControl;
		interface CC2420Packet;
	}  
}

implementation
{ 
	message_t packet;
	bool busy = FALSE;
	/* every node records in each round        */
	/* if it has received signal from others   */
	/* set to 0 when new round starts          */
	/* map <received_from, rssi>               */
	uint16_t rssi[NODES][NODES];
	uint16_t link[NODES];

	void clear_record()
	{
		bzero(rssi, sizeof(uint16_t) * NODES * NODES);
		bzero(link, sizeof(uint16_t) * NODES);
	}

	void printf_to_serial()
	{
		int i;
		int j;
		uint32_t time;
		/* 1-2-rssi 1-3-rssi 2-1-rssi 2-3-rssi ... */
		for (i = 0; i < NODES; ++i)
		{
			for (j = 0; j < NODES; ++j)
			{
				if (i != j && rssi[j][i] != 0)
				{
					printf("%d ", rssi[j][i]);
				}
			}			
		}
		/* add timestamp */
		time = call Timer.getNow();
		printf("%lu\n", time);
		printfflush();
	}

	void send_msg()
	{
		link_msg payload;
		payload.id = TOS_NODE_ID;
		memcpy(payload.rssi, link, sizeof(uint16_t) * NODES);
		
		if (!busy) 
		{
			link_msg *msg =
				(link_msg*)call AMSend.getPayload(&packet, sizeof(link_msg));
			*msg = payload;			
			if (call AMSend.send(AM_BROADCAST_ADDR, &packet, sizeof(link_msg)) == SUCCESS) 
				busy = TRUE;
		}
	}

	event void Boot.booted()
	{
		call RadioControl.start();
		
		if (TOS_NODE_ID == 1)
		{
			/* base node run as master                     */
			/* it send sync signal to slaves (other nodes) */
			/* to start timer for sending message          */
			/* 10 ms interval between each round           */
			call Timer.startPeriodic(NODES * 10 + 200);
		}			
	}
	
	event void RadioControl.startDone(error_t err)
	{
		if (err != SUCCESS)
			call RadioControl.start();
	}

	event void RadioControl.stopDone(error_t err) {}

	event void Timer.fired()
	{
		/* only for master node */
		memcpy(rssi[0], link, sizeof(uint16_t) * NODES);
		printf_to_serial();
		send_msg();
	}

	event void AMSend.sendDone(message_t* m, error_t err)
	{
		if (err == SUCCESS) 
		{
			busy = FALSE;
			/* clear table after each round */
			clear_record();
		}
	}
	
	event message_t* 
	Receive.receive(message_t* msg, void* payload, uint8_t len)
	{
		if (len == sizeof(link_msg))
		{
			link_msg *data = (link_msg*)payload;
			/* retrieve rssi value from packet */
			link[data->id - 1] = call CC2420Packet.getRssi(msg) - 45;
			/* get the token */
			if (data->id == TOS_NODE_ID - 1)
			{
				/* broadcast rssi table */
				send_msg();	
			}

			if (TOS_NODE_ID == 1)
			{
				/* master node collect the rssi value */
				memcpy(rssi[data->id - 1], data->rssi, sizeof(uint16_t) * NODES);
			}
			
		}
		return msg;
	}
}
