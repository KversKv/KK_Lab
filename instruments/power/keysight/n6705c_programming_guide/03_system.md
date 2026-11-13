# SYSTem Commands Introduction

System commands control system functions that are not directly related to output control, measurement, or status functions.

Common commands also control system functions such as self-test, saving and recalling states, and others.

| SCPI Command | Description |
|---|---|
| SYSTem |  |
| :CHANnel |  |
| [:COUNt]? | Returns the number of output channels in a mainframe |
| :MODel? (@chanlist) | Returns the model number of the selected channel |
| :OPTion? (@chanlist) | Returns the option installed in the selected channel |
| :SERial? (@chanlist) | Returns the serial number of the selected channel |
| :COMMunicate |  |
| :RLSTate LOCal \| REMote \| RWLock | Specifies the Remote/Local state of the instrument |
| :TCPip |  |
| :CONTrol? | Returns the control connection port number |
| :DATE | Sets the date of the system clock |
| :ERRor? | Returns the error number and error string |
| :GROup | (Group commands do NOT apply to N678xA SMU) |
| :CATalog? | Returns the groups that have been defined |
| :DEFine (@chanlist) | Group multiple channels to create a single output |
| :DELete \<channel\> | Removes the specified channel from a group |
| :ALL | Ungroups all channels |
| :PASSword |  |
| :FPANel:RESet | Resets the front panel lock password to zero |
| :REBoot | Returns the unit to its power-on state |
| :TIME | Sets the time of the system clock |
| :VERSion? | Returns the SCPI version number |

## SYSTem:CHANnel[:COUNt]?

### Syntax

```
SYSTem:CHANnel[:COUNt]?
```

### Description

This query returns the number of output channels in a mainframe.

### Return Format

\<NR1\> The number of output channels.

### Example

The following query returns the number of channels.

```
SYST:CHAN?
```

Typical Response:

```
+4
```

## SYSTem:CHANnel:MODel?

### Syntax

```
SYSTem:CHANnel:MODel? (@<chanlist>)
```

### Description

This query returns the model number of the specified output channels.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<AARD\> The model number of the output channel. Multiple responses are separated by commas.

### Example

The following query returns the model number in channels 2 and 3.

```
SYST:CHAN:MOD? (@2,3)
```

Typical Response:

```
N6751A,N6761A
```

## SYSTem:CHANnel:OPTion?

### Syntax

```
SYSTem:CHANnel:OPTion? (@<chanlist>)
```

### Description

This query returns a list of options installed in each channel specified in the channel list.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<SRD\> The query command returns an ASCII string enclosed in double quotes. If no option is installed, an empty quoted string ("") is returned. Multiple responses are separated by commas.

### Example

The following query returns the options in channels 1 through 3.

```
SYST:CHAN:OPT? (@1:3)
```

Response with options installed in channels 1 and 2, none in channel 3: Opt 760 ,

```
" " "Opt 760",""
```

## SYSTem:CHANnel:SERial?

### Syntax

```
SYSTem:CHANnel:SERial? (@<chanlist>)
```

### Description

This query returns the serial number of the specified output channels.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<AARD\> The serial number of the output channel. Multiple responses are separated by semicolons.

### Example

The following query returns the serial numbers in channels 2 and 3.

```
SYST:CHAN:SER? (@2,3)
```

Typical Response:

```
MY00123456;MY00234567
```

## SYSTem:COMMunicate:RLSTate

### Syntax

```
SYSTem:COMMunicate:RLSTate <state>
SYSTem:COMMunicate:RLSTate?
```

### Description

This command configures the remote/local state of the instrument according to the following settings: LOCal The instrument is set to front panel and remote interface control.

REMote The instrument is set to front panel and remote interface control.

RWLock The front panel keys are disabled. The instrument can only be controlled via the remote interface. This programmable setting is completely independent from the front panel lock/unlock function that is available from the front panel menu.

> **NOTE** The remote/local state is unaffected by \*RST or any SCPI commands other than SYSTem:COMMunicate:RLState.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<state\> | CPD | LOCal \| REMote \| RWLock | LOCal (set at power-on) |

### Remarks

The remote/local instrument state can also be set by other interface commands over the GPIB and some other I/O interfaces.

When multiple remote programming interfaces are active, the interface with the most recently changed remote/local state determines the instrument’s remote/local state.

