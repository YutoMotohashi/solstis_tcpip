from solstis_constants import (
    Scan_Type,
    Scan_Type_Fast,
    Commands,
    status_messages_severity,
)


def test_status_messages_severity_keys():
    dict_keys = set(
        status_messages_severity.keys()
    )  # replace 'your_dict' with your actual dictionary
    enum_values = set(e.value for e in Commands)

    assert (
        dict_keys == enum_values
    ), "Keys in the dictionary do not match the values in the enum"


def test_status_messages_severity_severity_classify():
    for key, value in status_messages_severity.items():
        # assert that any of the (_, seveiry) of subvalues is equal to 0
        assert any(
            severity == 0 for _, severity in value.values()
        ), f"Severity 0 not found in subvalues, key: {key}, value: {value}"
