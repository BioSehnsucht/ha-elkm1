# ha-elkm1
Home Assistant component, platforms for Elk M1 Gold and similar alarm / integration panels

Uses https://github.com/gwww/elkm1 / https://pypi.org/project/elkm1/

For documentation on the HASS components themselves (WIP - may be behind or ahead of functionality released on Github), see:
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/elkm1.markdown
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/alarm_control_panel.elkm1.markdown
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/climate.elkm1.markdown
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/light.elkm1.markdown
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/sensor.elkm1.markdown
* https://github.com/BioSehnsucht/home-assistant.github.io/blob/elkm1-gwww/source/_components/switch.elkm1.markdown

# Installation
Git clone or download release archive and place files in `(HASS config wherever it is)/custom_components/`.

You should have the following files after doing so in your HASS `config` directory:
```
custom_components/elkm1.py
custom_components/alarm_control_panel/elkm1.py
custom_components/climate/elkm1.py
custom_components/light/elkm1.py
custom_components/sensor/elkm1.py
custom_components/switch/elkm1.py
```

# Configuration
For details of other options, see the linked documentation above. The basic configuration to get started (in your HASS `configuration.yaml` is:
```yaml
elkm1:
  # 'elk' for unsecure TCP connections, 'elks' for secure TCP. 
  # For direct attached serial, use 'serial:///dev/ttyUSB0' on Unix-like systems (Linux, OS/X, etc)
  # or 'serial://COM1' on Windows.
  host: elk://127.0.0.1
  # username and password only used for elks protocol, ignored for elk
  username: myname
  password: mysecret
```

# Common issues
* First startup sometimes doesn't install the `elkm1` library dependency fast enough and you may get errors about the `elkm1` component failing to start. If this happens, try restarting HASS a second time.
* When using direct attached serial connection on Unix-type systems, note there will be three `/`'s (two `//` to separate protocol from the rest of the URI, and one `/` as part of the device path)
* If ElkRP is connected to the Elk, we can't send any messages (arm, disarm, query, etc) to the Elk, they are ignored. Disconnect ElkRP and the integration should resume working as expected.
* If your user code has `ACCESS` permission it may be unable to arm the alarm through HASS.
