# CALibrate Subsystem Introduction

This subsystem lets you calibrate the instrument. Only one channel can be calibrated at a time.

If calibration mode has not been enabled with CALibrate:STATe, the calibration commands will generate an error. Use CALibrate:SAVE to save any changes, otherwise all changes will be lost when you exit calibration mode.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

| SCPI Command | Description |
|---|---|
| CALibrate |  |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@channel) | Calibrates the output current programming |
| :LIMit |  |
| :NEGative \<NRf\>, | Calibrates the negative current limit (only on N6783A) |
| (@channel) |  |
| :POSitive \<NRf\>, | Calibrates the positive current limit (only on N678xA SMU) |
| (@channel) |  |
| :MEASure \<NRf\>, (@channel) | Calibrates the current measurement |
| :PEAK (@channel) | Calibrates the peak current limit (only on N675xA, N676xA) |
| :DATA \<NRf\> | Enters the calibration value |
| :DATE \<”date”\>, (@channel) | Sets the calibration date |
| :DPRog (@channel) | Calibrates the current downprogrammer |
| :LEVel P1 \| P2 \| P3 | Advances to the next calibration step |
| :PASSword \<NRf\> | Sets the numeric calibration password |
| :RESistance 20\| 6, (@channel) | Calibrates the output resistance (only on N6781A, N6785A) |
| :SAVE | Saves the new cal constants in non-volatile memory |
| :STATE \<Bool\> [,\<NRf\>] | Enables/disables calibration mode |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@channel) | Calibrates the output voltage programming |
| :CMRR (@channel) | Calibrates common mode rejection ratio (only on N675xA, N676xA) |
| :LIMit |  |
| :POSitive \<NRf\>, | Calibrates the positive voltage limit (only on N678xA SMU) |
| (@channel) |  |
| :MEASure \<NRf\>, (@channel) | Calibrates the voltage measurement |
| :AUXiliary (@channel) | Calibrates the auxiliary voltage measurement (only on N6781A, N6785A) |

## CALibrate:CURRent[:LEVel]

### Syntax

```
CALibrate:CURRent[:LEVel] <value>, (@<channel>)
```

### Description

This command initiates calibration of the output current. The value that you enter selects the range that is being calibrated.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum current of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the current of channel 1.

```
CAL:CURR 10.2,(@1)
```

### See Also

CALibrate:CURRent:MEASure

CALibrate:CURRent:PEAK

## CALibrate:CURRent:LIMit:NEGative

### Syntax

```
CALibrate:CURRent:LIMit:NEGative <value>,
(@<channel>)
```

### Description

This command initiates calibration of the negative current limit. The value is programmed in amperes and must be specified as negative. The value that you enter selects the range that is being calibrated. There is only one negative current range.

> **NOTE** This command only applies to models N6783A. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum current of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the negative current limit of channel 1.

```
CAL:CURR:LIM:NEG -2,(@1)
```

### See Also

CALibrate:CURRent:MEASure

## CALibrate:CURRent:LIMit:POSitive

### Syntax

```
CALibrate:CURRent:LIMit:POSitive <value>,
(@<channel>)
```

### Description

This command initiates calibration of the positive current limit. The value that you enter selects the range that is being calibrated.

> **NOTE** This command only applies to models N678xA SMU. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum current of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the positive current limit of channel 1.

```
CAL:CURR:LIM:POS 3,(@1)
```

### See Also

CALibrate:CURRent:MEASure

## CALibrate:CURRent:MEASure

### Syntax

```
CALibrate:CURRent:MEASure <value>, (@<channel>)
```

### Description

This command initiates calibration of the current measurement range.

The value that you enter selects the range that is being calibrated.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum current of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the current measurement range of channel 1.

```
CAL:CURR:MEAS 10.2,(@1)
```

### See Also

CALibrate:CURRent[:LEVel]

CALibrate:CURRent:PEAK

## CALibrate:CURRent:PEAK

### Syntax

```
CALibrate:CURRent:PEAK (@<channel>)
```

### Description

This command initiates calibration of the peak current limit.

> **NOTE** This command only applies to models N675xA and N676xA. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the peak current limit of channel 1.

```
CAL:CURR:PEAK (@1)
```

### See Also

CALibrate:CURRent[:LEVel]

CALibrate:CURRent:MEASure

## CALibrate:DATA

### Syntax

```
CALibrate:DATA <value>
```

### Description

This command enters a calibration value that you obtain by reading an external meter. You must first select a calibration level (with

CALibrate:LEVel) for the value being entered. Data values are expressed in base units - either volts or amperes, depending on which function is being calibrated.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The measured voltage or current value. | Required parameter |

### Example

The following command enters a value measured by an external meter.

```
CAL:DATA 10.01
```

### See Also

CALibrate:LEVel

## CALibrate:DATE

### Syntax

```
CALibrate:DATE <"date">, (@<channel>)
CALibrate:DATE?
```

### Description

This command stores the date that the power module was last calibrated.

The calibration date is stored in nonvolatile memory. Enter any ASCII string up to 16 characters. The query returns the date.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<”date”\> | SPD | String program data. String parameters must be enclosed in single or double quotes. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Remarks

The firmware does not interpret the string format. The information is not used by the firmware. The command is only provided to store the calibration date.

### Return Format

\<SRD\> The query command returns an ASCII string enclosed in double quotes. If no date is stored, an empty quoted string ("") is returned.

### Example

The following command enters a date.

```
CAL:DATE "4/22/11",(@1)
```

The following query returns the calibration date.

```
CAL:DATE?
```

Typical Response:

