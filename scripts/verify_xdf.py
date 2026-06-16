import argparse
import pyxdf


def get_info_value(info: dict, key: str, default: str = "") -> str:
    value = info.get(key, [default])
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    return default


def main():
    parser = argparse.ArgumentParser(description="Verify streams inside an XDF file.")
    parser.add_argument("xdf_path", help="Path to the .xdf file")
    args = parser.parse_args()

    print(f"Loading XDF file: {args.xdf_path}")
    streams, header = pyxdf.load_xdf(args.xdf_path)

    print()
    print(f"Number of streams found: {len(streams)}")

    for i, stream in enumerate(streams, start=1):
        info = stream["info"]

        name = get_info_value(info, "name")
        stream_type = get_info_value(info, "type")
        channel_count = int(get_info_value(info, "channel_count", "0"))

        sample_count = len(stream["time_series"])
        timestamp_count = len(stream["time_stamps"])

        print()
        print(f"Stream {i}")
        print("--------")
        print(f"Name: {name}")
        print(f"Type: {stream_type}")
        print(f"Channels: {channel_count}")
        print(f"Samples: {sample_count}")
        print(f"Timestamps: {timestamp_count}")

        if sample_count > 0:
            print(f"First timestamp: {stream['time_stamps'][0]}")
            print(f"Last timestamp:  {stream['time_stamps'][-1]}")
            print(f"First sample:    {stream['time_series'][0]}")

        if stream_type == "Markers" and sample_count > 0:
            print()
            print("Markers:")
            for marker, timestamp in zip(stream["time_series"], stream["time_stamps"]):
                marker_value = marker[0] if isinstance(marker, (list, tuple)) else marker
                print(f"  {timestamp}: {marker_value}")

    print()
    print("XDF verification complete.")


if __name__ == "__main__":
    main()
