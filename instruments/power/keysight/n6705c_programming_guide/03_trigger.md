# TRIGger Subsystem Introduction

Trigger commands control the remote triggering of the instrument. They specify the trigger source for the transient and the measurement system and also generate software triggers.

The Common command \*TRG is also used to trigger the instrument.

| SCPI Command | Description |
|---|---|
| TRIGger |  |
| :ACQuire |  |
| [:IMMediate] (@chanlist) | Triggers the measurement immediately |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the current trigger level |
| :SLOPe POSitive \| NEGative, | Sets the current trigger slope |
| (@chanlist) |  |
| :SOURce \<source\>, (@chanlist) | Sets the measurement trigger source \<source\> = BUS, CURRent\<n\>,EXTernal, PIN\<n\>, TRANsient\<n\>, VOLTage\<n\> |
| :TOUTput |  |
| [:ENABle] \<Bool\>, (@chanlist) | Enables measurement triggers to be sent to a digital port pin |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the voltage trigger level |
| :SLOPe POSitive \| NEGative, | Sets the voltage trigger slope |
| (@chanlist) |  |
| :ARB:SOURce BUS \| IMMediate \| EXTernal | Sets the arbitrary waveform trigger source |
| :DLOG |  |
| [:IMMediate] | Triggers the internal data logger immediately |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the current trigger level of the data logger |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the current trigger slope of the data logger |
| :SOURce \<source\> | Sets the internal data logger trigger source \<source\> = BUS, CURRent\<n\>, EXTernal, IMMediate, VOLTage\<n\>, ARSK, OOOK |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the voltage trigger level of the data logger |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the voltage trigger slope of the data logger |
| :ELOG |  |
| [:IMMediate] (@chanlist) | Triggers the external data logger immediately |
| :SOURce \<source\>, (@chanlist) | Sets the external data logger trigger source \<source\> = BUS, EXTernal, IMMediate, PIN\<n\> |
| :HISTogram |  |
| [:IMMediate] (@chanlist) | Triggers the current histogram immediately (N6781A, N6782A, N6785A, N6786A) |
| :SOURce \<source\>, (@chanlist) | Sets the current histogram trigger source (N6781A, N6782A, N6785A, N6786A) \<source\> = BUS, EXTernal, IMMediate, PIN\<n\> |
| :TRANsient |  |
| [:IMMediate] (@chanlist) | Triggers the output immediately |
| :SOURce \<source\>, (@chanlist) | Sets the output trigger source \<source\> = BUS, EXTernal, IMMediate, PIN\<n\>, TRANsient\<n\> |

## TRIGger:ACQuire[:IMMediate]

### Syntax

```
TRIGger:ACQuire[:IMMediate] (@<chanlist>)
```

### Description

This command sends an immediate trigger to the measurement system.

When the trigger system is initiated, a measurement trigger causes the instrument to measure the output voltage or current, and store the results in a buffer.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

You must initiate the measurement trigger system before you can send any triggers.

The measured quantity, either voltage or current, must be specified by the SENSe:FUNCtion command.

When the triggered measurement has completed, the WTG-meas bit in the Status Operation Condition register is cleared.

### Example

The following command generates a measurement trigger on channels 1 and 2.

```
TRIG:ACQ (@1,2)
```

### See Also

INITiate[:IMMediate]:ACQuire

SENSe:FUNCtion:CURRent

SENSe:FUNCtion:VOLTage

\*TRG

## TRIGger:ACQuire:CURRent[:LEVel]

### Syntax

