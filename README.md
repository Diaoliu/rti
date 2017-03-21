## Usage

#### Dependencies

1. **nesc** complier
2. **tinyos** library
3. python
  * matplotlib
  * tinker (GUI backend for matplotlib)
  * scipy, numpy

#### Backend

1. configure `TINYOS_ROOT_DIR` according to your tinyos-main path
2. make ROM image `make telosb`
3. `sudo make telosb reinstall.XXX bsl, /dev/ttyUSB0` where XXX is the node id and /dev/ttyUSB0 from `motelist`

#### Frontend

1. listening the serial port using 
  `cd frontend && sudo python rssi_listener.py /dev/ttyUSB0`
2. edit node coordinates in file 
   `frontend/log/coords.txt`
3. redirect output into txt file
   `sudo python rssi_listener.py /dev/ttyUSB0 > log/listen_out.txt`
4. for static analysis
   `log/listen_out.txt | python rti_generator.py`
4. for dynamic analysis
   `sudo python rssi_listener.py /dev/ttyUSB0 | python rti_generator.py`
