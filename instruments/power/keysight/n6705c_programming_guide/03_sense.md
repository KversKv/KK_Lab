# SENSe Subsystem Introduction

Sense commands control the current measurement range, the bandwidth detector of the instrument, and the data acquisition sequence.

| SCPI Command | Description |
|---|---|
| SENSe |  |
| :CURRent |  |
| :CCOMpensate \<Bool\>, (@chanlist) | Enables/disables the capacitive current compensation |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Selects the current measurement range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A, N6785A, N6786A) |
| :DLOG |  |
| :CURRent |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the internal data log current range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A, N6785A, N6786A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current data logging |
| :MINMax \<Bool\> | Enables/disables min/max data logging |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables voltage data logging |
| :MARKer\<1,2\> |  |
| :POINt \<NRf+\> | Positions the data log markers |
| :OFFSet \<NR1\> | Sets trigger offset as a percent from start of data log duration |
| :PERiod \<NRf+\> | Sets the interval between samples (replaces TINTerval) |
| :TIME \<NRf+\> | Sets the duration of the data log in seconds |
| :TINTerval \<NRf+\> | Sets the interval between samples (for backward compatibility) |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the internal data log voltage range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A) |
| :ELOG |  |
| :CURRent |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the external data log current range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A, N6785A, N6786A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables external current data logging |
| :MINMax \<Bool\>, (@chanlist) | Enables/disables external min/max current data logging |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables external voltage data logging |
| :MINMax \<Bool\>, (@chanlist) | Enables/disables external min/max voltage data logging |
| :PERiod \<NR1\>, (@chanlist) | Sets the integration time of the external data logging |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the external data log voltage range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A) |
| :FUNCtion “VOLTage”\|”CURRent” \| “NONE”, | Enables the measurement function (for backward compatibility) |
| (@chanlist) |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current measurements (replaces FUNCtion) |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables voltage measurements (replaces FUNCtion) |
| :INPut MAIN \| AUXiliary, (@chanlist) | Selects the voltage measurement input (only on N6781A, N6785A) |

| SCPI Command | Description |
|---|---|
| SENSe (continued) |  |
| :HISTogram |  |
| :CURRent |  |
| [:DC]:BIN |  |
| :GAIN? \<binrange\>, (@chanlist) | Queries the LSB weight of the histogram (N6781A, N6782A, N6785A, and N6786A) |
| :OFFSet? \<binrange\>, (@chanlist) | Queries the weight of the histogram (N6781A, N6782A, N6785A, N6786A) |
| :RANGes? (@chanlist) | Queries the values of the bin ranges (N6781A, N6782A, N6785A, N6786A) |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the measurement range of the histogram (N6781A, N6782A, N6785A,N6786A) |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A, N6785A, N6786A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current histogram (N6781A, N6782A, N6785A, N6786A) |
| :SWEep |  |
| :OFFSet |  |
| :POINts \<NRf+\>, (@chanlist) | Defines the trigger offset in the measurement sweep |
| :POINts \<NRf+\>, (@chanlist) | Defines the number of data points in the measurement |
| :TINTerval \<NRf+\>, (@chanlist) | Sets the measurement sample interval |
| :RESolution RES20 \| RES40 | Sets the measurement sample interval |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Selects the voltage measurement range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781A, N6782A) |
| :WINDow |  |
| [:TYPE] HANNing \| RECTangular, (@chanlist) | Selects the window type |

## SENSe:CURRent[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:CURRent[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:CURRent[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects a DC current measurement range on models that have multiple ranges. The value that you enter must be higher than the maximum current that you expect to measure. Units are in amperes. The instrument selects the range with the best resolution for the value entered. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum DC current that can be measured on the range that is presently set.

> **NOTE** Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 100 mA range on channel 3.

```
SENS:CURR:RANG 0.1,(@3)
```

The following query returns the range selected on channel 3.

```
SENS:CURR:RANG? (@3)
```

Typical Response:

```
+1.000000E-01
```

### See Also

SENSe:VOLTage[:DC]:RANGe

## SENSe:CURRent[:DC]:RANGe:AUTO

### Syntax

```
SENSe:CURRent[:DC]:RANGe:AUTO <Bool>, (@<chanlist>)
SENSe:CURRent[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables current measurement autoranging.

Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges. Autoranging does not include the 10 μA range, which must be selected individually.

When enabled, this command overrides the SENSe:CURRent[:DC]:RANGe setting.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A.

Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if current measurement autoranging is OFF, and 1 if current measurement autoranging is ON.

### Examples

The following command turns current measurement autoranging ON for channel 2.

```
SENS:CURR:RANG:AUTO ON,(@2)
```

The following query returns the current measurement autorange setting of channel 1.

```
SENS:CURR:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:CURRent[:DC]:RANGe

## SENSe:CURRent:CCOMpensate

### Syntax

```
SENSe:CURRent:CCOMpensate <Bool>, (@<chanlist>)
SENSe:CURRent:CCOMpensate? (@<chanlist>)
```

### Description

This command turns current measurement compensation ON or OFF on the specified output channel.

When turned ON, this function corrects the output current measurement for the current that flows into the output capacitor. This current is only significant when high dv/dt occurs, and because this current does not flow into the output load, it represents an error when not corrected. Note that turning on the current measurement compensation increases the peak to peak noise in current measurements.

