import json
import socket
from box import BoxList


# Exception class for Solstis specific errors
class SolstisError(Exception):
    """Exception raised when the Solstis response indicates an error

    Attributes:
        message ~ explanation of the error
        severity ~ severity of the error (0 = warning, 1 = error, 2 = critical, 10 = communication error)
    """

    def __init__(self, message, severity=0):
        self.message = message
        self.severity = 0


class SolstisCore:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.connection = None  # Placeholder for the actual connection object.
        self.response_buffer = BoxList([])
        self._transmission_id_counter = 0

    def connect(self, timeout=5.0):
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(timeout)  # Set a timeout of 5 seconds
            self.connection.connect((self.server_ip, self.server_port))
        except socket.timeout:
            self.connection = None
            raise TimeoutError("Connection timed out")
        except Exception as e:
            print(f"Failed to connect to the server: {e}")
            self.connection = None

    def send_command(self, transmission_id=1, op="start_link", params=None):
        if self.connection is None:
            raise SolstisError("Not connected to the server.", severity=10)

        if params is not None:
            message = {
                "transmission_id": [transmission_id],
                "op": op,
                "parameters": params,
            }
        else:
            message = {"transmission_id": [transmission_id], "op": op}
        command = {"message": message}
        message_json = json.dumps(command)
        self.connection.sendall(message_json.encode())

    def receive_response(self):
        response = self.connection.recv(1024)  # Adjust the buffer size as needed.
        self.response_buffer += BoxList([json.loads(response.decode())])
        response_json = self.response_buffer.pop(0)
        return response_json

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def _verify_messsage(self, message, op=None, transmission_id=None):
        msgID = message["message"]["transmission_id"][0]
        msgOP = message["message"]["op"]
        if msgOP == "parse_fail":
            err_msg = "Mesage with ID " + str(msgID) + " failed to parse."
            err_msg += "\n\n" + str(message)
            raise SolstisError(err_msg, 10)
        if transmission_id is not None:
            if msgID != transmission_id:
                err_msg = (
                    "Message with ID"
                    + str(msgID)
                    + " did not match expected ID of: "
                    + str(transmission_id)
                )
                raise SolstisError(err_msg, 10)
        if op is not None:
            if msgOP != op:
                message = (
                    "Message with ID"
                    + str(msgID)
                    + "with operation command of '"
                    + msgOP
                    + "' did not match expected operation command of: "
                    + op
                )
                raise SolstisError(message)

    def _start_link(self, transmission_id, ip_address):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        ip_address: The IP address of the client.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        'ok' - The link has been successfully established.
        'failed' - The link could not be formed.
        """
        self.send_command(transmission_id, "start_link", {"ip_address": ip_address})
        response = self.receive_response()
        self._verify_messsage(
            response, op="start_link_reply", transmission_id=transmission_id
        )

        return response

    def _set_wave_m(self, transmission_id, wavelength):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        wavelength: The target wavelength value in nm within the tuning range of the SolsTiS.

        Returns:
        The response from the Solstis device as a dictionary. The response includes the following fields:
        'status' - The status of the operation:
            0 - operation successful.
            1 - no link to wavelength meter or no meter configured.
            2 - wavelength out of range.
        'current_wavelength' - The most recently obtained wavelength reading from the wavelength meter.
        'extended_zone' - Indicates if the current wavelength is in an extended zone:
            0 - current wavelength is not in an extended zone.
            1 - current wavelength is in an extended zone.
        'duration' - Time taken in seconds from receiving the task to transmitting the final report.
        """
        self.send_command(transmission_id, "set_wave_m", {"wavelength": wavelength})
        response = self.receive_response()
        self._verify_messsage(
            response, op="set_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _poll_wave_m(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The response includes the following fields:
        'status' - The status of the tuning software:
            0 - tuning software not active.
            1 - no link to wavelength meter or no meter configured.
            2 - tuning in progress.
            3 - wavelength is being maintained.
        'current_wavelength' - The most recently obtained wavelength reading from the wavelength meter.
        'lock_status' - The status of the wavelength lock:
            0 - wavelength is not being maintained.
            1 - wavelength is being maintained.
        'extended_zone' - Indicates if the current wavelength is in an extended zone:
            0 - current wavelength is not in an extended zone.
            1 - current wavelength is in an extended zone.
        """
        self.send_command(transmission_id, "poll_wave_m")
        response = self.receive_response()
        self._verify_messsage(
            response, op="poll_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _lock_wave_m(self, transmission_id, operation):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        operation: The operation to perform. Can be "on" to maintain the current wavelength or "off" to stop maintaining it.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - no link to wavelength meter.
        """
        self.send_command(transmission_id, "lock_wave_m", {"operation": operation})
        response = self.receive_response()
        self._verify_messsage(
            response, op="lock_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _stop_wave_m(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - no link to wavelength meter.
        The 'current_wavelength' field in the response is the most recently obtained wavelength reading from the wavelength meter.
        """
        self.send_command(transmission_id, "stop_wave_m")
        response = self.receive_response()
        self._verify_messsage(
            response, op="stop_wave_m_reply", transmission_id=transmission_id
        )

        return response

    def _move_wave_t(self, transmission_id, wavelength):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        wavelength: The target wavelength in nm within the tuning range of the SolsTiS.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation successful.
        1 - command failed.
        2 - wavelength out of range.
        """
        self.send_command(transmission_id, "move_wave_t", {"wavelength": wavelength})
        response = self.receive_response()
        self._verify_messsage(
            response, op="move_wave_t_reply", transmission_id=transmission_id
        )

        status = response["message"]["parameters"]["status"]
        if status != 0:
            error_messages = {1: "Command failed.", 2: "Wavelength out of range."}
            raise SolstisError(
                "Failed to move wavelength: "
                + error_messages.get(status, "Unknown error")
            )

        return response

    def _poll_move_wave_t(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - Tuning completed.
        1 - Tuning in progress.
        2 - Tuning operation failed.
        """
        self.send_command(transmission_id, "poll_move_wave_t")
        response = self.receive_response()
        self._verify_messsage(
            response, op="poll_move_wave_t_reply", transmission_id=transmission_id
        )

        return response

    def _stop_move_wave_t(self, transmission_id):
        """
        Parameters:
        transmission_id: The ID for this transmission.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following value:
        0 - operation completed.
        """
        self.send_command(transmission_id, "stop_move_wave_t")
        response = self.receive_response()
        self._verify_messsage(
            response, op="stop_move_wave_t_reply", transmission_id=transmission_id
        )

        return response

    def _tune_etalon(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The etalon tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_etalon", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_etalon_reply", transmission_id=transmission_id
        )

        return response

    def _tune_cavity(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The reference cavity tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_cavity", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_cavity_reply", transmission_id=transmission_id
        )

        return response

    def _fine_tune_cavity(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The fine reference cavity tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "fine_tune_cavity", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="fine_tune_cavity_reply", transmission_id=transmission_id
        )

        return response

    def _tune_resonator(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The resonator tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "tune_resonator", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="tune_resonator_reply", transmission_id=transmission_id
        )

        return response

    def _fine_tune_resonator(self, transmission_id, setting):
        """
        Parameters:
        transmission_id: The ID for this transmission.
        setting: The fine resonator tuning setting, expressed as a percentage where 100 is full scale.

        Returns:
        The response from the Solstis device as a dictionary. The 'status' field in the response can have the following values:
        0 - operation completed.
        1 - setting out of range.
        2 - command failed.
        """
        self.send_command(transmission_id, "fine_tune_resonator", {"setting": setting})
        response = self.receive_response()
        self._verify_messsage(
            response, op="fine_tune_resonator_reply", transmission_id=transmission_id
        )

        return response

    def _allocate_transmission_id(self):
        self._transmission_id_counter += 1
        max_transmission_id = 2**30 - 1
        if self._transmission_id_counter > max_transmission_id:
            self._transmission_id_counter = 0
        return self._transmission_id_counter

    def _check_response(self, response):
        # switch depending on the operation
        operation = response["message"]["op"]
        status = response["message"]["parameters"]["status"]
        if operation == "start_link_reply":
            if status == "ok":
                pass
            elif status == "failed":
                raise SolstisError("Failed to start link.", severity=2)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "set_wave_m_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError(
                    "No link to wavelength meter or no meter configured.", severity=1
                )
            elif status == 2:
                raise SolstisError("Wavelength out of range.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "poll_wave_m_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError(
                    "No link to wavelength meter or no meter configured.", severity=1
                )
            elif status == 2:
                raise SolstisError("Tuning in progress.", severity=1)
            elif status == 3:
                raise SolstisError("Wavelength is being maintained.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "lock_wave_m_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("No link to wavelength meter.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "stop_wave_m_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("No link to wavelength meter.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "move_wave_t_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Command failed.", severity=1)
            elif status == 2:
                raise SolstisError("Wavelength out of range.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "poll_move_wave_t_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Tuning in progress.", severity=1)
            elif status == 2:
                raise SolstisError("Tuning operation failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "stop_move_wave_t_reply":
            if status == 0:
                pass
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "tune_etalon_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Setting out of range.", severity=1)
            elif status == 2:
                raise SolstisError("Command failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "tune_cavity_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Setting out of range.", severity=1)
            elif status == 2:
                raise SolstisError("Command failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "fine_tune_cavity_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Setting out of range.", severity=1)
            elif status == 2:
                raise SolstisError("Command failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "tune_resonator_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Setting out of range.", severity=1)
            elif status == 2:
                raise SolstisError("Command failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)
        elif operation == "fine_tune_resonator_reply":
            if status == 0:
                pass
            elif status == 1:
                raise SolstisError("Setting out of range.", severity=1)
            elif status == 2:
                raise SolstisError("Command failed.", severity=1)
            else:
                raise SolstisError("Unknown error.", severity=2)

    ### Public methods ###
    def start_link(self, ip_address: str = "192.168.1.107"):
        """
        Parameters:
        ip_address: The IP address of the client.
        """
        transmission_id = self._allocate_transmission_id()
        response = self._start_link(transmission_id, ip_address)
        self._check_response(response)

        return response

    def set_wave_m(self, wavelength: float):
        """
        Parameters:
        wavelength: The target wavelength value in nm within the tuning range of the SolsTiS.
        """
        transmission_id = self._allocate_transmission_id()
        response = self._set_wave_m(transmission_id, wavelength)
        self._check_response(response)

        # the parameter of extended_zone is not used in the current version

        return response

    def poll_wave_m(self):
        """
        Parameters: None
        """
        transmission_id = self._allocate_transmission_id()
        response = self._poll_wave_m(transmission_id)
        self._check_response(response)

        return response

    def lock_wave_m(self, operation: bool):
        """
        Parameters:
        operation: The operation to perform. Can be True to maintain the current wavelength or False to stop maintaining it.
        """
        transmission_id = self._allocate_transmission_id()
        response = self._lock_wave_m(transmission_id, "on" if operation else "off")
        self._check_response(response)

        return response

    def stop_wave_m(self):
        """
        Parameters: None
        """
        transmission_id = self._allocate_transmission_id()
        response = self._stop_wave_m(transmission_id)
        self._check_response(response)

        return response

    def move_wave_t(self, wavelength: float):
        """
        Parameters:
        wavelength: The target wavelength in nm within the tuning range of the SolsTiS.
        """
        transmission_id = self._allocate_transmission_id()
        response = self._move_wave_t(transmission_id, wavelength)
        self._check_response(response)

        return response

    def poll_move_wave_t(self):
        """
        Parameters: None
        """
        transmission_id = self._allocate_transmission_id()
        response = self._poll_move_wave_t(transmission_id)
        self._check_response(response)

        return response

    def stop_move_wave_t(self):
        """
        Parameters: None
        """
        transmission_id = self._allocate_transmission_id()
        response = self._stop_move_wave_t(transmission_id)
        self._check_response(response)

        return response

    def tune_etalon(self, setting: float):
        """
        Parameters:
        setting: The etalon tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."

        transmission_id = self._allocate_transmission_id()
        response = self._tune_etalon(transmission_id, setting)
        self._check_response(response)

        return response

    def tune_cavity(self, setting: float):
        """
        Parameters:
        setting: The reference cavity tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."

        transmission_id = self._allocate_transmission_id()
        response = self._tune_cavity(transmission_id, setting)
        self._check_response(response)

        return response

    def fine_tune_cavity(self, setting: float):
        """
        Parameters:
        setting: The fine reference cavity tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."

        transmission_id = self._allocate_transmission_id()
        response = self._fine_tune_cavity(transmission_id, setting)
        self._check_response(response)

        return response

    def tune_resonator(self, setting: float):
        """
        Parameters:
        setting: The resonator tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."

        transmission_id = self._allocate_transmission_id()
        response = self._tune_resonator(transmission_id, setting)
        self._check_response(response)

        return response

    def fine_tune_resonator(self, setting: float):
        """
        Parameters:
        setting: The fine resonator tuning setting, expressed as a percentage where 100 is full scale.
        """
        assert 0 <= setting <= 100, "Setting out of range."

        transmission_id = self._allocate_transmission_id()
        response = self._fine_tune_resonator(transmission_id, setting)
        self._check_response(response)

        return response


def response_keys(op):
    """Returns the keys of the response dictionary for the given operation"""
    if op == "start_link":
        return ["status"]
    elif op == "set_wave_m":
        return ["status", "current_wavelength", "extended_zone"]
    elif op == "poll_wave_m":
        return ["status", "current_wavelength", "lock_status", "extended_zone"]
    elif op == "lock_wave_m":
        return ["status"]
    elif op == "stop_wave_m":
        return ["status", "current_wavelength"]
    elif op == "move_wave_t":
        return ["status"]
    elif op == "poll_move_wave_t":
        return ["status", "current_wavelength"]
    elif op == "stop_move_wave_t":
        return ["status"]
    elif op == "tune_etalon":
        return ["status"]
    elif op == "tune_cavity":
        return ["status"]
    elif op == "fine_tune_cavity":
        return ["status"]
    elif op == "tune_resonator":
        return ["status"]
    elif op == "fine_tune_resonator":
        return ["status"]
    else:
        raise ValueError("Unknown operation: " + op)


### for testing ###


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
        print(self.last_message_received)
        print(type(self.last_message_received))
        print(self.last_message_received["message"])
        print(self.last_message_received["message"]["transmission_id"])

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
        elif op == "set_wave_m":
            params_ret = {
                "status": 0,
                "current_wavelength": 500,
                "extended_zone": 0,
            }
        elif op == "poll_wave_m":
            params_ret = {
                "status": 0,
                "current_wavelength": 500,
                "lock_status": 0,
                "extended_zone": 0,
            }
        elif op == "lock_wave_m":
            params_ret = {
                "status": 0,
            }
        elif op == "stop_wave_m":
            params_ret = {
                "status": 0,
                "current_wavelength": 500,
            }
        elif op == "move_wave_t":
            params_ret = {
                "status": 0,
            }
        elif op == "poll_move_wave_t":
            params_ret = {
                "status": 0,
                "current_wavelength": 500,
            }
        elif op == "stop_move_wave_t":
            params_ret = {
                "status": 0,
            }
        elif op == "tune_etalon":
            params_ret = {
                "status": 0,
            }
        elif op == "tune_cavity":
            params_ret = {
                "status": 0,
            }
        elif op == "fine_tune_cavity":
            params_ret = {
                "status": 0,
            }
        elif op == "tune_resonator":
            params_ret = {
                "status": 0,
            }
        elif op == "fine_tune_resonator":
            params_ret = {
                "status": 0,
            }
        else:
            raise ValueError("Unknown operation: " + op)

        message = {
            "transmission_id": [transmission_id],
            "op": op_reply,
            "parameters": params_ret,
        }

        response = {"message": message}
        return response

    def receive_response(self):
        response = self.create_dummy_response()
        self.response_buffer += BoxList([response])
        response_json = self.response_buffer.pop(0)
        return response_json

    def disconnect(self):
        self.connection = None
