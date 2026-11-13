# MEASure Subsystem Introduction

Measure commands measure the output voltage or current. They trigger the acquisition of new data before returning the reading. Measurements are performed by digitizing the instantaneous output voltage or current for a specified measurement time, storing the results in a buffer, and calculating the average value. Use Measure commands when the measurement does not need to be synchronized with any other event.

| SCPI Command | Description |
|---|---|
| MEASure |  |
| [:SCALar] |  |
| :CURRent |  |
| [:DC]? (@chanlist) | Takes a measurement; returns the average current |
| :ACDC? (@chanlist) | Takes a measurement; returns the total rms current (AC + DC) |
| :HIGH? (@chanlist) | Takes a measurement; returns the high level of a current pulse |
| :LOW? (@chanlist) | Takes a measurement; returns the low level of a current pulse |
| :MAXimum? (@chanlist) | Takes a measurement, returns the maximum current |
| :MINimum? (@chanlist) | Takes a measurement, returns the minimum current |
| :POWer |  |
| [:DC]? (@chanlist) | Takes a measurement; returns the average output power |
| :VOLTage |  |
| [:DC]? (@chanlist) | Takes a measurement; returns the average voltage |
| :ACDC? (@chanlist) | Takes a measurement; returns the total rms voltage (AC + DC) |
| :HIGH? (@chanlist) | Takes a measurement; returns the high level of a voltage pulse |
| :LOW? (@chanlist) | Takes a measurement; returns the low level of a voltage pulse |
| :MAXimum? (@chanlist) | Takes a measurement, returns the maximum voltage |
| :MINimum? (@chanlist) | Takes a measurement, returns the minimum voltage |
| :ARRay | (Array commands only on N676xA, N678xA SMU and Option 054) |
| :CURRent [:DC]? (@chanlist) | Takes a measurement; returns the instantaneous output current |
| :POWer [:DC]? (@chanlist) | Takes a measurement, returns the instantaneous output power |
| :VOLTage [:DC]? (@chanlist) | Takes a measurement; returns the instantaneous output voltage |

## MEASure[:SCALar]:CURRent[:DC]?

### Syntax

```
MEASure[:SCALar]:CURRent[:DC]? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the average output current in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the current measured on channel 1.

```
MEAS:CURR? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage[:DC]?

## MEASure[:SCALar]:CURRent:ACDC?

### Syntax

```
MEASure[:SCALar]:CURRent:ACDC? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the total RMS current (AC + DC) in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the RMS current measured on channel 1.

```
MEAS:CURR:ACDC? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage:ACDC?

## MEASure[:SCALar]:CURRent:HIGH?

### Syntax

```
MEASure[:SCALar]:CURRent:HIGH? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the High level of a current pulse waveform in amperes.

The High level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points above the 50% point is the high bin. The average of all the data points in the high bin is returned as the High level.

If no high bin contains more than 1.25% of the total number of acquired points, then the maximum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the high level of a current pulse on channel 1.

```
MEAS:CURR:HIGH? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage:HIGH?

## MEASure[:SCALar]:CURRent:LOW?

### Syntax

```
MEASure[:SCALar]:CURRent:LOW? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the Low level of a current pulse waveform in amperes.

The Low level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points below the 50% point is the low bin. The average of all the data points in the low bin is returned as the Low level. If no low bin contains less than 1.25% of the total number of acquired points, then the minimum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the low level of a current pulse on channel 1.

```
MEAS:CURR:LOW? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage:LOW?

## MEASure[:SCALar]:CURRent:MAXimum?

### Syntax

```
MEASure[:SCALar]:CURRent:MAXimum? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the maximum value in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum current value on channel 1.

```
MEAS:CURR:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage:MAX?

## MEASure[:SCALar]:CURRent:MINimum?

### Syntax

```
MEASure[:SCALar]:CURRent:MINimum? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the minimum value in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum current value on channel 1.

```
MEAS:CURR:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:VOLTage:MIN?

## MEASure[:SCALar]:POWer[:DC]?

### Syntax

```
MEASure[:SCALar]:POWer[:DC]? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the average output power in watts.

> **NOTE** This command only applies to models N676xA and N678xA SMU. These models have simultaneous voltage and current measurement capability.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the power measured on channel 1.

```
MEAS:POW? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure:ARRay:POWer[:DC]?

## MEASure[:SCALar]:VOLTage[:DC]?

### Syntax

