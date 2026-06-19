# NAD AVR

[![HACS](https://img.shields.io/badge/HACS-Custom%20Integration-orange?style=for-the-badge)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/badge/Version-v0.1.3-0EA5E9?style=for-the-badge)](https://github.com/Micpi/nad-avr/releases/latest)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/mickaelpila)

Home Assistant custom integration for NAD T187, T777 and T787 home cinema amplifiers using the official NAD RS-232 / Ethernet ASCII protocol.

## Installation Via HACS

1. Open HACS in Home Assistant.
2. Go to Integrations, open the menu, then Custom repositories.
3. Add `https://github.com/Micpi/nad-avr`.
4. Select category `Integration`.
5. Install `NAD AVR`.
6. Restart Home Assistant.
7. Go to Settings, Devices & services, Add integration, then search `NAD AVR`.

## Features

- UI configuration flow with Telnet or RS-232 transport.
- Main `media_player` entity for power, mute, volume and source.
- Complete generic command surface from the NAD API documents:
  - 276 protocol variables
  - queryable variables as sensors
  - ranged variables as numbers
  - enumerated variables as selects
  - On/Off and Yes/No variables as switches
  - raw services for every command/operator
- Compatible with Ethernet port 23 and RS-232 115200 8N1.

Most advanced entities are disabled by default to keep the device page readable. Enable the variables you need from Home Assistant's entity registry.

## Configuration

Choose one transport in the config flow:

| Transport | Parameters |
| --- | --- |
| Telnet | Host, port, name, model |
| RS-232 | Serial port, baudrate, name, model |

The NAD protocol uses TCP port `23` for Ethernet/Telnet and `115200 8N1` for RS-232.

## Services

- `nad_avr.send_command`
- `nad_avr.set_variable`
- `nad_avr.query_variable`
- `nad_avr.increment_variable`
- `nad_avr.decrement_variable`
- `nad_avr.send_ir`

Examples:

```yaml
service: nad_avr.set_variable
data:
  variable: Main.ListeningMode
  value: Stereo
```

```yaml
service: nad_avr.increment_variable
data:
  variable: Main.Volume
```

## Notes

The NAD protocol sends and receives ASCII commands in the form `Prefix.Variable?`, `Prefix.Variable=value`, `Prefix.Variable+` and `Prefix.Variable-`, wrapped with carriage returns. Ethernet and RS-232 use the same command set.

