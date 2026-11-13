# DISPlay Commands Introduction

The Display commands let you control the front panel display.

| SCPI Command | Description |
|---|---|
| DISPlay |  |
| [:WINDow] |  |
| :VIEW METER1 \| METER4 | Selects 1-channel or 4-channel meter view |

## DISPlay[:WINDow]:VIEW

### Syntax

```
DISPlay[:WINDow]:VIEW <view>
DISPlay[:WINDow]:VIEW?
```

### Description

This command selects the output channel view of the front panel display.

METER1 displays one output channel. METER4 displays all output channels up to a maximum of four.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<view\> | CPD | METER1 \| METER4 | METER1 |

### Return Format

\<CRD\> The query command returns METER1 or METER4.

### Example

The following command sets the front panel to display only one output channel.

```
DISP:VIEW METER1
```

The following query returns the channel view of the front-panel display.

```
DISP:VIEW?
```

Typical Response:

```
METER1
```
