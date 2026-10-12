# Kali Agent Setup

This guide is for a Kali machine running the Wazuh agent when the Wazuh manager is inside the same Docker host as this Ariba SOC stack.

## Goal

Keep the agent reconnectable across normal network changes such as:

- Wi-Fi to LAN
- Home Wi-Fi to office Wi-Fi
- Temporary adapter resets

This does not keep a connection alive while the machine is actually offline. It only makes reconnect behavior reliable.

## Recommended Manager Address

Use the host loopback address in the Kali agent config:

```xml
<client>
  <server>
    <address>127.0.0.1</address>
    <port>1514</port>
    <protocol>tcp</protocol>
  </server>

  <config-profile>kali, kali-host, linux</config-profile>
  <notify_time>10</notify_time>
  <time-reconnect>60</time-reconnect>
  <auto_restart>yes</auto_restart>
</client>
```

Why this is the best fit for the Docker setup in this repo:

- `infrastructure/docker-compose.yml` publishes the manager port to the host.
- `127.0.0.1` does not change when the host moves between Wi-Fi and LAN.
- `tcp` avoids UDP loss behavior.
- `time-reconnect` and `auto_restart` help the agent recover after short disconnects.

Do not use:

- `192.168.x.x`
- `10.x.x.x`
- a public IP

for the same-host Docker lab. Those break as soon as the interface or network changes.

## When To Use Something Else

If the manager is not on the same host, use one of these instead:

- a stable DNS name
- a VPN IP such as WireGuard or Tailscale
- a local DNS override in `/etc/hosts` if the address is truly fixed

## Service Handling

After editing the config, restart the agent service.

Typical checks:

```bash
sudo systemctl restart wazuh-agent
sudo systemctl status wazuh-agent
```

If your install uses a different service name, keep the same restart/status pattern for that service.

## Connectivity Check

Verify that the agent can reach the published manager port:

```bash
nc -vz 127.0.0.1 1514
```

If that fails, check:

- the Docker stack is running
- the manager container is up
- the port mapping is present
- local firewall rules are not blocking the connection

## Troubleshooting

If the agent still disconnects frequently:

- confirm the manager is actually on the same host
- confirm the agent config uses `127.0.0.1`
- keep `protocol` set to `tcp`
- keep `time-reconnect` at `60` or lower
- avoid putting the manager on a changing Wi-Fi or LAN IP

If you need the agent to survive a full network outage, that is not possible. The best you can do is ensure it reconnects immediately once the network returns.
