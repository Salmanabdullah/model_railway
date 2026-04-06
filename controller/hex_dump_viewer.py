def format_hex_dump(data: bytes, width: int = 16) -> str:
    """
    Return a classic multi-line hex dump.

    Example line:
    0000  20 00 07 54 56 50 53 5F 42 35 5F 44 4F 57 4E 20  | ..TVPS_B5_DOWN |
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("format_hex_dump expects bytes or bytearray")

    lines = []

    for offset in range(0, len(data), width):
        chunk = data[offset:offset + width]

        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)

        # pad hex part so ASCII column aligns
        padded_hex = hex_part.ljust(width * 3 - 1)

        lines.append(f"{offset:04X}  {padded_hex}  |{ascii_part}|")

    return "\n".join(lines)


def print_hex_dump(title: str, data: bytes, width: int = 16):
    print(title)
    print(format_hex_dump(data, width=width))