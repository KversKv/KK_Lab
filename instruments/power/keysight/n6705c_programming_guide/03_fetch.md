# FETCh Subsystem Introduction

Fetch commands return measurement data that has been previously acquired. If you take a voltage measurement, you can fetch only voltage data. If you take a current measurement, you can fetch only current data.

Use Fetch commands to return measurement data that has been synchronized with a triggered event.

| SCPI Command | Description |
|---|---|
| FETCh |  |
| [:SCALar] |  |
| :CURRent |  |
| [:DC]? (@chanlist) | Returns the average current |
| :ACDC? (@chanlist) | Returns the total rms current (AC + DC) |
| :HIGH? (@chanlist) | Returns the high level of a current pulse |
| :LOW? (@chanlist) | Returns the low level of a current pulse |
| :MAXimum? (@chanlist) | Returns the maximum current |
| :MINimum? (@chanlist) | Returns the minimum current |
| :POWer |  |
| [:DC]? (@chanlist) | Returns the average output power |
| :VOLTage |  |
| [:DC]? (@chanlist) | Returns the average voltage |
| :ACDC? (@chanlist) | Returns the total rms voltage (AC + DC) |
| :HIGH? (@chanlist) | Returns the high level of a voltage pulse |
| :LOW? (@chanlist) | Returns the low level of a voltage pulse |
| :MAXimum? (@chanlist) | Returns the maximum voltage |
| :MINimum? (@chanlist) | Returns the minimum voltage |
| :ARRay |  |
| :CURRent [:DC]? (@chanlist) | Returns the instantaneous output current |
| :POWer [:DC]? (@chanlist) | Returns the instantaneous output power |
| :VOLTage [:DC]? (@chanlist) | Returns the instantaneous output voltage |
| :DLOG |  |
| :AHOur? (@chanlist) | Returns the amp-hours between markers |
| :CURRent |  |
| [:DC]? (@chanlist) | Returns the average current between markers |
| :MAXimum? (@chanlist) | Returns the maximum current between markers |
| :MINimum? (@chanlist) | Returns the minimum current between markers |
| :PTPeak? (@chanlist) | Returns the peak-to-peak current between markers |
| :VOLTage |  |
| [:DC]? (@chanlist) | Returns the average voltage between markers |
| :MAXimum? (@chanlist) | Returns the maximum voltage between markers |
| :MINimum? (@chanlist) | Returns the minimum voltage between markers |
| :PTPeak? (@chanlist) | Returns the peak-to-peak voltage between markers |
| :WHOur? (@chanlist) | Returns the watt-hours between markers |
| :ELOG \<NR1\>, (@chanlist) | Returns the most recent external data log records |
| :HISTogram |  |
| :CURRent? \<binrange\>, | Returns the histogram current data (N6781A, N6782A, N6785A, |
| (@chanlist) | N6786A) |

## FETCh[:SCALar]:CURRent[:DC]?

### Syntax

```
FETCh[:SCALar]:CURRent[:DC]? (@<chanlist>)
```

### Description

This query returns the average output current in amperes. The data returned is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the current measured on channel 1.

```
FETC:CURR? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage[:DC]?

## FETCh[:SCALar]:CURRent:ACDC?

### Syntax

```
FETCh[:SCALar]:CURRent:ACDC? (@<chanlist>)
```

### Description

This query returns the total RMS current (AC + DC) in amperes. The data returned is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the RMS current measured on channel 1.

```
FETC:CURR:ACDC? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage:ACDC?

## FETCh[:SCALar]:CURRent:HIGH?

### Syntax

```
FETCh[:SCALar]:CURRent:HIGH? (@<chanlist>)
```

### Description

This query returns the High level of a current pulse waveform in amperes.

The data used by this query calculation is the result of the last measurement command or triggered acquisition.

The High level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points above the 50% point is the high bin. The average of all the data points in the high bin is returned as the High level.

If no high bin contains more than 1.25% of the total number of acquired points, then the maximum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the high level of the current pulse on channel 1.