### Return Format

\<CRD\> The query command returns LOC, REM, or RWL.

### Examples

The following command sets the remote/local state of the instrument.

```
SYST:COMM:RLST REMote
```

The following query returns the remote/local state of the instrument.

```
SYST:COMM:RLST?
```

Typical Response:

```
LOC
```

## SYSTem:COMMunicate:TCPip:CONTrol?

### Syntax

```
SYSTem:COMMunicate:TCPip:CONTrol?
```

### Description

This query returns the control connection port number. This is used to open a control socket connection to the instrument. Unlike the data socket, which uses a fixed port number (5025 for Keysight instruments), the port number for a control socket varies, and must be obtained using this query.

> **NOTE** Refer to chapter 3 of the User's Guide under “Using Sockets” for more information.

### Remarks

After the control port number is obtained, a control socket connection can be opened.

The control socket connection can only be used by a client to send a Device Clear to the instrument or to detect Service Request (SRQ) events.

All commands to the control socket must be terminated with a newline \<NL\>, and all query responses returned on the control socket will be terminated with a newline.

### Return Format

\<NR1\> The Control connection port number.

### Example

The following query returns the Control connection port number.

```
SYST:COMM:TCP:CONT?
```

Typical Response:

```
+5000
```

## SYSTem:DATE

### Syntax

```
SYSTem:DATE <yyyy>,<mm>,<dd>
SYSTem:DATE?
```

### Description

This command sets the date of the real time clock in year (yyyy), month (mm), and day (dd).

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<yyyy\> | NR1 | An 4-digit integer representing the year | Required parameter |
| \<mm\> | NR1 | An integer from 1 to 12 | Required parameter |
| \<dd\> | NR1 | An integer from 1 to 31 | Required parameter |

### Return Format

\<NR1\> The query command returns comma-separated values that correspond to the year, month, and day.

### Examples

The following command sets the date (April 1, 2007).

```
SYST:DATE 2007,4,1
```

The following query returns the date.

```
SYST:DATE?
```

Typical Response:

```
2007,4,1
```

## SYSTem:ERRor?

### Syntax

```
SYSTem:ERRor?
```

### Description

This query returns the next error number and its corresponding message string from the error queue.

For a complete listing of instrument and system error messages, see SCPI Error Messages.

### Remarks

The front-panel ERR annunciator turns on when one or more errors are currently stored in the error queue.

Errors are retrieved in first-in-first-out (FIFO) order. The first error returned is the first error that was stored.

Errors are cleared as you read them. When you have read all errors from the error queue, the ERR annunciator turns off and the errors are cleared.

If more errors have accumulated than the queue can hold, the last error stored in the queue (the most recent error) is replaced with

```
-
```

. No additional errors are stored until

```
350,"Error queue overflow"
```

you remove errors from the queue. If no errors have occurred when you read the error queue, the instrument responds with .

```
+0,"No error"
```

The error queue is cleared by the \*CLS (Clear Status) command and when power is cycled. The errors are also cleared when you read the error queue.

### Return Format

\<NR1\>,\<SRD\> The error string may contain up to 80 characters and consists of an error number and an error string enclosed in double quotes. For example: -113,"Undefined header".

### Example

The following query reads and clears one error.

```
SYST:ERR?
```

Typical Response:

```
-101,"Invalid character"
```

## SYSTem:GROup:CATalog?

### Syntax

```
SYSTem:GROup:CATalog?
```

### Description

This query returns information about channels that are grouped. The defined groups are enclosed in quotes.

> **NOTE** This command does NOT apply to models N678xA SMU.

### Return Format

\<SRD\> The defined groups in quotes. Multiple responses are separated by commas.

### Example

The following query returns the channels that are grouped.

```
SYST:GRO:CAT?
```

Response with 4 channels; none grouped:

```
"1","2","3","4"
```

Response with channels 1 + 2 grouped; 3 + 4 grouped:

```
"1,2","3,4"
```

Response with channels 1 - 3 grouped; channel 4 not grouped:

```
"1,2,3","4"
```

## SYSTem:GROup:DEFine

### Syntax

```
SYSTem:GROup:DEFine (@<chanlist>)
```

### Description

This command defines a list of output channels as a paralleled group. This effectively creates a single output with higher current and power capability. You can group up to four channels per mainframe.

