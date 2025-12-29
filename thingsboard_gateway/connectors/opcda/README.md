# OPC DA Connector for ThingsBoard IoT Gateway

## Overview

The OPC DA (OLE for Process Control Data Access) Connector allows ThingsBoard IoT Gateway to connect to OPC DA servers and collect data from industrial devices and systems.

## Features

- Connect to OPC DA servers (local or remote via DCOM)
- Read multiple tags/items from OPC DA server
- Support for attributes and timeseries data
- Configurable polling intervals
- Support for RPC (Remote Procedure Calls) from ThingsBoard
- Support for attribute updates from ThingsBoard
- Automatic data type conversion
- Quality and timestamp handling

## Requirements

### Python Libraries

```bash
pip install OpenOPC-Python3x
pip install pywin32  # For Windows systems
```

### System Requirements

- **Windows**: OPC DA is primarily a Windows technology using COM/DCOM
- **Linux/Mac**: Use OpenOPC Gateway Server running on Windows as a bridge

### OPC DA Server

You need an OPC DA server running. For testing, you can use:
- Matrikon OPC Simulation Server (free)
- Kepware OPC Server
- Any industrial OPC DA server

## Configuration

### Basic Configuration Structure

```json
{
  "server": {
    "name": "Your.OPC.Server.Name",
    "host": "localhost",
    "pollPeriodInMillis": 5000,
    "disableSubscriptions": true,
    "mapping": [...]
  }
}
```

### Configuration Parameters

#### Server Level

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| name | string | required | OPC DA Server ProgID (e.g., "Matrikon.OPC.Simulation.1") |
| host | string | "localhost" | Hostname or IP address of OPC DA server |
| pollPeriodInMillis | integer | 5000 | Polling interval in milliseconds |
| disableSubscriptions | boolean | true | OPC DA typically uses polling, not subscriptions |
| showMap | boolean | false | Enable detailed logging for debugging |
| mapping | array | required | Device and tag mappings |

#### Device Mapping

Each mapping entry defines a device and its tags:

```json
{
  "deviceNodePattern": "Device1",
  "deviceNamePattern": "My Device Name",
  "deviceTypePattern": "Sensor",
  "attributes": [...],
  "timeseries": [...],
  "attributes_updates": [...],
  "rpc_methods": [...]
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| deviceNodePattern | string | Unique identifier for the device configuration |
| deviceNamePattern | string | Device name in ThingsBoard |
| deviceTypePattern | string | Device type in ThingsBoard |
| attributes | array | Static attributes to read |
| timeseries | array | Time-series data to read |
| attributes_updates | array | Attributes that can be written from ThingsBoard |
| rpc_methods | array | RPC methods configuration |

#### Tag Configuration

For attributes and timeseries:

```json
{
  "key": "temperature",
  "tag": "Channel1.Device1.Temperature",
  "type": "double"
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| key | string | Key name in ThingsBoard |
| tag | string | OPC DA tag/item ID |
| type | string | Data type: int, double, float, string, bool |

#### Attribute Updates Configuration

```json
{
  "attributeOnThingsBoard": "setpoint",
  "attributeOnDevice": "Channel1.Device1.Setpoint"
}
```

#### RPC Methods Configuration

```json
{
  "method": "setValue",
  "tag": "Channel1.Device1.Control"
}
```

## Example Configuration

See `opcda_config_example.json` for a complete example.

## Usage in Gateway Configuration

Add the OPC DA connector to your gateway configuration file (tb_gateway.yaml):

```yaml
connectors:
  -
    name: OPC-DA Connector
    type: opcda
    configuration: opcda.json
```

## RPC Commands

The connector supports the following RPC commands from ThingsBoard:

### Get Tag Value

```json
{
  "method": "get",
  "params": "Channel1.Device1.Temperature"
}
```

Or:

```json
{
  "method": "opcda_get",
  "params": "tag=Channel1.Device1.Temperature"
}
```

### Set Tag Value

```json
{
  "method": "set",
  "params": {
    "tag": "Channel1.Device1.Setpoint",
    "value": 25.5
  }
}
```

Or string format:

```json
{
  "method": "opcda_set",
  "params": "tag=Channel1.Device1.Setpoint;value=25.5"
}
```

### Custom RPC Methods

Configure custom methods in the configuration file and call them:

```json
{
  "method": "setValue",
  "params": 100
}
```

## Troubleshooting

### Connection Issues

1. **Cannot connect to OPC server**
   - Verify OPC server name (ProgID) is correct
   - Check if OPC server is running
   - Verify DCOM permissions (for remote connections)

2. **OpenOPC not found**
   ```bash
   pip install OpenOPC-Python3x
   ```

3. **pywin32 errors on Windows**
   ```bash
   pip install --upgrade pywin32
   python Scripts/pywin32_postinstall.py -install
   ```

### Remote OPC Server Connection

For remote OPC servers (DCOM):
1. Configure DCOM permissions on Windows
2. Use correct hostname/IP in configuration
3. Ensure network connectivity and firewall rules

### Linux/Mac Support

On non-Windows systems:
1. Install OpenOPC Gateway Server on a Windows machine
2. Configure gateway server to bridge OPC DA access
3. Connect to gateway server from Linux/Mac

## Data Quality

OPC DA provides quality indicators for each tag:
- **Good**: Value is reliable
- **Bad**: Value is unreliable
- **Uncertain**: Value quality is questionable

The connector logs quality information but currently sends all values to ThingsBoard.

## Performance Considerations

- Adjust `pollPeriodInMillis` based on your needs (1000-60000 ms typical)
- Too frequent polling may impact OPC server performance
- Group related tags in same device for efficient reading
- Use OPC DA groups if server supports it (future enhancement)

## Limitations

- Windows-specific protocol (requires Windows or Gateway Server)
- Polling-based (no real-time subscriptions like OPC UA)
- COM/DCOM complexity for remote access
- No built-in security compared to OPC UA

## Migration to OPC UA

Consider migrating to OPC UA for:
- Cross-platform support
- Better security
- Real-time subscriptions
- Modern architecture

## License

Apache License 2.0

## Support

For issues and questions:
- ThingsBoard Community: https://groups.google.com/forum/#!forum/thingsboard
- GitHub Issues: https://github.com/thingsboard/thingsboard-gateway/issues
