class BleAddress:
    def __init__(self, address, address_type=None):
        self.address = str(address)
        self.address_type = address_type

    def __str__(self):
        return self.address

    def __repr__(self):
        return f"BleAddress({self.address!r})"