```
FETC:CURR:HIGH? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage:HIGH?

## FETCh[:SCALar]:CURRent:LOW?

### Syntax

```
FETCh[:SCALar]:CURRent:LOW? (@<chanlist>)
```

### Description

This query returns the Low level of a current pulse waveform in amperes.

The data used by this query calculation is the result of the last measurement command or triggered acquisition.

The Low level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points below the 50% point is the low bin. The average of all the data points in the low bin is returned as the Low level. If no low bin contains less than 1.25% of the total number of acquired points, then the minimum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the low level of the current pulse on channel 1.

```
FETC:CURR:LOW? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage:LOW?

## FETCh[:SCALar]:CURRent:MAXimum?

### Syntax

```
FETCh[:SCALar]:CURRent:MAXimum? (@<chanlist>)
```

### Description

This query returns the maximum value in amperes. The value is from the last measurement command or triggered acquisition.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum current value on channel 1.

```
FETC:CURR:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage:MAX?

## FETCh[:SCALar]:CURRent:MINimum?

### Syntax

```
FETCh[:SCALar]:CURRent:MINimum? (@<chanlist>)
```

### Description

This query returns the minimum value in amperes. The value is from the last measurement command or triggered acquisition.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum current value on channel 1.

```
FETC:CURR:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:VOLTage:MIN?

## FETCh[:SCALar]:POWer[:DC]?

### Syntax

```
FETCh[:SCALar]:POWer[:DC]? (@<chanlist>)
```

### Description

This query returns the average output power in watts. The data returned is the result of the last measurement command or triggered acquisition.

The data is valid until the next MEASure or INITiate command occurs. For triggered data acquisitions, you must enable BOTH current and voltage measurements (see SENSe:FUNCtion:CURRent and SENSe:FUNCtion:VOLTage).

> **NOTE** This command only applies to models N676xA and N678xA SMU. These models have simultaneous voltage and current measurement capability.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the powere measured on channel 1.

```
FETC:POW? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh:ARRay:POWer[:DC]?

## FETCh[:SCALar]:VOLTage[:DC]?

### Syntax

```
FETCh[:SCALar]:VOLTage[:DC]? (@<chanlist>)
```

### Description

This query returns the average output voltage in volts. The data returned is the result of the last measurement command or triggered acquisition.

The data is valid until the next MEASure or INITiate command occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the voltage measured on channel 1.

```
FETC:VOLT? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent[:DC]?

## FETCh[:SCALar]:VOLTage:ACDC?

### Syntax

```
FETCh[:SCALar]:VOLTage:ACDC? (@<chanlist>)
```

### Description

This query returns the total RMS voltage (AC + DC) in volts. The data returned is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the RMS voltage measured on channel 1.

```
FETC:VOLT:ACDC? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent:ACDC?

## FETCh[:SCALar]:VOLTage:HIGH?

### Syntax

```
FETCh[:SCALar]:VOLTage:HIGH? (@<chanlist>)
```

### Description

This query returns the High level of a voltage pulse waveform in volts. The data used by this query calculation is the result of the last measurement command or triggered acquisition.

The High level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points above the 50% point is the high bin. The average of all the data points in the high bin is returned as the High level.

If no high bin contains more than 1.25% of the total number of acquired points, then the maximum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the high level of the voltage pulse on channel 1.

```
FETC:VOLT:HIGH? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent:HIGH?

## FETCh[:SCALar]:VOLTage:LOW?

### Syntax

```
FETCh[:SCALar]:VOLTage:LOW? (@<chanlist>)
```

### Description

This query returns the Low level of a voltage pulse waveform in volts. The data used by this query calculation is the result of the last measurement command or triggered acquisition.

The Low level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points below the 50% point is the low bin. The average of all the data points in the low bin is returned as the Low level. If no low bin contains less than 1.25% of the total number of acquired points, then the minimum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the low level of the voltage pulse on channel 1.

```
FETC:VOLT:LOW? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent:LOW?

## FETCh[:SCALar]:VOLTage:MAXimum?

### Syntax

```
FETCh[:SCALar]:VOLTage:MAXimum? (@<chanlist>)
```

### Description

This query returns the maximum value in volts. The value is from the last measurement command or triggered acquisition.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum voltage value on channel 1.

```
FETC:VOLT:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent:MAX?

