import pytest

from scpilib.tcpListener import splitter


def test_command_split():
    scpi_commands = [
        (b'', ([], b'')),
        (b'\n \r ', ([], b'')),
        (b'*IDN?\n', ([b'*IDN?'], b'')),
        (b'*IDN?;C1\n', ([b'*IDN?;C1'], b'')),
        (b'*IDN?\nC2 123\rC3\n', ([b'*IDN?', b'C2 123', 'C3'], b'')),
        (b'*IDN?\nC2 123\rC3\nrest...', ([b'*IDN?', b'C2 123', 'C3'], b'rest...')),
        (b'   *IDN?\n \n \r', ([b'*IDN?'], b'')),
        (b'  \n \r  *IDN?\n \r \n  ', ([b'*IDN?'], b'')),
        (b'*IDN?\nC2 123\n', ([b'*IDN?', b'C2 123'], b'')),
        (b' *IDN?\n  C2 123\rC3\n\rrest...', ([b'*IDN?', b'C2 123', b'C3'], b'rest...')),
        (b' *IDN?\n  C2 123;C3\rC4\n\rrest...', ([b'*IDN?', b'C2 123;C3', b'C4'], b'rest...')),
        (1000*b'*idn?\n'+' bla ', (1000*[b'*idn?'], b'bla')),
    ]
    for inp, expected in scpi_commands:
        assert splitter(inp) == expected
