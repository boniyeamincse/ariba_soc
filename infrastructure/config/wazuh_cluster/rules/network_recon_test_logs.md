# Network Recon Test Logs

These are synthetic examples you can feed into your Wazuh source to verify the 100046-100055 rules.

## 100046 Internal Port Scan

```json
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"22"}
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"80"}
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"445"}
```

## 100047 External Port Scan

```json
{"srcip":"10.10.10.25","dstip":"198.51.100.10","dstport":"22"}
{"srcip":"10.10.10.25","dstip":"198.51.100.11","dstport":"80"}
{"srcip":"10.10.10.25","dstip":"198.51.100.12","dstport":"3389"}
```

## 100048 One Source to Many Internal Hosts

```json
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"445"}
{"srcip":"10.10.10.25","dstip":"10.10.10.11","dstport":"445"}
{"srcip":"10.10.10.25","dstip":"10.10.10.12","dstport":"445"}
```

## 100049 One Host touching many unusual ports

```json
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"4444"}
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"5555"}
{"srcip":"10.10.10.25","dstip":"10.10.10.10","dstport":"31337"}
```

## 100050 Suspicious or Random DNS Domain

```json
{"srcip":"10.10.10.25","dstip":"10.10.10.53","dstport":"53","query":"a8f7d3k9q1w2e4r6t8y0.example.com"}
```

## 100051 High Volume DNS Queries

```json
{"srcip":"10.10.10.25","dstip":"10.10.10.53","dstport":"53","query":"update.example.com"}
{"srcip":"10.10.10.25","dstip":"10.10.10.53","dstport":"53","query":"cdn.example.com"}
{"srcip":"10.10.10.25","dstip":"10.10.10.53","dstport":"53","query":"api.example.com"}
```

## 100052 Connection to Known Malicious IOC

```json
{"srcip":"10.10.10.25","dstip":"203.0.113.250","dstport":"443"}
```

## 100053 Unusual Outbound Connection

```json
{"srcip":"10.10.10.25","dstip":"198.51.100.40","dstport":"4444"}
{"srcip":"10.10.10.25","dstip":"198.51.100.41","dstport":"5555"}
```

## 100054 Restricted Server Access

```json
{"srcip":"10.10.10.25","dstip":"203.0.113.251","dstport":"3389"}
```

## 100055 Possible Lateral Movement

```json
{"srcip":"10.10.10.25","dstip":"203.0.113.251","dstport":"3389"}
{"srcip":"10.10.10.25","dstip":"203.0.113.252","dstport":"3389"}
```