```
TRIGger:ACQuire:CURRent[:LEVel] <current>,
(@<chanlist>)
TRIGger:ACQuire:CURRent[:LEVel]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the triggered current level of the specified output channel when the measurement trigger source is set to current. Units are in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:ACQuire:SOURce current parameter.

A non-programmable hysteresis for level triggers reduces false triggering on slow signals. The hysteresis is set to 0.0005 X maximum range value.

For example, on the 10 A range, the hysteresis is approximately 5 mA.

### Return Format

\<NR3\> The query command returns the programmed trigger level in the form +n.nnnnnnE+nn for the specified output channel.

### Examples

The following command sets the triggered current level to 2 A on channel 2.

```
TRIG:ACQ:CURR 2,(@2)
```

The following query returns the programmed triggered current level.

```
TRIG:ACQ:CURR (@2)
```

Typical Response:

```
+2.000000E+00
```

### See Also

TRIGger:ACQuire:SOURce

## TRIGger:ACQuire:CURRent:SLOPe

### Syntax

```
TRIGger:ACQuire:CURRent:SLOPe <slope>, (@<chanlist>)
TRIGger:ACQuire:CURRent:SLOPe? (@<chanlist>)
```

### Description

This command sets the slope of the current signal of the specified output channel when the trigger source for the measurement is set to a current level.

POSitive Specifies a rising slope of the output signal.

NEGative Specifies a falling slope of the output signal.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slope\> | CPD | POSitive \| NEGative | POS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:ACQuire:SOURce current parameter.

### Return Format

\<CRD\> The query command returns POS or NEG.

### Examples

The following command sets the current slope to Positive on output channel 2.

```
TRIG:ACQ:CURR:SLOP POS,(@2)
```

The following query returns the current slope on output channel 2.

```
TRIG:ACQ:CURR:SLOP (@2)
```

Typical Response:

```
POS
```

### See Also

TRIGger:ACQuire:SOURce

## TRIGger:ACQuire:SOURce

### Syntax

```
TRIGger:ACQuire:SOURce <source>, (@<chanlist>)
TRIGger:ACQuire:SOURce? (@<chanlist>)
```

### Description

This command selects the trigger source for the measurement trigger system. The following trigger sources can be selected: BUS Selects a remote interface trigger command.

CURRent\<n\> Selects an output current level. \<n\> specifies the channel.

EXTernal Selects ALL connector pins that have been configured as trigger sources.

PIN\<n\> Selects a digital port pin configured as a trigger input.

\<n\> specifies the pin number.

TRANsient\<n\> Selects the transient system of an output channel as the trigger source. \<n\> specifies the channel.

VOLTage\<n\> Selects an output voltage level. \<n\> specifies the channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| CURRent\<1-4\> PIN\<1-7\> \| TRANsient\<1-4\> \| VOLTage\<1-4\> | BUS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

PIN\<n\> must be configured as trigger input before it can be used as a trigger source. See [SOURce:]DIGital:PIN\<n\>:FUNCtion and [SOURce:]DIGital:PIN\<n\>:POLarity.

You can also configure the transient system to use it as a trigger source.

See: [SOURce:]STEP:TOUTput, [SOURce:]LIST:TOUTput:BOSTep , and [SOURce:]LIST:TOUTput:EOSTep.

When specifying an output current or voltage level, you must also specify the level as well as the slope. See: TRIGger:ACQuire:CURRent[:LEVel],

TRIGger:ACQuire:CURRent:SLOPe, TRIGger:ACQuire:VOLTage[:LEVel], and TRIGger:ACQuire:VOLTage:SLOPe.

### Return Format

\<CRD\> The query command returns BUS, CURR\<n\>, PIN\<n\>, TRAN\<n\>, or VOLT\<n\>.

### Examples

The following command selects pin 1 as the measurement trigger source for channel 2.

```
TRIG:ACQ:SOUR PIN1,(@2)
```

The following query returns the measurement trigger source of channel 1.

```
TRIG:ACQ:SOUR? (@1)
```

Typical Response:

```
BUS
```

### See Also

[SOURce:]DIGital:PIN\<1-7\>:FUNCtion [SOURce:]DIGital:PIN\<1-7\>:POLarity [SOURce:]STEP:TOUTput [SOURce:]LIST:TOUTput:BOSTep [SOURce:]LIST:TOUTput:EOSTep

## TRIGger:ACQuire:TOUTput[:ENABle]

### Syntax

```
TRIGger:ACQuire:TOUTput[:ENABle] <Bool>,
(@<chanlist>)
TRIGger:ACQuire:TOUTput[:ENABle]? (@<chanlist>)
```

### Description

This command enables measurement triggers to be sent to any digital port pin that has been configured as a trigger output. The enabled state is ON (1); the disabled state is OFF (0).

When a measurement is initiated, the MEAS_active status bit is set true, allowing measurement triggers to be sent. Measurement triggers can continue to be sent until the measurement completes or is aborted and the MEAS_active status is set false.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The digital port pin must be configured as a trigger output before it can source a trigger signal. See [SOURce:]DIGital:PIN\<n\>:FUNCtion and [SOURce:]DIGital:PIN\<n\>:POLarity.

When the measurement trigger source is a transient trigger or output voltage/current level, ANY measurement trigger that occurs is sent to the configured trigger output pin. You must make sure that no trigger occurs other than the trigger of interest. TRIGger:ACQuire:TOUTput is disabled when the acquisition is complete.

If the measurement trigger source generates multiple trigger events, each trigger event will generate a measurement trigger signal at the configured trigger output pins. In this case, it may not be possible to identify which trigger event was the one that actually triggered the measurement.

### Return Format

\<NR1\> The query command returns 0 if the command is disabled, and 1 if the command is enabled.

### Examples

The following command enables sending measurement triggers to digital output pins on channel 2.

```
TRIG:ACQ:TOUT ON,(@2)
```

The following query returns the state of TRIG:ACQ:TOUT on output channel 2.

```
TRIG:ACQ:TOUT? (@2)
```

Typical Response:

```
1
```

### See Also

TRIGger:ACQuire:SOURce

## TRIGger:ACQuire:VOLTage[:LEVel]

### Syntax

```
TRIGger:ACQuire:VOLTage[:LEVel] <voltage>,
(@<chanlist>)
TRIGger:ACQuire:VOLTage[:LEVel]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the triggered voltage level of the specified output channel when the measurement trigger source is set to voltage. Units are in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:ACQuire:SOURce voltage parameter.

