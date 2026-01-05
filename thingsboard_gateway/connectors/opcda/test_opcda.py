import OpenOPC
import time
import pythoncom


def main():
    pythoncom.CoInitialize()

    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')

    item_ids = [
        "test.tag1",
        "test.tag2"
    ]

    while True:
        for item in item_ids:
            value, quality, timestamp = opc.read(item,sync=True)
            print(f"{item} = {value}, {quality}, {timestamp}")
        time.sleep(0.4)


if __name__ == "__main__":
    main()