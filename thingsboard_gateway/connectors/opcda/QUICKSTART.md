# OPC DA Connector Quick Start Guide

## Installation

### Step 1: Install Required Dependencies

#### For Windows:

```bash
pip install OpenOPC-Python3x
pip install pywin32
```

After installing pywin32, run the post-install script:

```bash
python Scripts/pywin32_postinstall.py -install
```

#### For Linux/Mac:

You'll need to use OpenOPC Gateway Server running on a Windows machine as a bridge:

1. Install OpenOPC Gateway Server on a Windows machine
2. On Linux/Mac, install OpenOPC client:

```bash
pip install OpenOPC-Python3x
```

## Step 2: Install and Start an OPC DA Server

For testing purposes, you can use Matrikon OPC Simulation Server:

1. Download from: https://www.matrikonopc.com/downloads/178/productsoftware/index.aspx
2. Install the simulation server
3. Start the OPC server (default name: "Matrikon.OPC.Simulation.1")

## Step 3: Test OPC Connection

Before configuring the gateway, test your OPC connection using OpenOPC:

```python
import OpenOPC

# Create client
opc = OpenOPC.client()

# List available OPC servers
servers = opc.servers()
print("Available OPC Servers:", servers)

# Connect to your server
opc.connect('Matrikon.OPC.Simulation.1')

# List available tags
tags = opc.list('*', recursive=True, flat=True)
print("Available tags:", tags[:10])  # Print first 10 tags

# Read a tag
value = opc.read('Random.Int1')
print("Tag value:", value)

# Close connection
opc.close()
```

## Step 4: Configure the Gateway

### Create OPC DA Connector Configuration

Create a file `opcda.json` in your gateway configuration directory:

```json
{
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "localhost",
    "pollPeriodInMillis": 5000,
    "disableSubscriptions": true,
    "mapping": [
      {
        "deviceNodePattern": "SimulationDevice",
        "deviceNamePattern": "OPC DA Simulation Device",
        "deviceTypePattern": "Simulation",
        "attributes": [
          {
            "key": "deviceModel",
            "tag": "Random.String",
            "type": "string"
          }
        ],
        "timeseries": [
          {
            "key": "randomInt",
            "tag": "Random.Int1",
            "type": "int"
          },
          {
            "key": "randomReal",
            "tag": "Random.Real4",
            "type": "double"
          }
        ]
      }
    ]
  }
}
```

### Update Gateway Configuration

Edit your `tb_gateway.yaml` file to include the OPC DA connector:

```yaml
thingsboard:
  host: YOUR_THINGSBOARD_HOST
  port: 1883
  security:
    accessToken: YOUR_ACCESS_TOKEN

storage:
  type: memory
  read_records_count: 100
  max_records_count: 100000

connectors:
  - name: OPC-DA Connector
    type: opcda
    configuration: opcda.json
```

## Step 5: Start the Gateway

```bash
python -m thingsboard_gateway
```

## Step 6: Verify Data in ThingsBoard

1. Log in to your ThingsBoard instance
2. Navigate to Devices
3. You should see "OPC DA Simulation Device"
4. Check Latest Telemetry to see data coming in

## Common Configuration Patterns

### Multiple Devices

```json
{
  "server": {
    "name": "Your.OPC.Server",
    "host": "localhost",
    "pollPeriodInMillis": 5000,
    "mapping": [
      {
        "deviceNodePattern": "Device1",
        "deviceNamePattern": "Pump 1",
        "deviceTypePattern": "Pump",
        "timeseries": [
          {
            "key": "speed",
            "tag": "Plant.Pumps.Pump1.Speed",
            "type": "int"
          },
          {
            "key": "flowRate",
            "tag": "Plant.Pumps.Pump1.FlowRate",
            "type": "double"
          }
        ]
      },
      {
        "deviceNodePattern": "Device2",
        "deviceNamePattern": "Tank 1",
        "deviceTypePattern": "Tank",
        "timeseries": [
          {
            "key": "level",
            "tag": "Plant.Tanks.Tank1.Level",
            "type": "double"
          },
          {
            "key": "temperature",
            "tag": "Plant.Tanks.Tank1.Temperature",
            "type": "double"
          }
        ]
      }
    ]
  }
}
```

