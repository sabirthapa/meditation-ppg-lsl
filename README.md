# Meditation PPG LSL Recorder

This repository is for connecting to multiple MAXREFDES280 / OS61 wristbands and collecting raw PPG data during group meditation sessions.

The goal is to collect PPG from 30-40 wristbands, split across 4-5 laptops, and stream the data through Lab Streaming Layer (LSL) so all streams can be time-aligned and saved.

This repo is focused only on data collection, connection, streaming, and recording. Analysis will be handled separately after the PPG data is collected.

## Main Goal

- Connect multiple wristbands over BLE
- Collect raw PPG data from each band
- Stream each band as a separate LSL stream
- Record all streams using LabRecorder
- Send session markers through LSL
- Save clean logs for debugging connection and packet issues

## Planned System

Each laptop will handle a subset of wristbands.


