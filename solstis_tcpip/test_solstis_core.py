import pytest
from box import BoxList

from solstis_tcpip.solstis_core import SolstisCore, SolstisError
from solstis_tcpip.solstis_constants import Commands
from solstis_tcpip.utils import response_keys


class MockSolstisCore(SolstisCore):
    def __init__(self, server_ip, server_port):
        # Use __init__ of SolstisCore to set up the connection
        super().__init__(server_ip, server_port)
        self.last_message_received = None

    def connect(self):
        self.connection = True
        pass

    def send_command(self, transmission_id=1, op="start_link", params=None):
        if self.connection is None:
            raise SolstisError("Not connected to the server.", severity=10)


        if params is not None:
            # convert number to [number] to match the solstis format for each value in the params
            for key, value in params.items():
                if isinstance(value, (int, float)):
                    params[key] = [value]
            message = {
                "transmission_id": [transmission_id],
                "op": op,
                "parameters": params,
            }
        else:
            message = {"transmission_id": [transmission_id], "op": op}
        command = {"message": message}
        self.last_message_received = command

    def create_dummy_response(self):
        transmission_id = self.last_message_received["message"]["transmission_id"][0]
        op = self.last_message_received["message"]["op"]
        if "parameters" in self.last_message_received["message"]:
            params = self.last_message_received["message"]["parameters"]
        else:
            params = None

        op_reply = op + "_reply"
        if op == "start_link":
            params_ret = {
                "status": "ok",
            }
        elif op == "ping":
            params_ret = {
                "text_out": params["text_in"].swapcase(),
            }
        elif op == "set_wave_m":
            params_ret = {
                "status": [0],
                "current_wavelength": [500],
                "extended_zone": 0,
            }
        elif op == "poll_wave_m":
            params_ret = {
                "status": [3],
                "current_wavelength": [500],
                "lock_status": 0,
                "extended_zone": 0,
            }
        elif op == "lock_wave_m":
            params_ret = {
                "status": [0],
            }
        elif op == "stop_wave_m":
            params_ret = {
                "status": [0],
                "current_wavelength": [500],
            }
        elif op == "move_wave_t":
            params_ret = {
                "status": [0],
            }
        elif op == "poll_move_wave_t":
            params_ret = {
                "status": [0],
                "current_wavelength": [500],
            }
        elif op == "stop_move_wave_t":
            params_ret = {
                "status": [0],
            }
        elif op == "tune_etalon":
            params_ret = {
                "status": [0],
            }
        elif op == "tune_cavity":
            params_ret = {
                "status": [0],
            }
        elif op == "fine_tune_cavity":
            params_ret = {
                "status": [0],
            }
        elif op == "tune_resonator":
            params_ret = {
                "status": [0],
            }
        elif op == "fine_tune_resonator":
            params_ret = {
                "status": [0],
            }
        else:
            raise ValueError("Unknown operation: " + op)

        message = {
            "transmission_id": [transmission_id],
            "op": op_reply,
            "parameters": params_ret,
        }

        response = {"message": message}
        print(response)
        return response

    def receive_response(self):
        response = self.create_dummy_response()
        self.response_buffer += BoxList([response])
        response_json = self.response_buffer.pop(0)
        return response_json

    def disconnect(self):
        self.connection = None


def test_mock_solstiscore1():
    # Test that the dummy connection reporesent the real connection of server (Default movement)
    solstis = MockSolstisCore(server_ip="192.000.0.000", server_port=12345)
    solstis.connect()
    solstis.start_link(ip_address="192.111.1.1111")
    solstis.disconnect()


def test_mock_solstiscore2():
    # Test that the dummy connection reporesent the real connection of server (If the server is not connected)
    solstis = MockSolstisCore(server_ip="192.000.0.000", server_port=12345)
    solstis.connect()
    solstis.disconnect()
    with pytest.raises(SolstisError):
        solstis.start_link(ip_address="192.111.1.1111")


def test_mock_solstiscore3():
    # Test that the dummy response has the correct keys
    solstis = MockSolstisCore(server_ip="192.000.0.000", server_port=12345)
    solstis.connect()
    solstis.start_link(ip_address="192.111.1.1111")

    response = solstis.ping(text_in="HelloWorld")
    for key in response["message"]["parameters"]:
        assert key in response_keys("ping")

    response = solstis.set_wave_m(wavelength=500)
    for key in response["message"]["parameters"]:
        assert key in response_keys("set_wave_m")

    response = solstis.poll_wave_m()
    for key in response["message"]["parameters"]:
        assert key in response_keys("poll_wave_m")

    response = solstis.lock_wave_m(True)
    for key in response["message"]["parameters"]:
        assert key in response_keys("lock_wave_m")

    response = solstis.stop_wave_m()
    for key in response["message"]["parameters"]:
        assert key in response_keys("stop_wave_m")

    response = solstis.move_wave_t(wavelength=500)
    for key in response["message"]["parameters"]:
        assert key in response_keys("move_wave_t")

    response = solstis.poll_move_wave_t()
    for key in response["message"]["parameters"]:
        assert key in response_keys("poll_move_wave_t")

    response = solstis.stop_move_wave_t()
    for key in response["message"]["parameters"]:
        assert key in response_keys("stop_move_wave_t")

    response = solstis.tune_etalon(setting=50)
    for key in response["message"]["parameters"]:
        assert key in response_keys("tune_etalon")

    response = solstis.tune_cavity(setting=50)
    for key in response["message"]["parameters"]:
        assert key in response_keys("tune_cavity")

    response = solstis.fine_tune_cavity(setting=50)
    for key in response["message"]["parameters"]:
        assert key in response_keys("fine_tune_cavity")

    response = solstis.tune_resonator(setting=50)
    for key in response["message"]["parameters"]:
        assert key in response_keys("tune_resonator")

    response = solstis.fine_tune_resonator(setting=50)
    for key in response["message"]["parameters"]:
        assert key in response_keys("fine_tune_resonator")

    solstis.disconnect()


# From now, assuming that the dummy response is working, we can test the SolstisCore class main functions
def test_solstiscore_without_comm1():
    # Default movement
    solstis = MockSolstisCore(server_ip="192.000.0.000", server_port=12345)
    solstis.connect()
    solstis.start_link(ip_address="192.111.1.1111")

    solstis.ping(text_in="HelloWorld")
    solstis.set_wave_m(wavelength=500)
    solstis.poll_wave_m()
    solstis.lock_wave_m(True)
    solstis.stop_wave_m()
    solstis.move_wave_t(wavelength=500)
    solstis.poll_move_wave_t()
    solstis.stop_move_wave_t()
    solstis.tune_etalon(setting=50)
    solstis.tune_cavity(setting=50)
    solstis.fine_tune_cavity(setting=50)
    solstis.tune_resonator(setting=50)
    solstis.fine_tune_resonator(setting=50)

    solstis.disconnect()


def test_solstiscore1():
    # Default movement
    solstis = SolstisCore(server_ip="192.000.0.000", server_port=12345)

    _command_keys = set(solstis._command.keys())
    enum_values = set(e.value for e in Commands)

    assert (
        _command_keys == enum_values
    ), "Keys in the dictionary do not match the values in the enum"