## FETCh[:SCALar]:VOLTage:MINimum?

### Syntax

```
FETCh[:SCALar]:VOLTage:MINimum? (@<chanlist>)
```

### Description

This query returns the minimum value in volts. The value is from the last measurement command or triggered acquisition.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum voltage value on channel 1.

```
FETC:VOLT:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

FETCh[:SCALar]:CURRent:MIN?

## FETCh:ARRay:CURRent[:DC]?

### Syntax

```
FETCh:ARRay:CURRent[:DC]? (@<chanlist>)
```

### Description

This query returns an array containing the digitized output current in amperes. The data returned by the FETCh command is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs.

The output current is digitized whenever a measurement command is sent or an acquisition trigger occurs. The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet. The number of points returned is set by SENSe:SWEep:POINts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the current measured on channel 1.

```
FETC:ARR:CURR? (@1)
```

### See Also

FETCh:ARRay:VOLTage[:DC]?

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

FORMat:BORDer FORMat:[:DATA]

## FETCh:ARRay:POWer[:DC]?

### Syntax

```
FETCh:ARRay:POWer[:DC]? (@<chanlist>)
```

### Description

This query returns an array containing the digitized output power in watts.

The data returned by the FETCh command is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs. For triggered data acquisitions, you must enable BOTH current and voltage measurements (see SENSe:FUNCtion:CURRent and SENSe:FUNCtion:VOLTage).

The output power is digitized whenever a measurement command is sent or an acquisition trigger occurs. The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet. The number of points returned is set by SENSe:SWEep:POINts.

> **NOTE** This command only applies to models N676xA and N678xA SMU. These models have simultaneous voltage and current measurement capability.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the power measured on channel 1.

```
FETC:ARR:POW? (@1)
```

### See Also

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

## FETCh:ARRay:VOLTage[:DC]?

### Syntax

```
FETCh:ARRay:VOLTage[:DC]? (@<chanlist>)
```

### Description

This query returns an array containing the digitized output voltage in volts. The data returned by the FETCh command is the result of the last measurement command or triggered acquisition. The data is valid until the next MEASure or INITiate command occurs.

The output voltage is digitized whenever a measurement command is sent or an acquisition trigger occurs. The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet. The number of points returned is set by SENSe:SWEep:POINts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The FETCh query does not perform a new measurement.

The FETCh query allows additional measurement calculations from the same acquired data.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the voltage measured on channel 1.

```
FETC:ARR:VOLT? (@1)
```

### See Also

FETCh:ARRay:CURRent[:DC]?

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

FORMat:BORDer FORMat:[:DATA]

## FETCh:DLOG:AHOur?

### Syntax

```
FETCh:DLOG:AHOur? (@<chanlist>)
```

### Description

This query returns the amp-hours delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Ah (amp-hours) value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the amp-hours delineated by the markers on channel 1.

```
FETC:DLOG:AHO? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:CURRent[:DC]?

### Syntax

```
FETCh:DLOG:CURRent[:DC]? (@<chanlist>)
```

### Description

This query returns the average output current that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Avg (average) value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the current delineated by the markers on channel 1.

```
FETC:DLOG:CURR? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:CURRent:MAXimum?

### Syntax

```
FETCh:DLOG:CURRent:MAXimum? (@<chanlist>)
```

### Description

This query returns the maximum DC output current that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Max value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum current delineated by the markers on channel 1.

```
FETC:DLOG:CURR:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:CURRent:MINimum?

### Syntax

```
FETCh:DLOG:CURRent:MINimum? (@<chanlist>)
```

### Description

This query returns the minimum DC output current that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Min value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum current delineated by the markers on channel 1.

```
FETC:DLOG:CURR:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:CURRent:PTPeak?

### Syntax

```
FETCh:DLOG:CURRent:PTPeak? (@<chanlist>)
```

### Description

This query returns the peak-to-peak output current that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Vp-p value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the peak-to-peak current delineated by the markers on channel 1.

```
FETC:DLOG:CURR:PTP? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:VOLTage[:DC]?

