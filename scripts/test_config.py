import argparse

from src.utils.config_loader import load_config


def main():
    parser = argparse.ArgumentParser(description="Test laptop config loading.")
    parser.add_argument("--config", required=True, help="Path to laptop config JSON.")
    args = parser.parse_args()

    config = load_config(args.config)

    print("Config loaded successfully")
    print(f"Laptop ID: {config['laptop_id']}")
    print(f"Number of bands: {len(config['bands'])}")

    for band in config["bands"]:
        print(
            f"- participant_id={band['participant_id']} | "
            f"device_identifier={band['device_identifier']} | "
            f"stream_name={band['stream_name']}"
        )


if __name__ == "__main__":
    main()