This command does not apply to Models N678xA SMU.

> **NOTE** On Models N676xA this command only applies in the High current range.

On Models N6751A/N6752A this command requires Option LGA to be installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if current measurement compensation is OFF, and 1 if current measurement compensation is ON.

### Examples

The following command turns current measurement compensation ON for output channel 2.

```
SENS:CURR:CCOM ON,(@2)
```

The following query returns the current measurement compensation setting of channel 1.

```
SENS:CURR:CCOM? (@1)
```

Typical Response:

```
0
```

## SENSe:DLOG:CURRent[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:DLOG:CURRent[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:DLOG:CURRent[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects the internal datalog current measurement range on models that have multiple ranges. The value that you enter must be the highest value in amperes that you expect to measure. The instrument selects the best range that can be used to make this measurement. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum current that can be measured on the range that is presently set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 100 mA range on channel 3.

```
SENS:DLOG:CURR:RANG 0.1,(@3)
```

The following query returns the range selected on channel 3.

```
SENS:DLOG:CURR:RANG? (@3)
```

Typical Response:

```
+1.000000E-01
```

### See Also

SENSe:DLOG:VOLTage:RANGe

## SENSe:DLOG:CURRent[:DC]:RANGe:AUTO

### Syntax

```
SENSe:DLOG:CURRent[:DC]:RANGe:AUTO <Bool>,
(@<chanlist>)
SENSe:DLOG:CURRent[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables the internal datalog current measurement autoranging. Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges. Autoranging does not include the 10 μA range, which must be selected individually.

When enabled, this command overrides the SENS:DLOG:CURR:RANG setting.

> **NOTE** This command only applies to models N6781A and N6782A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if current data logging autoranging is OFF, and 1 if current data logging autoranging is ON.

### Examples

The following command turns current data logging autoranging ON for channel 2.

```
SENS:DLOG:CURR:RANG:AUTO ON,(@2)
```

The following query returns the current data logging autorange setting of channel 1.

```
SENS:DLOG:CURR:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:DLOG:CURRent:RANGe

## SENSe:DLOG:FUNCtion:CURRent

### Syntax

```
SENSe:DLOG:FUNCtion:CURRent <Bool>, (@<chanlist>)
SENSe:DLOG:FUNCtion:CURRent? (@<chanlist>)
```

### Description

This command turns current data logging ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if current data logging is OFF, and 1 if current data logging is ON.

### Examples

The following command turns current data logging ON for output channel 2.

```
SENS:DLOG:FUNC:CURR ON,(@2)
```

The following query returns the current data logging setting of channel 1.

```
SENS:DLOG:FUNC:CURR? (@1)
```

Typical Response:

```
0
```

## SENSe:DLOG:FUNCtion:MINMax

### Syntax

```
SENSe:DLOG:FUNCtion:MINMax <Bool>
SENSe:DLOG:FUNCtion:MINMax?
```

### Description

This command enables/disables the logging of the minimum and maximum values to the datalog file.

Although data is logged to the data file at the logging interval, it is sampled at a rate of 20.48 microseconds. When the data is logged, the minimum, maximum, and average values are computed from all of the samples taken during the logging interval. With

SENSe:DLOG:FUNCtion:MINMax disabled, only the average values are entered into the datalog file. With SENSe:DLOG:FUNCtion:MINMax enabled, all three values are entered into the datalog file - thus tripling its size.

This function cannot be enabled when interleaved data logging is in effect.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |

### Return Format

\<NR1\> The query command returns 0 if MIN/MAX logging is OFF, and 1 if MIN/MAX logging is ON.

### Examples

The following command turns MIN/MAX logging ON for all output channels.

```
SENS:DLOG:FUNC:MINM ON
```

The following query returns the MIN/MAX logging setting.

```
SENS:DLOG:FUNC:MINM?
```

Typical Response:

```
1
```

## SENSe:DLOG:FUNCtion:VOLTage

### Syntax

```
SENSe:DLOG:FUNCtion:VOLTage <Bool>, (@<chanlist>)
SENSe:DLOG:FUNCtion:VOLTage? (@<chanlist>)
```

### Description

This command turns voltage data logging ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | ON |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if voltage data logging is OFF, and 1 if voltage data logging is ON.

### Examples

The following command turns voltage data logging ON for output channel 2.

```
SENS:DLOG:FUNC:VOLT ON,(@2)
```

The following query returns the voltage data logging setting of channel 1.

```
SENS:DLOG:FUNC:VOLT? (@1)
```

Typical Response:

```
0
```

## SENSe:DLOG:MARKer\<1,2\>:POINt

### Syntax

```
SENSe:DLOG:MARKer<1,2>:POINt <seconds>
SENSe:DLOG:MARKer<1,2>:POINt?
```

### Description

This command set the position of the data logger markers. Positions are set in seconds relative to the trigger position. A negative time gives positions before the trigger.

The marker positions are adjusted to the closest actual sample point.

Querying the marker positions after a FETCh:DLOG:CURRent? or FETCh:DLOG:VOLTage? query will return the exact time point that corresponds to the returned measurement data.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<seconds\> | NRf+ | - 3,599,964,000 to +3,599,964,000 | 7.5 s - for marker 1 27.5 s - for marker 2 |

