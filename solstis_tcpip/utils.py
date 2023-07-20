def response_keys(op):
    """Returns the keys of the response dictionary for the given operation"""
    if op == "start_link":
        return ["status"]
    elif op == "ping":
        return ["text_out"]
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