A non-programmable hysteresis for level triggers reduces false triggering on slow signals. The hysteresis is set to 0.0005 X maximum range value.

For example, on the 50 V range, the hysteresis is approximately 25 mV

### Return Format

\<NR3\> The query command returns the programmed trigger level in the form +n.nnnnnnE+nn for the specified output channel.

### Examples

The following command sets the triggered voltage level to 5 V on channel 2.

```
TRIG:ACQ:VOLT 5,(@2)
```

The following query returns the programmed triggered voltage level.

```
TRIG:ACQ:VOLT (@2)
```

Typical Response:

```
+5.000000E+00
```

### See Also

TRIGger:ACQuire:SOURce

## TRIGger:ACQuire:VOLTage:SLOPe

### Syntax

```
TRIGger:ACQuire:VOLTage:SLOPe <slope>, (@<chanlist>)
TRIGger:ACQuire:VOLTage:SLOPe? (@<chanlist>)
```

### Description

This command sets the slope of the voltage signal of the specified output channel when the trigger source for the measurement is set to a voltage level.

POSitive Specifies a rising slope of the output signal.

NEGative Specifies a falling slope of the output signal.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slope\> | CPD | POSitive \| NEGative | POS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:ACQuire:SOURce voltage parameter.

### Return Format

\<CRD\> The query command returns POS or NEG.

### Examples

The following command sets the voltage slope to Positive on output channel 2.

```
TRIG:ACQ:VOLT:SLOP POS,(@2)
```

The following query returns the voltage slope on output channel 2.

```
TRIG:ACQ:VOLT:SLOP (@2)
```

Typical Response:

```
POS
```

### See Also

TRIGger:ACQuire:SOURce

## TRIGger:ARB:SOURce

### Syntax

```
TRIGger:ARB:SOURce <source>
TRIGger:ARB:SOURce?
```

### Description

This command selects the trigger source for the arbitrary waveforms. The following trigger sources can be selected: BUS Selects a remote interface trigger command.

EXTernal Selects the rear panel Trigger In BNC connector.

IMMediate Triggers the arbitrary waveform immediately.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| IMMediate \| EXTernal | IMM |

### Return Format

\<CRD\> The query command returns BUS, EXT, or IMM.

### Examples

The following command selects the Trigger IN connector as the arbitrary waveform trigger source.

```
TRIG:ARB:SOUR EXT
```

The following query returns the arbitrary waveform trigger source.

```
TRIG:ARB:SOUR?
```

Typical Response:

```
BUS
```

## TRIGger:DLOG[:IMMediate]

### Syntax

```
TRIGger:DLOG[:IMMediate]
```

### Description

This command sends an immediate trigger signal to the data logger. This will trigger the data log regardless of the selected trigger source.

### Remarks