### Syntax

```
FETCh:DLOG:VOLTage[:DC]? (@<chanlist>)
```

### Description

This query returns the average output voltage that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Avg (average) value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the voltage delineated by the markers on channel 1.

```
FETC:DLOG:VOLT? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:VOLTage:MAXimum?

### Syntax

```
FETCh:DLOG:VOLTage:MAXimum? (@<chanlist>)
```

### Description

This query returns the maximum DC output voltage that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Max value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum voltage delineated by the markers on channel 1.

```
FETC:DLOG:VOLT:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:VOLTage:MINimum?

### Syntax

```
FETCh:DLOG:VOLTage:MINimum? (@<chanlist>)
```

### Description

This query returns the minimum DC output voltage that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Min value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum voltage delineated by the markers on channel 1.

```
FETC:DLOG:VOLT:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:VOLTage:PTPeak?

### Syntax

```
FETCh:DLOG:VOLTage:PTPeak? (@<chanlist>)
```

### Description

This query returns the peak-to-peak output voltage that is delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Loggger view. This value corresponds to the Vp-p value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the peak-to-peak voltage delineated by the markers on channel 1.

```
FETC:DLOG:VOLT:PTP? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:DLOG:WHOur?

### Syntax

```
FETCh:DLOG:WHOur? (@<chanlist>)
```

### Description

This query returns the watt-hours delineated by the front panel markers on the selected data log trace that appears in the instrument's Data Logger view. This value corresponds to the Wh (watt-hours) value shown on the bottom of the instrument's Data Logger view when markers are displayed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The value changes when the markers are moved either from the front panel or using the SCPI marker commands.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the watt-hours delineated by the markers on channel 1.

```
FETC:DLOG:WHO? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

SENSe:DLOG:MARKer\<1,2\>:POINt

## FETCh:ELOG?

### Syntax

```
FETCh:ELOG? <maxrecords>, (@<chanlist>)
```

### Description

This query returns external datalog data from the instrument’s buffer. The instrument has a buffer for each channel that holds 10 seconds of accumulated data. Data accumulates in the buffer at the rate determined by SENSe:ELOG:PERiod. Data must be read from the buffer periodically to avoid the buffer overflowing. The instrument assumes that there is only one reader of data, so whenever data is read using FETCh:ELOG? then that buffer space is made available in the instrument for storing more acquired data.

Maxrecords is the maximum number of records of external datalog data that the controller will return for each channel. A record is one set of voltage and current readings for one time interval. The exact format of a record depends on which functions have been enabled for external datalog sensing. If all functions are enabled, then one record will contain: Current average, Current minimum, Current maximum, Voltage average, Voltage minimum, Voltage maximum, in that order. If any of these sense functions are not enabled, that data is not part of the returned record. The values are returned as consecutive numbers in the response.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |
| \<maxrecord | NR1 | 1 to 16,384 (for 4 channels) | Required |
| s\> |  |  | parameter |

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns 100 data records of channel 1.

```
FETC:ELOG? 100, @1
```

### See Also

FORMat:BORDer FORMat[:DATA]

## FETCh:HISTogram:CURRent?

### Syntax

```
FETCh:HISTogram:CURRent? <binrange>, (@<chanlist>)
```

### Description

This query fetches the histogram current bin data. There are two bin ranges, with 4096 bins in each of the ranges.

Models N6781A/N6782A Models N6785A/N6786A

Range; Low High Low High Value: 7.8 mA 8 A 15.6 mA 16 A

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<binrange\> | Numeric | 8 \| 0.0078 (for N6781A/N6782A) 16 \| 0.0156 (for N6785A/N6786A) | Required parameter |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> [,\<NR3\>] The reading is in the form +n.nnnnnnE+nn. Bin values are separated by commas.

### Example

The following query returns the histogram current bin data of the 8 A range of channel 1.

```
FETC:HIST:CURR? 8, @1
```
