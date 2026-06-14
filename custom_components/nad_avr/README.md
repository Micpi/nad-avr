# NAD AVR

Home Assistant custom integration for NAD T187, T777 and T787 home cinema amplifiers using the official NAD RS-232 / Ethernet ASCII protocol.

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