### Return Format

\<NR1\> The query command returns the position of the marker from the trigger in seconds.

### Examples

The following command specifies a Marker1 point of 50 seconds after the trigger.

```
SENS:DLOG:MARK1:POIN 50
```

The following query returns the data log Marker 1 point.

```
SENS:DLOG:MARK1:POIN?
```

Typical Response:

```
5000
```

### See Also

FETCh:DLOG:CURRent?

FETCh:DLOG:VOLTage?

## SENSe:DLOG:OFFSet

### Syntax

```
SENSe:DLOG:OFFSet <percent>
SENSe:DLOG:OFFSet?
```

### Description

This command specifies the datalog trigger offset as a percent of the total datalog duration. Programming a trigger offset lets you specify the percent of pre-trigger data that will be logged to the datalog file.

A percent of 0 means the trigger occurs at the beginning of the running datalog, while 100 means that the trigger occurs at the end of the running datalog. Any value between 0 and 100 can be set.

The offset must be set to zero when interleaved data logging is in effect.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<percent\> | NR1 | 0 - 100 | 0 |

### Return Format

\<NR1\> The query command returns the trigger offset percentage.

### Examples

The following command specifies a trigger offset of 50%.

```
SENS:DLOG:OFFS 50
```

The following query returns the trigger offset setting.

```
SENS:DLOG:OFFS?
```

Typical Response:

```
50
```

## SENSe:DLOG:PERiod

### Syntax

```
SENSe:DLOG:PERiod <seconds>
SENSe:DLOG:PERiod? [MIN|MAX]
```

### Description

This command specifies the period of the datalog samples in seconds.

Although the absolute minimum logging period is 20.48 microseconds, the actual minimum varies as a function of the number of channels and readings that are being logged. The actual minimum is (20.48 microseconds x number of parameters being logged at each interval). So for example if average voltage, minimum voltage, maximum voltage, and average current are being logged for a single channel, the minimum logging period is (4 parameters X 20.48) = 81.9 microseconds. Values are rounded to the nearest 20.48-microsecond increment.

This function cannot be set to values less than 75 milliseconds when interleaved data logging is in effect.

> **NOTE** This command replaces the previous SENSe:DLOG:TINTerval command and should be used in new applications. SENSe:DLOG:TINTerval is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<seconds\> | NRf+ | 0.00002048 - 60 \| MIN \| MAX | 0.1 |

### Return Format

\<NR1\> The query command returns the datalog period in seconds.

### Examples

The following command specifies a datalog period of 0.01 seconds.

```
SENS:DLOG:PER 0.01
```

The following query returns the datalog period.

```
SENS:DLOG:PER?
```

Typical Response:

```
0.01
```

## SENSe:DLOG:TIME

### Syntax

```
SENSe:DLOG:TIME <seconds>
SENSe:DLOG:TIME? [MIN|MAX]
```

### Description

This command specifies the duration of the datalog in seconds. Values from 1 second up to the equivalent of 99,999 hours can be specified.

The resulting datalog file cannot exceed 2E9 bytes (1.87 Gbytes in Microsoft Windows units). If the duration value causes the file to exceeds this size, the time interval will automatically be adjusted to a longer interval to reduce the file size.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<seconds\> | NRf+ | 1 - 3,599,964,000 \| MIN \| MAX | 30 |

### Return Format

\<NR1\> The query command returns the duration of the datalog in seconds.

### Examples

The following command specifies a datalog duration of 5000 seconds.

```
SENS:DLOG:TIME 5000
```

The following query returns the datalog duration.

```
SENS:DLOG:TIME?
```

Typical Response:

```
5000
```

## SENSe:DLOG:TINTerval

### Syntax

```
SENSe:DLOG:TINTerval <seconds>
SENSe:DLOG:TINTerval? [MIN|MAX]
```

### Description

This command specifies the time interval between datalog samples in seconds. Values from 1 millisecond to 60 seconds can be specified. This function cannot be set to values less than 75 milliseconds when interleaved data logging is in effect.

> **NOTE** This command has been superceded by SENSe:DLOG:PERiod, but is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<seconds\> | NRf+ | 0.001 - 60 \| MIN \| MAX | 0.1 |

### Return Format

\<NR1\> The query command returns the datalog time interval in seconds.

### Examples

The following command specifies a datalog time interval of 0.01 seconds.

```
SENS:DLOG:TINT 0.01
```

The following query returns the datalog time interval.

```
SENS:DLOG:TINT?
```

Typical Response:

```
0.01
```

### See Also

SENSe:DLOG:PERiod

## SENSe:DLOG:VOLTage[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:DLOG:VOLTage[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:DLOG:VOLTage[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects the internal datalog voltage measurement range on models that have multiple ranges. The value that you enter must be the highest value in volts that you expect to measure. The instrument selects the best range that can be used to make this measurement. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum voltage that can be measured on the range that is presently set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 5 V range on channel 3.

```
SENS:DLOG:VOLT:RANG 5,(@3)
```

The following query returns the range selected on channel 1.

```
SENS:DLOG:VOLT:RANG? (@1)
```

Typical Response:

```
+5.500000E+01
```

### See Also

SENSe:DLOG:CURRent:RANGe

## SENSe:DLOG:VOLTage[:DC]:RANGe:AUTO

### Syntax