```
MEASure[:SCALar]:VOLTage[:DC]? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the average output voltage in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the voltage measured on channel 1.

```
MEAS:VOLT? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent[:DC]?

## MEASure[:SCALar]:VOLTage:ACDC?

### Syntax

```
MEASure[:SCALar]:VOLTage:ACDC? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the total RMS voltage (AC + DC) in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the RMS voltage measured on channel 1.

```
MEAS:VOLT:ACDC? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent:ACDC?

## MEASure[:SCALar]:VOLTage:HIGH?

### Syntax

```
MEASure[:SCALar]:VOLTage:HIGH? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the High level of a voltage pulse waveform in volts.

The High level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points above the 50% point is the high bin. The average of all the data points in the high bin is returned as the High level.

If no high bin contains more than 1.25% of the total number of acquired points, then the maximum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the high level of a voltage pulse on channel 1.

```
MEAS:VOLT:HIGH? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent:HIGH?

## MEASure[:SCALar]:VOLTage:LOW?

### Syntax

```
MEASure[:SCALar]:VOLTage:LOW? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the Low level of a voltage pulse waveform in volts.

The Low level calculation generates a histogram of the waveform using 16 bins between the maximum and minimum data points. The bin containing the most data points below the 50% point is the low bin. The average of all the data points in the low bin is returned as the Low level. If no low bin contains less than 1.25% of the total number of acquired points, then the minimum data point is returned.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the low level of a voltage pulse on channel 1.

```
MEAS:VOLT:LOW? (@1)
```

Typical Response:

```
+5.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent:LOW?

## MEASure[:SCALar]:VOLTage:MAXimum?

### Syntax

```
MEASure[:SCALar]:VOLTage:MAXimum? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement, and returns the maximum value in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the maximum voltage value on channel 1.

```
MEAS:VOLT:MAX? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent:MAX?

## MEASure[:SCALar]:VOLTage:MINimum?

### Syntax

```
MEASure[:SCALar]:VOLTage:MINimum? (@<<chanlist>>)
```

### Description

This query initiates and triggers a measurement, and returns the minimum value in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

\<NR3\> The reading is in the form +n.nnnnnnE+nn for each channel specified.

Multiple responses are separated by commas.

### Example

The following query returns the minimum voltage value on channel 1.

```
MEAS:VOLT:MIN? (@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

MEASure[:SCALar]:CURRent:MIN?

## MEASure:ARRay:CURRent[:DC]?

### Syntax

```
MEASure:ARRay:CURRent[:DC]? (@<<chanlist>>)
```

### Description

This query initiates and triggers a measurement and returns an array containing the digitized output current in amperes.

The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet:POINTs. The number of points returned is set by SENSe:SWEep:POINts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the current measured on channel 1.

```
MEAS:ARR:CURR? (@1)
```

### See Also

MEASure:ARRay:VOLTage[:DC]?

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

FORMat:BORDer FORMat[:DATA]

## MEASure:ARRay:POWer[:DC]?

### Syntax

```
MEASure:ARRay:POWer[:DC]? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement and returns an array containing the digitized output power in watts.

The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet:POINts. The number of points returned is set by SENSe:SWEep:POINts.

> **NOTE** This command only applies to models N676xA and N678xA SMU. These models have simultaneous voltage and current measurement capability.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the power measured on channel 1.

```
MEAS:ARR:POW? (@1)
```

### See Also

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

## MEASure:ARRay:VOLTage[:DC]?

### Syntax

```
MEASure:ARRay:VOLTage[:DC]? (@<chanlist>)
```

### Description

This query initiates and triggers a measurement and returns an array containing the digitized output voltage in volts.

The sampling rate is set by SENSe:SWEep:TINTerval. The position of the trigger relative to the beginning of the data buffer is determined by SENSe:SWEep:OFFSet:POINts. The number of points returned is set by SENSe:SWEep:POINts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The MEASure query starts a new measurement immediately. It is not synchronized to any trigger event.

Use the INITiate, trigger, and FETCh sequence if a synchronized measurement is necessary.

The default time interval and number of points settings yield a measurement time of 21 milliseconds per reading (1024 data points at 20.48 microsecond intervals). The default windowing function is Rectangular.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Example

The following query returns the voltage measured on channel 1.

```
MEAS:ARR:VOLT? (@1)
```

### See Also

MEASure:ARRay:CURRent[:DC]?

SENSe:SWEep:TINTerval

SENSe:SWEep:OFFset:POINts

SENSe:SWEep:POINts

FORMat:BORDer FORMat[:DATA]