You must initiate (run) the data logger before you trigger it.

### Example

The following command triggers the data logger.

```
TRIG:DLOG
```

### See Also

INITiate[:IMMediate]:DLOG

SENSe:DLOG:FUNCtion:CURRent

SENSe:DLOG:FUNCtion:VOLTage

\*TRG

## TRIGger:DLOG:CURRent[:LEVel]

### Syntax

```
TRIGger:DLOG:CURRent[:LEVel] <current>, (@<chanlist>)
TRIGger:DLOG:CURRent[:LEVel]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the trigger level of the specified output channel for a current-level triggered data log. Units are in amperes.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:DLOG:SOURce current parameter.

### Return Format

\<NR3\> The query command returns the programmed trigger level in the form +n.nnnnnnE+nn for the specified output channel.

### Examples

The following command sets the DLOG trigger current-level to 2 A on channel 2.

```
TRIG:DLOG:CURR 2,(@2)
```

The following query returns the programmed DLOG trigger current-level.

```
TRIG:DLOG:CURR (@2)
```

Typical Response:

```
+2.000000E+00
```

### See Also

TRIGger:DLOG:SOURce

## TRIGger:DLOG:CURRent:SLOPe

### Syntax

```
TRIGger:DLOG:CURRent:SLOPe <slope>, (@<chanlist>)
TRIGger:DLOG:CURRent:SLOPe? (@<chanlist>)
```

### Description

This command sets the slope polarity of a current-level trigger of the specified output channel for the data logger.

POSitive Specifies a rising slope of the output signal.

NEGative Specifies a falling slope of the output signal.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slope\> | CPD | POSitive \| NEGative | POS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:DLOG:SOURce current parameter.

### Return Format

\<CRD\> The query command returns POS or NEG.

### Examples

The following command sets a positive current-level trigger slope on output channel 2.

```
TRIG:DLOG:CURR:SLOP POS,(@2)
```

The following query returns the slope polarity of the current-level trigger on output channel 2.

```
TRIG:DLOG:CURR:SLOP (@2)
```

Typical Response:

```
POS
```

### See Also

TRIGger:DLOG:SOURce

## TRIGger:DLOG:SOURce

### Syntax

```
TRIGger:DLOG:SOURce <source>
TRIGger:DLOG:SOURce?
```

### Description

This command selects the trigger source for the data logger. The following trigger sources can be selected: BUS Selects a remote interface trigger command.

CURRent\<n\> Selects the measured current-level of a specific channel. \<n\> specifies the channel.

EXTernal Selects the rear panel Trigger In BNC connector and any connector pins configured as trigger sources.

IMMediate Sets the trigger source true, so that as soon as the data logger is INITiated it will send the trigger immediately.

VOLTage\<n\> Selects the measured voltage-level of a specific channel. \<n\> specifies the channel.

ARSKey Selects the Arb Run/Stop key.

OOOKey Selects the Output On/Off keys and the All Outputs On/Off keys.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| IMMediate \| EXTernal \| VOLTage\<1-4\> \| CURRent\<1-4\> \| ARSKey \| OOOKey | IMM |

### Remarks

If you have selected a voltage or current level as the trigger source, you must also program the voltage or current level and the slope polarity.

See: TRIGger:DLOG:CURRent, TRIGger:DLOG:CURRent:SLOPe,

TRIGger:DLOG:VOLTage, TRIGger:DLOG:VOLTage:SLOPe

### Return Format

\<CRD\> The query command returns IMM, EXT, BUS, VOLT\<n\>, CURR\<n\>, ARSK, or OOOK.

### Examples

The following command selects the Output On/Off key as the data log trigger source.

```
TRIG:DLOG:SOUR OOOK
```

The following query returns the data log trigger source.

```
TRIG:DLOG:SOUR?
```

Typical Response:

```
VOLT1
```

### See Also

TRIGger:DLOG:CURRent

TRIGger:DLOG:CURRent:SLOPe

TRIGger:DLOG:VOLTage

TRIGger:DLOG:VOLTage:SLOPe

## TRIGger:DLOG:VOLTage[:LEVel]

### Syntax

```
TRIGger:DLOG:VOLTage[:LEVel] <voltage>, (@<chanlist>)
TRIGger:DLOG:VOLTage[:LEVel]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the trigger level of the specified output channel for a voltage-level triggered data log. Units are in volts.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN\| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:DLOG:SOURce voltage parameter.