All channels in a group must have identical model numbers and have identical options installed.

All grouped channels must have their output terminals and, if remote sensing, their sense terminals connected in parallel.

After the channels are wired in parallel and defined as a group, they can be addressed using any of the channel-specific SCPI commands by sending the channel number of the LOWEST channel in the group.

> **NOTE** This command does NOT apply to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | Two or more channels. (@1,2) - channels 1 and 2 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

For the group changes to take effect, you must reboot the unit. Either cycle AC power or send the SYSTem:REBoot command.

Group channel definitions are stored in non-volatile memory and are unaffected by \*RST or \*RCL.

Group channel settings (voltage, current, etc.) are set and saved by \*RST or \*RCL.

This command also deletes any previously saved states.

### Example

The following command defines channels 1 , 2, and 3 as a group.

```
SYST:GRO:DEF (@1:3)
```

The following command defines channels 1 and 4 as a group.

```
SYST:GRO:DEF (@1,4)
```

## SYSTem:GROup:DELete

### Syntax

```
SYSTem:GROup:DELete <channel>
```

### Description

This command removes the indicated channel from a group. It leaves the other channels in the group intact.

When ungrouping a channel, you must also remove the parallel connections between the output and sense terminals of that channel.

> **NOTE** This command does NOT apply to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | 1 \| 2 \| 3 \| 4 | Required parameter |

### Remarks

For the group changes to take effect, you must reboot the unit. Either cycle AC power or send the SYSTem:REBoot command.

This command also deletes any previously saved states.

### Example

The following command deletes channel 3 from a group.

```
SYST:GRO:DEL 3
```

## SYSTem:GROup:DELete:ALL

### Syntax

```
SYSTem:GROup:DELete:ALL
```

### Description

This command deletes all groups on a mainframe. It returns any channels that have been grouped back to an ungrouped state.

When ungrouping channels, you must also remove all paralleled sense and output terminal connections between channels.

> **NOTE** This command does NOT apply to models N678xA SMU.

### Remarks

For the group changes to take effect, you must reboot the unit. Either cycle AC power or send the SYSTem:REBoot command.

This command also deletes any previously saved states.

### Example

The following command deletes all groups.

```
SYST:GRO:DEL:ALL
```

## SYSTem:PASSword:FPANel:RESet

### Syntax

```
SYSTem:PASSword:FPANel:RESet
```

### Description

This command resets the front panel lockout password to the factory-shipped setting, which is zero (0). This command does not reset the calibration password.

> **NOTE** The front panel password can also be reset to 0 by setting an internal switch on the unit. Refer to the Service Manual under “Calibration Switches” for more information. This switch does NOT reset the front panel lockout password.

### Example

The following command resets the front panel password.

```
SYST:PASS:FPAN:RES
```

### See Also

\*RST

## SYSTem:REBoot

### Syntax

```
SYSTem:REBoot
```

### Description

This command causes the instrument to reboot to its power-on state.

### Example

The following command reboots the instrument.

```
SYST:REB
```

### See Also

\*RST

## SYSTem:TIME

### Syntax

```
SYSTem:TIME <hh>,<mm>,<ss>
SYSTem:TIME?
```

### Description

This command sets the real time clock in hours (hh), minutes (mm), and seconds (ss).

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<hh\> | NR1 | An integer from 0 to 23 | Required parameter |
| \<mm\> | NR1 | An integer from 0 to 59 | Required parameter |
| \<ss\> | NR1 | An integer from 0 to 59 | Required parameter |

### Return Format

\<NR1\> The query command returns comma-separated values that correspond to the hours, minutes, and seconds.

### Examples

The following command sets a time.

```
SYST:TIME 12,30,0
```

The following query returns the time of the clock.

```
SYST:TIME?
```

Typical Response:

```
12,30,0
```

## SYSTem:VERSion?

### Syntax

```
SYSTem:VERSion?
```

### Description

This command returns the version of the SCPI (Standard Commands for Programmable Instruments) standard with which the instrument is in compliance.

### Return Format

\<SRD\> The command returns a string in the form "YYYY.V", where YYYY represents the year of the version and V represents a version for that year.

### Example

The following query returns the SCPI version.

```
SYST:VERS?
```

Typical Response:

```
"2007.0"
```