### With Attributes Updates (Write Support)

```json
{
  "server": {
    "name": "Your.OPC.Server",
    "host": "localhost",
    "pollPeriodInMillis": 5000,
    "mapping": [
      {
        "deviceNodePattern": "Controller",
        "deviceNamePattern": "PLC Controller",
        "deviceTypePattern": "PLC",
        "timeseries": [
          {
            "key": "currentValue",
            "tag": "PLC.Current.Value",
            "type": "double"
          }
        ],
        "attributes_updates": [
          {
            "attributeOnThingsBoard": "setpoint",
            "attributeOnDevice": "PLC.Setpoint"
          }
        ]
      }
    ]
  }
}
```

### With RPC Methods

```json
{
  "server": {
    "name": "Your.OPC.Server",
    "host": "localhost",
    "pollPeriodInMillis": 5000,
    "mapping": [
      {
        "deviceNodePattern": "Motor",
        "deviceNamePattern": "Motor 1",
        "deviceTypePattern": "Motor",
        "timeseries": [
          {
            "key": "speed",
            "tag": "Motor.Speed",
            "type": "int"
          }
        ],
        "rpc_methods": [
          {
            "method": "setSpeed",
            "tag": "Motor.SpeedSetpoint"
          },
          {
            "method": "start",
            "tag": "Motor.Start",
            "value": true
          },
          {
            "method": "stop",
            "tag": "Motor.Start",
            "value": false
          }
        ]
      }
    ]
  }
}
```

## Remote OPC Server Connection

For connecting to a remote OPC server:

```json
{
  "server": {
    "name": "Your.OPC.Server",
    "host": "192.168.1.100",
    "pollPeriodInMillis": 5000,
    "mapping": [...]
  }
}
```

### DCOM Configuration for Remote Access

On the OPC Server machine (Windows):

1. Open Component Services (dcomcnfg)
2. Navigate to Component Services → Computers → My Computer
3. Right-click → Properties → Default Properties
4. Set Default Authentication Level to "Connect"
5. Set Default Impersonation Level to "Identify"
6. Apply

Configure OPC Server DCOM permissions:
1. Expand Component Services → Computers → My Computer → DCOM Config
2. Find your OPC Server
3. Right-click → Properties → Security
4. Configure Launch and Activation Permissions
5. Configure Access Permissions
6. Add the user account that will access the OPC server

## Troubleshooting

### "OPC server not found"

```python
# List available servers
import OpenOPC
opc = OpenOPC.client()
print(opc.servers())
```

Verify the server name matches exactly (case-sensitive).

### "Access Denied" errors

- Check DCOM permissions
- Run Python script with Administrator privileges
- Verify firewall rules

### "No data appearing in ThingsBoard"

1. Check gateway logs for errors
2. Verify tags exist in OPC server
3. Test tag reading with OpenOPC directly
4. Check ThingsBoard connection (access token)

### High CPU usage

- Increase `pollPeriodInMillis` value
- Reduce number of tags being polled
- Group related tags together

## Performance Tuning

### Optimal Poll Period

- For real-time monitoring: 1000-2000 ms
- For general monitoring: 5000-10000 ms
- For slow-changing values: 30000-60000 ms

### Tag Organization

Group related tags in the same device mapping for efficient bulk reading:

```json
{
  "deviceNodePattern": "ProductionLine1",
  "deviceNamePattern": "Production Line 1",
  "timeseries": [
    {"key": "speed", "tag": "Line1.Speed", "type": "int"},
    {"key": "count", "tag": "Line1.Count", "type": "int"},
    {"key": "efficiency", "tag": "Line1.Efficiency", "type": "double"}
  ]
}
```

## Next Steps

1. Configure your production OPC DA server details
2. Map your actual tags to device attributes and telemetry
3. Set up dashboards in ThingsBoard to visualize the data
4. Configure alarms and rules based on OPC DA data
5. Implement RPC methods for remote control

## Support and Resources

- ThingsBoard Gateway Documentation: https://thingsboard.io/docs/iot-gateway/
- OpenOPC Documentation: http://openopc.sourceforge.net/
- Community Forum: https://groups.google.com/forum/#!forum/thingsboard

## Example: Complete Working Configuration

See `opcda_config_example.json` for a complete, working example configuration.