### Return Format

\<NR3\> The query command returns the programmed trigger level in the form +n.nnnnnnE+nn for the specified output channel.

### Examples

The following command sets the DLOG trigger voltage-level to 5 V on channel 2.

```
TRIG:DLOG:VOLT 5,(@2)
```

The following query returns the programmed DLOG trigger voltage-level.

```
TRIG:DLOG:VOLT (@2)
```

Typical Response:

```
+5.000000E+00
```

### See Also

TRIGger:DLOG:SOURce

## TRIGger:DLOG:VOLTage:SLOPe

### Syntax

```
TRIGger:DLOG:VOLTage:SLOPe <slope>, (@<chanlist>)
TRIGger:DLOG:VOLTage:SLOPe? (@<chanlist>)
```

### Description

This command sets the slope polarity of a voltage-level trigger of the specified output channel for the data logger.

POSitive Specifies a rising slope of the output signal.

NEGative Specifies a falling slope of the output signal.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slope\> | CPD | POSitive \| NEGative | POS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The output channel specified with this command must match the output channel specified by the TRIGger:DLOG:SOURce voltage parameter.

### Return Format

\<CRD\> The query command returns POS or NEG.

### Examples

The following command sets a positive voltage-level trigger slope on output channel 2.

```
TRIG:DLOG:VOLT:SLOP POS,(@2)
```

The following query returns the slope polarity of the voltage-level trigger on output channel 2.

```
TRIG:DLOG:VOLT:SLOP (@2)
```

Typical Response:

```
POS
```

### See Also

TRIGger:DLOG:SOURce

## TRIGger:ELOG[:IMMediate]

### Syntax

```
TRIGger:ELOG[:IMMediate] (@<chanlist>)
```

### Description

This command sends an immediate trigger signal to the external data logger. This will trigger the external data log regardless of the selected trigger source.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

You must initiate (run) the external data logger before you trigger it.

### Example

The following command triggers the external data logger on channel 1.

```
TRIG:ELOG @1
```

### See Also

INITiate[:IMMediate]:ELOG

SENSe:ELOG:FUNCtion:CURRent

SENSe:ELOG:FUNCtion:VOLTage

\*TRG

## TRIGger:ELOG:SOURce

### Syntax

```
source
TRIGger:ELOG:SOURce < >, (@<chanlist>)
TRIGger:ELOG:SOURce? (@<chanlist>)
```

### Description

This command selects the trigger source for the external data logger. The following trigger sources can be selected: BUS Selects a remote interface trigger command.

EXTernal Selects the rear panel Trigger In BNC connector and any digital port pin that has been configured as a trigger input.

IMMediate Sets the trigger source true, so that as soon as the external data logger is INITiated it will send the trigger immediately.

PIN\<n\> Selects a digital port pin configured as a trigger input.

\<n\> specifies the pin number.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| EXTernal \| IMMediate \| PIN\<1-7\> | BUS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

PIN\<n\> must be configured as trigger input before it can be used as a trigger source. See [SOURce:]DIGital:PIN\<n\>:FUNCtion and [SOURce:]DIGital:PIN\<n\>:POLarity.

### Return Format

\<CRD\> The query command returns IMM, EXT, BUS, or PIN\<n\>.

### Examples

The following command selects BUS as the external data log trigger source.

```
TRIG:ELOG:SOUR BUS,@1
```

The following query returns the data log trigger source.

```
TRIG:ELOG:SOUR? @1
```

Typical Response:

```
BUS
```

## TRIGger:HISTogram[:IMMediate]

### Syntax

```
TRIGger:HISTogram[:IMMediate] (@<chanlist>)
```

### Description

This command sends an immediate trigger signal to the histogram current measurement data logger. This will trigger the histogram measurement regardless of the selected trigger source.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

You must initiate (run) the histogram measurement data logger before you trigger it.

### Example

The following command triggers the histogram measurement on channel 1.

```
TRIG:HIST @1
```

### See Also

INITiate[:IMMediate]:HISTogram

SENSe:HISTogam:FUNCtion:CURRent

\*TRG

## TRIGger:HISTogram:SOURce