```
"April 22, 2011"
```

## CALibrate:DPRog

### Syntax

```
CALibrate:DPRog (@<channel>)
```

### Description

This command initiates calibration of the current downprogrammer.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the current downprogrammer of channel 1.

```
CAL:DPR (@1)
```

## CALibrate:LEVel

### Syntax

```
CALibrate:LEVel <level>
```

### Description

This command is used to advance to the next level in the calibration. P1 is the first calibration level; P2 is the second level; P3 is the third level.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<level\> | CPD | P1 \| P2 \| P3 | Required parameter |

### Remarks

Some calibration sequences may require some settling time after sending CAL:LEV but before reading the data from the DVM and sending CAL:DATA.

### Example

The following command selects the first calibration level.

```
CAL:LEV P1
```

### See Also

CALibrate:DATA

## CALibrate:PASSword

### Syntax

```
CALibrate:PASSword <password>
```

### Description

This command lets you change the calibration password. The new password is automatically stored in nonvolatile memory and does not have to be stored with CALibrate:SAVE. If the password is set to 0, password protection is removed and the ability to enter calibration mode is unrestricted. The factory-default password 0 (zero).

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<password\> | NRf | A numeric value up to 15 digits in length. | Required parameter |

### Example

The following command sets the password to a value of 1234.

```
CAL:PASS 1234
```

## CALibrate:RESistance

### Syntax

```
CALibrate:RESistance <range>, (@<channel>)
```

### Description

This command initiates calibration of the output resistance.

> **NOTE** This command only applies to models N6781A and N6785A. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | Numeric | 20 \| 6 | 20 V |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the output resistance of the 20 V range of channel 1.

```
CAL:RES 20, (@1)
```

## CALibrate:SAVE

### Syntax

```
CALibrate:SAVE
```

### Description

This command saves calibration constants in non-volatile memory after the calibration procedure has been completed. If calibration mode is exited by programming CALibration:STATe OFF without first saving the new constants, the previous constants are restored.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Example

The following command saves the calibration values.

```
CAL:SAVE
```

### See Also

CALibrate:STATe

## CALibrate:STATe

### Syntax

```
CALibrate:STATe <Bool>, [<password>]
CALibrate:STATe?
```

### Description

This command enables or disables calibration mode. Calibration mode must be enabled for the instrument to accept any calibration commands.

The first parameter specifies the ON (1) or OFF (0) state. The second parameter is the password.

A numeric password is required if calibration mode is being enabled and the existing password is not 0. If the password is not entered or is incorrect, an error is generated and the calibration mode remains disabled.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<password\> | NRf | A numeric value up to 15 digits in length. | Required if password not 0 |

### Remarks

When the calibration state is changed from enabled to disabled, new calibration constants are lost unless they have already been stored with CALibrate:SAVE.

### Return Format

\<NR1\> The query returns only the calibration state, not the password. It returns either 0 (OFF), or 1 (ON).

### Example

The following command enables calibration mode; the password is 1234.

```
CAL:STAT ON, 1234
```

The following query returns the calibration state.

```
CAL:STAT?
```

Typical Response:

```
1
```

### See Also

CALibrate:SAVE

## CALibrate:VOLTage[:LEVel]

### Syntax

```
CALibrate:VOLTage[:LEVel] <value>, (@<channel>)
```

### Description

This command initiates calibration of the output voltage. The value that you enter selects the range that is being calibrated.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum voltage of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the voltage of channel 1.

```
CAL:VOLT 51,(@1)
```

### See Also

CALibrate:VOLTage:MEASure

CALibrate:VOLTage:CMRR

## CALibrate:VOLTage:CMRR

### Syntax

```
CALibrate:VOLTage:CMRR (@<channel>)
```

### Description

This command initiates calibration of the voltage common mode rejection ratio.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the voltage common mode rejection ratio of channel 1.

```
CAL:VOLT:CMRR (@1)
```

### See Also

CALibrate:VOLTage[:LEVel]

CALibrate:VOLTage:MEASure

## CALibrate:VOLTage:LIMit:POSitive

### Syntax

```
CALibrate:VOLTage:LIMit:POSitive <value>,
(@<channel>)
```

### Description

This command initiates calibration of the positive voltage limit. The value that you enter selects the range that is being calibrated.

> **NOTE** This command only applies to model N678xA SMU. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum voltage of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the positive voltage limit of channel 1.

```
CAL:VOLT:LIM:POS 20,(@1)
```

### See Also

CALibrate:VOLTage:MEASure

## CALibrate:VOLTage:MEASure

### Syntax

```
CALibrate:VOLTage:MEASure <value>, (@<channel>)
```

### Description

This command initiates calibration of the voltage measurement range.

The value that you enter selects the range that is being calibrated.

> **NOTE** Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | The maximum voltage of the range that is being calibrated. | Required parameter |
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the voltage measurement range of channel 1.

```
CAL:VOLT:MEAS 51,(@1)
```

### See Also

CALibrate:VOLTage[:LEVel]

CALibrate:VOLTage:CMRR

## CALibrate:VOLTage:MEASure:AUXiliary

### Syntax

```
CALibrate:VOLTage:MEASure:AUXiliary (@<channel>)
```

### Description

This command initiates calibration of the auxiliary voltage measurement input.

> **NOTE** This command only applies to models N6781A and N6785A. Refer to Chapter 3 in the Service Guide for a detailed description of the calibration procedure.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | The output channel that is being calibrated. | Required parameter |

### Example

The following command calibrates the auxiliary voltage measurement input of channel 1.

```
CAL:VOLT:MEAS:AUX (@1)
```
