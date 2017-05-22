# ha-elkm1
Home Assistant component, platforms for Elk M1 Gold and similar alarm / integration panels

Uses https://github.com/BioSehnsucht/pyelk / https://pypi.python.org/pypi/PyElk

For the actual HA component, add something along these lines to your configuration YAML :

```
elkm1:
  host: socket://1.2.3.4:2101
  code: 1234
```

You can use ```host: /dev/ttyUSB0``` or such as well