```
SENSe:DLOG:VOLTage[:DC]:RANGe:AUTO <Bool>,
(@<chanlist>)
SENSe:DLOG:VOLTage[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables the internal datalog voltage measurement autoranging. Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges.

When enabled, this command overrides the SENSe:DLOG:VOLTage:RANGe setting.

> **NOTE** This command only applies to models N6781A and N6782A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if voltage data logging autoranging is OFF, and 1 if voltage data logging autoranging is ON.

### Examples

The following command turns voltage data logging autoranging ON for channel 2.

```
SENS:DLOG:VOLT:RANG:AUTO ON,(@2)
```

The following query returns the voltage data logging autorange setting of channel 1.

```
SENS:DLOG:VOLT:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:DLOG:VOLTage:RANGe

## SENSe:ELOG:CURRent[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:ELOG:CURRent[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:ELOG:CURRent[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects the external datalog current measurement range on models that have multiple ranges. The value that you enter must be the highest value in amperes that you expect to measure. The instrument selects the best range that can be used to make this measurement. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum current that can be measured on the range that is presently set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 100 mA range on channel 3.

```
SENS:ELOG:CURR:RANG 0.1,(@3)
```

The following query returns the range selected on channel 3.

```
SENS:ELOG:CURR:RANG? (@3)
```

Typical Response:

```
+1.000000E-01
```

### See Also

SENSe:ELOG:VOLTage:RANGe

## SENSe:ELOG:CURRent[:DC]:RANGe:AUTO

### Syntax

```
SENSe:ELOG:CURRent[:DC]:RANGe:AUTO <Bool>,
(@<chanlist>)
SENSe:ELOG:CURRent[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables the external datalog current measurement autoranging. Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges. Autoranging does not include the 10 μA range, which must be selected individually.

When enabled, this command overrides the SENSe:ELOG:CURRent:RANGe setting.

> **NOTE** This command only applies to models N6781A and N6782A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if current data logging autoranging is OFF, and 1 if current data logging autoranging is ON.

### Examples

The following command turns external current data logging autoranging ON for channel 2.

```
SENS:ELOG:CURR:RANG:AUTO ON,(@2)
```

The following query returns the external current data logging autorange setting of channel 1.

```
SENS:ELOG:CURR:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:ELOG:CURRent:RANGe

## SENSe:ELOG:FUNCtion:CURRent

### Syntax

```
SENSe:ELOG:FUNCtion:CURRent <Bool>, (@<chanlist>)
SENSe:ELOG:FUNCtion:CURRent? (@<chanlist>)
```

### Description

This command turns external current data logging ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if external current data logging is OFF, and 1 if current data logging is ON.

### Examples

The following command turns external current data logging ON for output channel 2.

```
SENS:ELOG:FUNC:CURR ON,(@2)
```

The following query returns the external current data logging setting of channel 1.

```
SENS:ELOG:FUNC:CURR? (@1)
```

Typical Response:

```
0
```

## SENSe:ELOG:FUNCtion:CURRent:MINMax

### Syntax

```
SENSe:ELOG:FUNCtion:CURRent:MINMax <Bool>,
(@<chanlist>)
SENSe:ELOG:FUNCtion:CURRent:MINMax? (@<chanlist>)
```

### Description

This command turns external current data logging of the minimum and maximum current measurements ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if external minimum and maximum current measurements is OFF, and 1 if minimum and maximum current measurements is ON.

### Examples

The following command turns external minimum and maximum current measurements ON for output channel 2.

```
SENS:ELOG:FUNC:CURR:MINM ON,(@2)
```

The following query returns the external minimum and maximum current measurements setting of channel 1.

```
SENS:ELOG:FUNC:CURR:MINM? (@1)
```

Typical Response:

```
0
```

## SENSe:ELOG:FUNCtion:VOLTage

### Syntax

```
SENSe:ELOG:FUNCtion:VOLTage <Bool>, (@<chanlist>)
SENSe:ELOG:FUNCtion:VOLTage? (@<chanlist>)
```

### Description

This command turns external voltage data logging ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | ON |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if external voltage data logging is OFF, and 1 if voltage data logging is ON.

### Examples

The following command turns external voltage data logging ON for output channel 2.

```
SENS:ELOG:FUNC:VOLT ON,(@2)
```

The following query returns the external voltage data logging setting of channel 1.

```
SENS:ELOG:FUNC:VOLT? (@1)
```

Typical Response:

```
0
```

## SENSe:ELOG:FUNCtion:VOLTage:MINMax

### Syntax

```
SENSe:ELOG:FUNCtion:VOLTage:MINMax <Bool>,
(@<chanlist>)
SENSe:ELOG:FUNCtion:VOLTage:MINMax? (@<chanlist>)
```

### Description

This command turns external voltage data logging of the minimum and maximum voltage measurements ON or OFF on the specified output channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if external minimum and maximum voltage measurements is OFF, and 1 if minimum and maximum voltage measurements is ON.

### Examples

The following command turns external minimum and maximum voltage measurements ON for output channel 2.

```
SENS:ELOG:FUNC:VOLT:MINM ON,(@2)
```

The following query returns the external minimum and maximum voltage measurements setting of channel 1.

```
SENS:ELOG:FUNC:VOLT:MINM? (@1)
```

Typical Response:

```
0
```

## SENSe:ELOG:PERiod

### Syntax

```
SENSe:ELOG:PERiod <seconds>, (@<chanlist>)
SENSe:ELOG:PERiod? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the averaging (or integration) time of an external datalog measurement. Datalog measurement records are generated at the rate determined by this time interval.

Although the absolute minimum logging period is 102.4 microseconds, the actual minimum varies as a function of the number of channels and readings that are being logged. The limiting factor is the speed at which data can be fetched from the FIFO buffer. The actual minimum is (102.4 microseconds x number of parameters being logged at each interval). So for example if average voltage, minimum voltage, maximum voltage, and average current are being logged for a single channel, the minimum logging period is (4 parameters X 102.4) = 409.6 microseconds. Values are rounded to the nearest 20.48-microsecond increment.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<seconds\> | NRf+ | 0.0001024 to 60 \| MIN \| MAX | 0.1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns the external datalog period in seconds.

### Examples

The following command specifies an external datalog period of 0.01 seconds for channel 1.

```
SENS:ELOG:PER 0.01,(@1)
```

The following query returns the external datalog period from channel 1.

```
SENS:ELOG:PER? (@1)
```

Typical Response:

```
0.01
```

## SENSe:ELOG:VOLTage[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:ELOG:VOLTage[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:ELOG:VOLTage[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects the external datalog voltage measurement range on models that have multiple ranges. The value that you enter must be the highest value in volts that you expect to measure. The instrument selects the best range that can be used to make this measurement. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum voltage that can be measured on the range that is presently set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 5 V range on channel 3.

```
SENS:ELOG:VOLT:RANG 5,(@3)
```

The following query returns the range selected on channel 1.

```
SENS:ELOG:VOLT:RANG? (@1)
```

Typical Response:

```
+5.500000E+01
```

### See Also

SENSe:ELOG:CURRent:RANGe

## SENSe:ELOG:VOLTage[:DC]:RANGe:AUTO

### Syntax

```
SENSe:ELOG:VOLTage[:DC]:RANGe:AUTO <Bool>,
(@<chanlist>)
SENSe:ELOG:VOLTage[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables the external datalog voltage measurement autoranging. Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges.

When enabled, this command overrides the SENSe:ELOG:VOLTage:RANGe setting.

> **NOTE** This command only applies to models N6781A and N6782A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if voltage data logging autoranging is OFF, and 1 if voltage data logging autoranging is ON.

### Examples

The following command turns external voltage data logging autoranging ON for channel 2.

```
SENS:ELOG:VOLT:RANG:AUTO ON,(@2)
```

The following query returns the external voltage data logging autorange setting of channel 1.

```
SENS:ELOG:VOLT:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:ELOG:VOLTage:RANGe

## SENSe:FUNCtion

### Syntax

```
SENSe:FUNCtion <"function">, (@<chanlist>)
SENSe:FUNCtion? (@<chanlist>)
```

### Description

This command selects a measurement function on models that do not have simultaneous voltage and current measurement capability. This command is required so that the acquisition system knows which measurement function to acquire when a measurement is triggered.

Selecting NONE disables the measurement function.

> **NOTE** This command has been superceded by the SENSe:FUNCtion:CURRent and SENSe:FUNCtion:VOLTage commands, which should be used in new applications. SENSe:FUNCtion is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"function " \> | SPD | "CURRent"\|"VOLTage"\|"NONE" Parameters must be enclosed in single or double quotes | VOLTage |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<SRD\> The query command returns an ASCII string enclosed in double quotes for each channel specified. Multiple responses are separated by commas.

The short form of the parameter is always returned.

### Examples

The following command selects the voltage function on channel 3.

```
SENS:FUNC "VOLT", (@3)
```

The following query returns the function selected on channel 1 (quotes are also returned).

```
SENS:FUNC? (@1)
```

Typical Response:

```
"VOLT"
```

## SENSe:FUNCtion:CURRent

### Syntax

```
SENSe:FUNCtion:CURRent <Bool>, (@<chanlist>)
SENSe:FUNCtion:CURRent? (@<chanlist>)
```

### Description

This command enables or disables the current measurement function. It applies to all models, including those that have simultaneous voltage and current measurement capability. On modules with simultaneous measurement capability, you can enable BOTH current and voltage measurements (see SENSe:FUNCtion:VOLTage).

> **NOTE** This command replaces the previous SENSe:FUNCtion command and should be used in new applications. SENSe:FUNCtion is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the current measurements are disabled, and 1 if current measurements are enabled.

### Examples

The following command enables current measurements on channel 3.

```
SENS:FUNC:CURR ON, (@3)
```

The following query returns the current measurement state of channel 3.

```
SENS:FUNC:CURR? (@3)
```

Typical Response:

```
1
```

### See Also

SENSe:FUNCtion:VOLTage

## SENSe:FUNCtion:VOLTage

### Syntax

```
SENSe:FUNCtion:VOLTage <Bool>, (@<chanlist>)
SENSe:FUNCtion:VOLTage? (@<chanlist>)
```

### Description

This command enables or disables the voltage measurement function. It applies to all models, including those that have simultaneous voltage and current measurement capability. On modules with simultaneous measurement capability, you can enable BOTH current and voltage measurements (see SENSe:FUNCtion:CURRent).

> **NOTE** This command replaces the previous SENSe:FUNCtion command and should be used in new applications. SENSe:FUNCtion is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the voltage measurements are disabled, and 1 if voltage measurements are enabled.

### Examples

The following command enables voltage measurements on channel 3.

```
SENS:FUNC:VOLT ON, (@3)
```

The following query returns the voltage measurement state of channel 3.

```
SENS:FUNC:VOLT? (@3)
```

Typical Response:

```
1
```

### See Also

SENSe:FUNCtion:CURRent

## SENSe:FUNCtion:VOLTage:INPut

### Syntax

```
SENSe:FUNCtion:VOLTage:INPut <input>, (@<chanlist>)
SENSe:FUNCtion:VOLTage:INPut? (@<chanlist>)
```

### Description

This command selects the voltage measurement input on models that have an auxiliary voltage measurement input. Selecting MAIN selects the front panel binding posts as the measurement inputs. Selecting AUXiliary selects the rear panel auxiliary voltage inputs as the measurement inputs.

> **NOTE** This command only applies to models N6781A and N6785A, which have auxiliary voltage measurement capability.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<input\> | CPD | MAIN \| AUXiliary | MAIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<SRD\> The query command returns an ASCII string for each channel specified.

Multiple responses are separated by commas. The short form of the parameter is always returned.

### Examples

The following command selects the auxiliary voltage input on channel 3.

```
SENS:FUNC:VOLT:INP AUX, (@3)
```

The following query returns the function selected on channel 1.

```
SENS:FUNC:VOLT:INP? (@1)
```

Typical Response:

```
MAIN
```

## SENSe:HISTogram:CURRent[:DC]:BIN:GAIN?

### Syntax

```
,
SENSe:HISTogram:CURRent[:DC]:BIN:GAIN? <binrange>
(@<chanlist>)
```

### Description

This queries the LSB (or scaling factor) of a histogram in amperes per bin number. Histogram bins are numbered 0 through 4095, and the mean current value of a bin is: Current = (bin number x gain) + offset where gain is the value returned by this command, and offset is the value returned by SENS:HIST:CURR:BIN:OFFS. The gains and offsets vary slightly between units of the same model because of software calibration.

Binrange specifies one of the two histogram ranges. Each range has 4096 bins with a minimum and maximum amplitude and a bin size as follows:

Models N6781A/N6782A Models N6785A/N6786A

Range; Low High Low High Amplitude: - 7.8 mA to +7.8 - 8 A to +8 A - 15.6 mA to +15.6 - 16 A to +16 A mA mA Bin Size: 3.8 µ A 3.9 mA 7.6 µ A 7.8 mA

> **NOTE** This command only applies to models N6781A, N6782A, N6785A and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<binrange\> | Numeric | 8 \| 0.0078 (for N6781A/N6782A) 16 \| 0.0156 (for N6785A/N6786A) | Required parameter |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn. Multiple values are separated by commas.

### Example

The following query returns the histogram current bin gain of the 8 A range of channel 1.

```
SENS:HIST:CURR:BIN:GAIN? 8, (@1)
```

### See Also

SENSe:HISTogram:CURRent:BIN:OFFSet?

## SENSe:HISTogram:CURRent[:DC]:BIN:OFFSet?

### Syntax

```
,
SENSe:HISTogram:CURRent[:DC]:BIN:OFFSet? <binrange>
(@<chanlist>)
```

### Description

This queries the weight of the histogram in amperes. Histogram bins are numbered 0 through 4095, and the mean current value of a bin is: Current = (bin number x gain) + offset where gain is the value returned by SENS:HIST:CURR:BIN:GAIN, and offset is the value returned by this command. The gains and offsets vary slightly between units of the same model because of software calibration.

Binrange specifies one of the two histogram ranges. Each range has 4096 bins with a minimum and maximum amplitude and a bin size as follows:

Models N6781A/N6782A Models N6785A/N6786A

Range; Low High Low High Amplitude: - 7.8 mA to - 8 A to +8 A - 15.6 mA to - 16 A to +16 A +7.8 mA +15.6 mA Bin Size: 3.8 µ A 3.9 mA 7.6 µ A 7.8 mA

> **NOTE** This command only applies to models N6781A, N6782A, N6785A and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<binrange\> | Numeric | 8 \| 0.0078 (for N6781A/N6782A) 16 \| 0.0156 (for N6785A/N6786A) | Required parameter |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn. Multiple values are separated by commas.

### Example

The following query returns the histogram current bin offset of the 8 A range of channel 1.

```
SENS:HIST:CURR:BIN:OFFS? 8, (@1)
```

### See Also

SENSe:HISTogram:CURRent:BIN:GAIN?

## SENSe:HISTogram:CURRent[:DC]:BIN:RANGes?

### Syntax

```
SENSe:HISTogram:CURRent[:DC]:BIN:RANGes?
(@<chanlist>)
```

### Description

This queries the values of the current bin ranges. The following values are returned: Models N6781A/N6782A Models N6785A/N6786A

Range; Low High Low High Value: 7.8 mA 8 A 15.6 mA 16 A

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following query returns the current bin ranges on channel 3.

```
SENS:HIST:CURR:BIN:RANG? (@3)
```

Typical Response:

```
+8.000000E+00, +7.80000E-03
```

## SENSe:HISTogram:CURRent[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:HISTogram:CURRent[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:HISTogram:CURRent[:DC]:RANGe[:UPPer]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command selects the current histogram measurement range. The value that you enter must be the highest value in amperes that you expect to measure. The instrument selects the best range that can be used to make this measurement. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum current that can be measured on the range that is presently set.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 100 mA range on channel 3.

```
SENS:HIST:CURR:RANG 0.1,(@3)
```

The following query returns the range selected on channel 3.

```
SENS:HIST:CURR:RANG? (@3)
```

Typical Response:

```
+1.000000E-01
```

### See Also

SENSe:HISTogram:CURRent:RANGe:AUTO

## SENSe:HISTogram:CURRent[:DC]:RANGe:AUTO

### Syntax

```
SENSe:HISTogram:CURRent[:DC]:RANGe:AUTO <Bool>,
(@<chanlist>)
SENSe:HISTogram:CURRent[:DC]:RANGe:AUTO?
(@<chanlist>)
```

### Description

This command enables/disables histogram current measurement autoranging. Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges. Autoranging does not include the 10 μA range, which must be selected individually.

When enabled, this command overrides the SENSe:HISTogram:CURRent:RANGe setting.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if histogram measurement autoranging is OFF, and 1 if current measurement autoranging is ON.

### Examples

The following command turns histogram measurement autoranging ON for channel 2.

```
SENS:HIST:CURR:RANG:AUTO ON,(@2)
```

The following query returns the histogram measurement autorange setting of channel 1.

```
SENS:HIST:CURR:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:HISTogram:CURRent:RANGe

## SENSe:HISTogram:FUNCtion:CURRent

### Syntax

```
SENSe:HISTogram:FUNCtion:CURRent <Bool>,
(@<chanlist>)
SENSe:HISTogram:FUNCtion:CURRent? (@<chanlist>)
```

### Description

This command turns the current histogram function ON or OFF on the specified output channel.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the current histogram is OFF, and 1 if the current histogram is ON.

### Examples

The following command turns the current histogram ON for output channel 2.

```
SENS:HIST:FUNC:CURR ON,(@2)
```

The following query returns the current histogram setting of channel 1.

```
SENS:HIST:FUNC:CURR? (@1)
```

Typical Response:

```
0
```

## SENSe:SWEep:OFFSet:POINts

### Syntax

```
SENSe:SWEep:OFFSet:POINts <points>, (@<chanlist>)
SENSe:SWEep:OFFSet:POINts? [MIN|MAX,] (@<chanlist>)
```

### Description

This command defines the offset in a data sweep when the measurement is triggered. Programmed values can range from –(SENS:SWE:POIN setting –1) through 2,000,000,000 (2E9). Positive values represent the delay after the trigger occurs but before the samples are acquired. Negative values represent data samples taken prior to the trigger. The maximum negative value that can be programmed is one less than the maximum allowable SENSe:SWEep:POINts value.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<points\> | NRf+ | -524.287 - 2,000,000,000 \| MIN \| MAX | 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the number of offset points for each channel specified. Multiple responses are separated by commas.

### Examples

The following command specifies -2048 offset points on channel 3.

```
SENS:SWE:OFFS:POIN -2048,(@3)
```

The following query returns the number of offset points specified for channel 1.

```
SENS:SWE:OFFS:POIN? (@1)
```

Typical Response:

```
+0
```

### See Also

SENSe:SWEep:POINts

SENSe:SWEep:TINTerval

TRIGger:ACQuire:SOURce

## SENSe:SWEep:POINts

### Syntax

```
SENSe:SWEep:POINts <points>, (@<chanlist>)
SENSe:SWEep:POINts? [MIN|MAX,] (@<chanlist>)
```

### Description

This command defines the number of points in a measurement. The number of samples (points) that can be specified depends on the number of measurement parameters selected. You can measure up to eight parameters (voltage and current X 4 outputs).

1 parameter: up to 512 K points 2 parameters: up to 256 K points 3 parameters: up to 128 K points 4 parameters: up to 64 K points (K = 1024)

> **NOTE** Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<points\> | NRf+ | 1 – 512 K\* \| MIN \| MAX (\*for 1 measurement parameter) | N678xA SMU: 4883 All other modules: 1024 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns the number of points for each channel specified. Multiple responses are separated by commas.

### Examples

The following command specifies 2048 measurement points on channel 3.

```
SENS:SWE:POIN 2048,(@3)
```

The following query returns the number of points specified for channel 1.

```
SENS:SWE:POIN? (@1)
```

Typical Response:

```
+1024
```

### See Also

SENSe:SWEep:OFFSet:POINts

SENSe:SWEep:TINTerval

## SENSe:SWEep:TINTerval

### Syntax

```
SENSe:SWEep:TINTerval <interval>, (@<chanlist>)
SENSe:SWEep:TINTerval? [MIN|MAX,] (@<chanlist>)
```

### Description

This command defines the time period between samples in seconds.

Programmed values can range from 5.12 microseconds (for one measurement parameter on Models N678xA SMU) to 40,000 seconds.

Note that the shortest time interval (fastest speed) that can be specified depends on the number of parameters that are being measured and the model that is doing the measuring. Values above 10.24 microseconds are rounded to the nearest 10.24-microsecond increment. Values above 20.48 microseconds are rounded to the nearest 20.48-microsecond increment.

5.12 microseconds: 1 parameter on Models N678xA only 10.24 microseconds: 1 or 2 parameters on all models 20.48 microseconds: 3 or 4 parameters on all models

> **NOTE** Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<interval\> | NRf+ | 0.00000512 – 40,000 \| MIN \| MAX | 0.00002048 seconds |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the time interval for each channel specified.

The value returned is the time period rounded to the nearest 20.48 microsecond increment; which is not necessarily the value that was programmed. Multiple responses are separated by commas.

### Examples

The following command specifies a time interval of 1 second between measurement points on channel 3.

```
SENS:SWE:TINT 1,(@3)
```

The following query returns the measurement time interval for channel 1.

```
SENS:SWE:TINT? (@1)
```

Typical Response:

```
+2.048000E-5
```

### See Also

SENSe:SWEep:OFFSet:POINts

SENSe:SWEep:POINts

## SENSe:SWEep:TINTerval:RESolution

### Syntax

```
SENSe:SWEep:TINTerval:RESolution <resolution>
SENSe:SWEep:TINTerval:RESolution?
```

### Description

This command sets the resolution used in setting the time interval between digitized measurements for time intervals above 20.48 microseconds. Note that external data log measurements also use this resolution setting. The following resolutions may be specified:.

> **NOTE** RES20: rounds all values above 20.48 microseconds to the nearest multiple of 20.48 microseconds RES40: rounds all values above 20.48 microseconds to the nearest multiple of 40.96 microseconds This command is used only with models N676xA, N678xA SMU, or models that have Option 054 (High Speed Test Extensions).

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<resolution\> | CPD | RES20 \| RES40 | 0.00002048 seconds |

### Return Format

\<NR3\> The query command returns the measurement resolution.

### Examples

The following command specifies a measurement resolution of 40 microseconds.

```
SENS:SWE:TINT:RES RES40
```

The following query returns the measurement resolution.

```
SENS:SWE:TINT:RES?
```

Typical Response:

```
RES20
```

### See Also

SENSe:SWEep:TINTerval

SENSe:ELOG:PERiod

## SENSe:VOLTage[:DC]:RANGe[:UPPer]

### Syntax

```
SENSe:VOLTage[:DC]:RANGe[:UPPer] <range>,
(@<chanlist>)
SENSe:VOLTage[:DC]:RANGe[:UPPer]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command selects a DC voltage measurement range on models that have multiple ranges. The programmed value must be the maximum voltage that you expect to measure. Units are in volts. The instrument selects the range with the best resolution for the value entered. MIN selects the lowest range; MAX selects the highest range.

When queried, the returned value is the maximum DC voltage that can be measured on the range that is presently set.

> **NOTE** Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View. .

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the range in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects the 5 V range on channel 3.

```
SENS:VOLT:RANG 5,(@3)
```

The following query returns the range selected on channel 1.

```
SENS:VOLT:RANG? (@1)
```

Typical Response:

```
+5.500000E+01
```

### See Also

SENSe:CURRent[:DC]:RANGe

## SENSe:VOLTage[:DC]:RANGe:AUTO

### Syntax

```
SENSe:VOLTage[:DC]:RANGe:AUTO <Bool>, (@<chanlist>)
SENSe:VOLTage[:DC]:RANGe:AUTO? (@<chanlist>)
```

### Description

This command enables/disables voltage measurement autoranging.

Autoranging provides seamless measurement ranging, which results in a wide dynamic range with no data being lost across ranges.

When enabled, this command overrides the SENSe:VOLTage[:DC]:RANGe setting.

> **NOTE** This command only applies to models N6781A and N6782A. Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if voltage measurement autoranging is OFF, and 1 if voltage measurement autoranging is ON.

### Examples

The following command turns voltage measurement autoranging ON for channel 2.

```
SENS:VOLT:RANG:AUTO ON,(@2)
```

The following query returns the voltage measurement autorange setting of channel 1.

```
SENS:VOLT:RANG:AUTO? (@1)
```

Typical Response:

```
0
```

### See Also

SENSe:VOLTage[:DC]:RANGe

## SENSe:WINDow[:TYPE]

### Syntax

```
SENSe:WINDow[:TYPE] <window>, (@<chanlist>)
SENSe:WINDow[:TYPE]? (@<chanlist>)
```

### Description

This command sets a signal conditioning function used in DC measurement calculations on models that have measurement controls.

Select from the following filter window types: HANNing The Hanning window is a "raised cosine" function. It is a signal conditioning function that reduces errors in DC measurement calculations in the presence of periodic signals such as AC line ripple.

RECTangular A window that returns measurement calculations with no signal conditioning.

Note that neither window function alters the instantaneous voltage or current data returned in the measurement array.

> **NOTE** Refer to “Front Panel Preferences” in the User’s Guide to enable this command in Meter View. .

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<window\> | CPD | HANNing \| RECTangular | RECTangular |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the window setting for each channel specified. Multiple responses are separated by commas.

### Examples

The following command specifies a RECTangular measurement window for channel 3.

```
SENS:WIND RECT,(@3)
```

The following query returns the measurement window for channel 1.

```
SENS:WIND? (@1)
```

Typical Response:

```
RECT
```