### Syntax

```
TRIGger:HISTogram:SOURce <source>, (@<chanlist>)
TRIGger:HISTogram:SOURce? (@<chanlist>)
```

### Description

This command selects the trigger source for the histogram measurement data logger. The following trigger sources can be selected: BUS Selects a remote interface trigger command.

EXTernal Selects the rear panel Trigger In BNC connector and any digital port pin that has been configured as a trigger input.

IMMediate Sets the trigger source true, so that as soon as the histogram measurement data logger is INITiated it will send the trigger immediately.

PIN\<n\> Selects a digital port pin configured as a trigger input. \<n\> specifies the pin number.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| EXTernal \| IMMediate \| PIN\<1-7\> | BUS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

PIN\<n\> must be configured as trigger input before it can be used as a trigger source. See [SOURce:]DIGital:PIN\<n\>:FUNCtion and [SOURce:]DIGital:PIN\<n\>:POLarity.

### Return Format

\<CRD\> The query command returns IMM, EXT, BUS, or PIN\<n\>.

### Examples

The following command selects BUS as the histogram measurement trigger source.

```
TRIG:HIST:SOUR BUS,@1
```

The following query returns the histogram measurement trigger source.

```
TRIG:HIST:SOUR? @1
```

Typical Response:

```
BUS
```

## TRIGger:TRANsient[:IMMediate]

### Syntax

```
TRIGger:TRANsient[:IMMediate] (@<chanlist>)
```

### Description

This command generates an immediate transient trigger regardless of the selected trigger source. Output triggers affect the following functions: voltage, current, and current limit.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

You must initiate the output trigger system before you can send any triggers.

When sent, the transient trigger will initiate an output change as specified by the CURRent:TRIGgered or VOLTage:TRIGgered commands.

When the transient trigger sequence has completed, the WTG-tran bit in the Status Operation Condition register is cleared.

### Example

The following command generates an output trigger on channels 1 and 2.

```
TRIG:TRAN (@1,2)
```

### See Also

INITiate[:IMMediate]:TRANsient [SOURce:]CURRent[:LEVel]:TRIGgered [SOURce:]VOLTage[:LEVel]:TRIGgered [SOURce:]CURRent:MODE [SOURce:]VOLTage:MODE

\*TRG

## TRIGger:TRANsient:SOURce

### Syntax

```
source
TRIGger:TRANsient:SOURce < >, (@<chanlist>)
TRIGger:TRANsient:SOURce? (@<chanlist>)
```

### Description

This command selects the trigger source for the output trigger system.

The following trigger sources can be selected: BUS Selects a remote interface trigger command.

EXTernal Selects ALL connector pins that have been configured as trigger sources.

IMMediate Sets the trigger source true, so that as soon as the data logger is INITiated it will send the trigger immediately.

PIN\<n\> Selects a digital port pin configured as a trigger input. \<n\> specifies the pin number.

TRANsient\<n\> Selects the transient system of an output channel as the trigger source. \<n\> specifies the channel.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<source\> | CPD | BUS \| EXTernal \| IMMediate \| PIN\<1-7\> \| TRANsient\<1-4\> | BUS |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

PIN\<n\> must be configured as trigger input before it can be used as a trigger source. See [SOURce:]DIGital:PIN\<n\>:FUNCtion and [SOURce:]DIGital:PIN\<n\>:POLarity.

You can also configure the transient system to use it as a trigger source.

See: [SOURce:]STEP:TOUTput, [SOURce:]LIST:TOUTput:BOSTep, and [SOURce:]LIST:TOUTput:EOSTep.

### Return Format

\<CRD\> The query command returns BUS, PIN\<n\>, or TRAN\<n\>.

### Examples

The following command selects pin 1 as the output trigger source for channel 2.

```
TRIG:TRAN:SOUR PIN1,(@2)
```

The following query returns the output trigger source of channel 1.

```
TRIG:TRAN:SOUR? (@1)
```

Typical Response:

```
BUS
```

### See Also

[SOURce:]DIGital:PIN\<1-7\>:FUNCtion [SOURce:]DIGital:PIN\<1-7\>:POLarity [SOURce:]STEP:TOUTput [SOURce:]LIST:TOUTput:BOSTep [SOURce:]LIST:TOUTput:EOSTep
