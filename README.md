# solstis_tcpip

## Author

written by Yuto Motohashi, 2023/08/31

## Description

For controlling a Solstis Laser using TCP/IP using Python

## Installation

### Clone

```bash
git clone https://github.com/YutoMotohashi/solstis_tcpip
cd ./solstis_tcpip
poetry install
```

### Environmental Variables

To establish the communication, you need to set the environmental variables of following. For the setting of solstis side, please refer to the manual of Solstis.

- Solstis IP address

- the port through which you want to communicate with Solstis

- your IP address

### Usage

basic usage is shown in `/solstis_tcpip/solstis_tcpip/init_test/test_communication_hard.ipynb`

### Exceptions

- `SolstisError`: raised when Solstis returns error. All the results except for the best result result in this error. The way to handle this error is up to the user. The communication with Solstis is already finished when this error is raised.

### test

```bash
poetry run python pytest
```

### Limitation

- This library covers only the command without a report. 
