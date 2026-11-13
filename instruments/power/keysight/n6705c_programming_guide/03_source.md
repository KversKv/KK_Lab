# SOURce Subsystem Introduction

The Source subsystem programs the current, digital, list, step, and voltage functions.

| SCPI Command | Description |
|---|---|
| [SOURce:]ARB |  |
| :COUNt \<NRf+\> \| INFinity, (@chanlist) | Sets the Arb repeat count |
| :CURRent \| :VOLTage | Specifies current or voltage Arbs |
| :CDWell |  |
| [:LEVel] \< NRf+\> {,\<NRf\>}, (@chanlist) | Sets the list of the constant dwell Arb |
| :DWELl \< NRf+\>, (@chanlist) | Sets the dwell time for the constant dwell Arb |
| :POINts? (@\<chanlist\>) | Returns the number of constant-dwell Arb points |
| :CONVert (@chanlist) | Converts the selected Arb to a user-defined list |
| :EXPonential |  |
| :END |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the end level of the exponential Arb |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the initial level of the exponential Arb |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |
| :TCONstant \< NRf+\>, (@chanlist) | Sets the time constant of the exponential Arb |
| :TIMe \< NRf+\>, (@chanlist) | Sets the time of the exponential Arb |
| :PULSe |  |
| :END |  |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the end time |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the initial level of the pulse |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |
| :TOP |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the top level of the pulse |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the pulse |
| :RAMP |  |
| :END |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the end level of the ramp |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the end time |
| :RTIMe \< NRf+\>, (@chanlist) | Sets the rise time of the ramp |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the initial level of the ramp |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |
| :SINusoid |  |
| :AMPLitude \< NRf+\>, (@chanlist) | Sets the amplitude of the sine wave |
| :FREQuency \< NRf+\>, (@chanlist) | Sets the frequency of the sine wave |
| :OFFSet \< NRf+\>, (@chanlist) | Sets the DC offset of the sine wave |
| :STAircase |  |
| :END |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the end level of the staircase |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the end time |
| :NSTeps \< NRf+\>, (@chanlist) | Sets the number of steps in the staircase |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the initial level of the staircase |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |
| :TIMe \<NRf+\>, (@chanlist) | Sets the length of the staircase |
| :STEP |  |
| :END |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the end level of the step |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlistl) | Sets the initial level of the step |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |

| SCPI Command | Description |
|---|---|
| [SOURce:]ARB (continued) |  |
| :TRAPezoid |  |
| :END |  |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the end time |
| :FTIMe \< NRf+\>, (@chanlist) | Sets the length of the fall time |
| :RTIMe \< NRf+\>, (@chanlist) | Sets the length of the rise time |
| :STARt |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the initial level of the trapezoid |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the start time or delay |
| :TOP |  |
| [:LEVel] \< NRf+\>, (@chanlist) | Sets the top level of the trapezoid |
| :TIMe \< NRf+\>, (@chanlist) | Sets the length of the top of the trapezoid |
| :UDEFined |  |
| :BOSTep |  |
| [:DATA] \<Bool\> {,\<Bool\>}, (@chanlist) | Generate triggers at the Beginning Of STep |
| :POINts? (@chanlist) | Returns the number of BOST points |
| :DWELl \<NRf\> {,\<NRf\>}, (@chanlist) | Sets the user-defined dwell values |
| :POINts? (@chanlist) | Returns the number of dwell points |
| :LEVel \<NRf\> {,\<NRf\>}, (@chanlist) | Sets the user-defined level values |
| :POINts? (@chanlist) | Returns the number of points |
| :FUNCtion \<function\>, (@chanlist) | Selects the Arb function (for backward compatibility) |
| :SHAPe \<function\>, (@chanlist) | Selects the Arb function (replaces ARB:FUNCtion) |
| :TYPE CURRent \| VOLTage, (@chanlist) | Selects the Arb type (replaces ARB:FUNCtion) |
| :SEQuence |  |
| :COUNt \<NRf+\> \| INFinity, (@chanlist) | Sets the number of times the sequence is repeated |
| :LENgth? (@chanlist) | Returns the number of steps in the sequence |
| :QUALity? (@chanlist) | Returns the quality of the waveforms in the sequence |
| :RESet (@chanlist) | Resets the sequence to its power-on default setting |
| :STEP |  |
| :COUNt \<NRf+\> \| INFinity, \<step#\>, (@chanlist) | Sets the number of times the sequence step is repeated |
| :CURRent \<ARB_function\>, \<step#\>, (@chanlist) | Programs the waveform steps within a current sequence |
| :FUNCtion |  |
| :SHAPe \<function\>, \<step#\>, (@chanlist) | Creates a new sequence step |
| :PACing DWELl \| TRIGger, \<step#\>, (@chanlist) | Specifies the type of pacing for the step |
| :VOLTage \<ARB_function\>, \<step#\>, (@chanlist) | Programs the waveform steps within a voltage sequence |
| :TERMinate |  |
| :LAST \<Bool\>, (@chanlist) | Sets the sequence termination mode |
| :TERMinate |  |
| :LAST \<Bool\>, (@chanlist) | Sets the Arb termination mode |
| [SOURce:]CURRent |  |
| [:LEVel] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the output current |
| :TRIGgered [:AMPLitude] \<NRf+\>, (@chanlist) | Sets the triggered output current |
| :LIMit |  |
| [:POSitive] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the positive current limit (only on N678xA SMU, N6783A) |
| :COUPle \<Bool\>, (@chanlist) | Sets the current limit tracking state (only on N678xA SMU) |
| :NEGative |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the negative current limit (only on N678xA SMU, N6783A-BAT) |
| :MODE FIXed \| STEP \| LIST \| ARB, (@chanlist) | Sets the current trigger mode |
| :PROTection |  |
| :DELay |  |
| [:TIME] \<NRf+\> (@chanlist) | Sets the over-current protection programming delay |
| :STARt SCHange \| CCTRans, (@chanlist) | Sets the over-current protection programming mode |
| :STATe \<Bool\>, (@chanlist) | Enables/disables over-current protection on the selected output |
| :RANGe \<NRf+\>, (@chanlist) | Sets the output current range |
| :SLEW |  |
| [:IMMediate] \<NRf+\> \| INFinity, (@chanlist) | Sets the output current slew rate (N678xA SMU) |
| MAXimum \<Bool\>, (@chanlist) | Enables/disables the maximum slew rate override (N678xA SMU) |

| SCPI Command | Description |
|---|---|
| [SOURce:]DIGital |  |
| :INPut |  |
| :DATA? | Reads the state of the digital port pins |
| :OUTPut |  |
| :DATA \<NRf\> | Sets the digital port |
| :PIN\<1-7\> |  |
| :FUNCtion \<function\> | Sets the selected pin’s function \<function\>= DIO, DINPut, TOUTput, TINPput, FAULt, INHibit, ONCouple, OFFCouple |
| :POLarity POSitive \| NEGative | Sets the selected pin’s polarity |
| :TOUTput |  |
| :BUS [:ENABle] \<Bool\> | Enables/disables BUS-generated triggers on digital pins |
| [SOURce:]EMULation \<type\>, (@chanlist) | Specifies the emulation mode on N678xA \<type\> = PS4Q, PS2Q, PS1Q, BATTery, CHARger, CCLoad, CVLoad, VMETer, AMETer |
| [SOURce:]FUNCtion CURRent \| VOLTage, (@chanlist) | Specifies current priority or voltage priority mode (N678xA SMU) |
| [SOURce:]LIST |  |
| :COUNt \<NRf+\> \| INFinity, (@chanlist) | Sets the list repeat count |
| :CURRent |  |
| [:LEVel] \<NRf\> {,\<NRf\>}, (@chanlist) | Sets the current list |
| :POINts? (@chanlist) | Returns the number of current list points |
| :DWELl \<NRf\> {,\<NRf\>}, (@chanlist) | Sets the list of dwell times |
| :POINts? (@chanlist) | Returns the number of dwell list points |
| :STEP ONCE \| AUTO, (@chanlist) | Specifies how the list responds to triggers |
| :TERMinate |  |
| :LAST \<Bool\>, (@chanlist) | Sets the list termination mode |
| :TOUTput |  |
| :BOSTep |  |
| [:DATA] \<Bool\> {,\<Bool\>}, (@chanlist) | Generate triggers at the Beginning Of STep |
| :POINts? (@chanlist) | Returns the number of BOST list points |
| :EOSTep |  |
| [:DATA] \<Bool\> {,\<Bool\>}, (@chanlist) | Generate triggers at the End Of STep |
| :POINts? (@chanlist) | Returns the number of EOST list points |
| :VOLTage |  |
| [:LEVel] \<NRf\> {,\<NRf\>}, (@chanlist) | Sets the voltage list |
| :POINts? (@chanlist) | Returns the number of voltage list points |
| [SOURce:]POWer |  |
| :LIMit \<NRf+\>, (@chanlist) | Sets the power limit on output channels |
| [SOURce:]RESistance |  |
| [:LEVel] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the output resistance (only on N6781A, N6785A) |
| :STATe \<Bool\>, (@chanlist) | Enables/disables output resistance programming (N6781A, N6785A) |
| [SOURce:]STEP |  |
| :TOUTput \<Bool\>, (@chanlist) | Generate a trigger output on the voltage or current step |
| [SOURce:]VOLTage |  |
| [:LEVel] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the output voltage |
| :TRIGgered [:AMPLitude] \<NRf+\>, (@chanlist) | Sets the triggered output voltage |
| :BWIDth DEFault \| FAST1 \| FAST2 \| FAST3, (@chanlist) | Sets the voltage bandwidth (only on N678xA SMU) |
| :LIMit |  |
| [:POSitive] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the positive voltage limit (only on N678xA SMU) |
| :COUPle \<Bool\>, (@chanlist) | Sets the voltage limit tracking state (only on N6784A) |
| :NEGative |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the negative voltage limit (only on N6784A) |
| :MODE FIXed \| STEP \| LIST \| ARB, (@chanlist) | Sets the voltage trigger mode |

| SCPI Command | Description |
|---|---|
| [SOURce:]VOLTage (continued) |  |
| :PROTection |  |
| [:LEVel] \<NRf+\>, (@chanlist) | Sets the over-voltage protection level (not on N678xA SMU) |
| :DELay[:TIME] \<NRf+\>, (@chanlist) | Sets the over-voltage protection delay (only on N6783A) |
| :REMote |  |
| [:POSitive][:LEVel] \<NRf+\>, (@chanlist) | Sets the positive remote OV protection level (only on N678xA SMU) |
| :NEGative[:LEVel] \<NRf+\>, (@chanlist) | Sets the negative remote OV protection level (only on N6784A) |
| :RANGe \<NRf+\>, (@chanlist) | Sets the output voltage range |
| :SENSe |  |
| :SOURce INTernal \| EXTernal, (@chanlist) | Sets the remote sense relays |
| :SLEW |  |
| [:IMMediate] \<NRf+\> \| INFinity, (@chanlist) | Sets the output voltage slew rate |
| MAXimum \<Bool\>, (@chanlist) | Enables/disables the maximum slew rate override |

## ARB Diagrams

Voltage ARB Current ARB

Step

Ramp

Staircase

Sinusoid

Pulse

Trapezoid

Exponential

## [SOURce:]ARB:COUNt

### Syntax

```
[SOURce:]ARB:COUNt <count>|INFinity, (@<chanlist>)
[SOURce:]ARB:COUNt? [MIN|MAX|INFinity,] (@<chanlist>)
```

### Description

This command sets the number of times that the arbitrary waveform is repeated. The repeat count range is 1 through \>16 million. For constant-dwell Arbs only, the maximum count is limited to 256.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<count\> | NRf+ | 1 - 16,777,216 \| MIN \| MAX \| INFinity | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Use the INFinity parameter to repeat the arbitrary waveform continuously.

If MAX, or a value greater than 16,777,216 is programmed, the Arb will also repeat continuously.

Use ABORt:TRANsient to stop the Arb at any time. When the Arb is aborted, the output returns to the settings that were in effect before the Arb started.

### Return Format

\<NR3\> The query command returns the repeat count for each channel specified.

Multiple responses are separated by commas. If a repeat count of 9.9E37 is returned, it means that the Arb is set to repeat continuously.

### Examples

The following command sets the repeat count to 10 on channel 1.

```
ARB:COUN 10,(@1)
```

The following query returns the repeat count of channel 1.

```
ARB:COUN? (@1)
```

Typical Response:

```
+10
```

## [SOURce:]ARB:CURRent:CDWell[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:CDWell[:LEVel]
<current>{,<current>}, (@<chanlist>)
[SOURce:]ARB:CURRent:CDWell[:LEVel]? (@<chanlist>)
```

### Description

This command specifies the level of each point of a constant-dwell ARB.

Current and voltage CD ARBs share settings, so setting the current CD ARB resets the voltage CD ARB level to its default value and vice-versa. A comma-delimited list of up to 65,535 points may be programmed.

For better performance, the list of current points can be sent as a definite length binary block instead of an ASCII list.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf | 0 – maximum | 1 point set to the |

or The maximum value is dependent minimum \<block\> on the current rating of the power programmable module. value \<chanlist\> Numeric One or more channels. Required (@2) - channel 2 parameter (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Examples

The following command programs a constant-dwell current ARB. The ARB contains 5 points and is on channel 1.

```
ARB:CURR:CDW 5,4,3,2,1,(@1)
```

The following query returns the constant-dwell current settings of channel 1.

```
ARB:CURR:CDW? (@1)
```

### See Also

[SOURce:]ARB:CURRent:CDWell:DWELl

FORMat:BORDer FORMat[:DATA]

## [SOURce:]ARB:CURRent:CDWell:DWELl

### Syntax

```
[SOURce:]ARB:CURRent:CDWell:DWELl <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:CDWell:DWELl? (@<chanlist>)
```

### Description

This command specifies the dwell time for each point of a constant-dwell ARB. Current and voltage CD ARBs share settings, so setting this parameter for a current CD ARB also changes the voltage dwell value and vice versa. Programmed values can range from 10.24 microseconds to 0.30 seconds. Values are rounded to the nearest 10.24-microsecond increment.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf | 0.00001024 - 0.30 | 0.001 seconds |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The maximum repeat count for CD ARBs is 256. See [SOURce:]ARB:COUNt.

### Return Format

\<NR3\> The query command returns the programmed dwell time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs constant-dwell time of 0.2 seconds on channel 1.

```
ARB:CURR:CDW:DWEL 0.2,(@1)
```

The following query returns the constant-dwell time of channel 1.

```
ARB:CURR:CDW:DWEL? (@1)
```

Typical Response:

```
+1.000000E-03
```

### See Also

[SOURce:]ARB:CURRent:CDWell[:LEVel]

## [SOURce:]ARB:CURRent:CDWell:POINts?

### Syntax

```
[SOURce:]ARB:CURRent:CDWell:POINts? (@<chanlist>)
```

### Description

This query returns the number of current points in a constant-dwell ARB.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> Returns the number of points in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following query returns the number of current points of channel 1.

```
ARB:CURR:CDW:POIN? (@1)
```

Typical Response:

```
+4.376500E+04
```

### See Also

[SOURce:]ARB:VOLTage:CDWell:POINts?

## [SOURce:]ARB:CURRent:CONVert

### Syntax

```
[SOURce:]ARB:CURRent:CONVert (@<chanlist>)
```

### Description

This command converts the specified arbitrary waveform to a list of points in the user-defined current waveform format. This makes it possible to modify/edit one of the "standard" arbitrary waveforms. The command performs the same function as the "Edit Points" button on the front panel ARB Properties dialog windows.

To use this command you must first specify an ARB shape and type using the [SOURce:]ARB:FUNCtion:SHAPe and the [SOURce:]ARB:FUNCtion:TYPE commands.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

If the ARB function of the specified channel is already set to a user-defined current waveform, the command is ignored and the conversion is not performed.

If the ARB function of the specified channel is set to "NONE", the command is ignored and the conversion is not performed.

### Example

The following command converts the ARB previously specified on channel 1.

```
ARB:CURR:CONV (@1)
```

### See Also

[SOURce:]ARB:FUNCtion:SHAPe [SOURce:]ARB:FUNCtion:TYPE

## [SOURce:]ARB:CURRent:EXPonential:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:END[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:EXPonential:END[:LEVel]
<current>, (@<chanlist>)
[SOURce:]ARB:CURRent:EXPonential:END[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:END
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:END
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end level current (after the exponential waveform ends) in amperes. Referenced to I in the Exponential diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 – maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end level current for the exponential waveform on channel 1.

```
ARB:CURR:EXP:END 1,(@1)
ARB:SEQ:STEP:CURR:EXP:END 1, 1,(@1)
```

The following query returns the end level current of channel 1.

```
ARB:CURR:EXP:END? (@1)
ARB:SEQ:STEP:CURR:EXP:END? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:EXPonential:STARt[:LEVel]

## [SOURce:]ARB:CURRent:EXPonential:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:EXPonential:STARt[:LEVel]
<current>, (@<chanlist>)
[SOURce:]ARB:CURRent:EXPonential:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt[
:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt[
:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial current (before the exponential waveform starts) in amperes. Referenced to I in the Exponential diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 – maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn . Multiple responses are separated by commas.

```
1
```

### Examples

The following command programs an start level current for the exponential waveform on channel 1.

```
ARB:CURR:EXP:STAR 1,(@1)
ARB:SEQ:STEP:CURR:EXP:STAR 1, 1,(@1)
```

The following query returns the start level current of channel 1.

```
ARB:CURR:EXP:STAR? (@1)
ARB:SEQ:STEP:CURR:EXP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:EXPonential:STARt:TIMe [SOURce:]ARB:CURRent:EXPonential:END[:LEVel]

## [SOURce:]ARB:CURRent:EXPonential:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:EXPonential:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:EXPonential:STARt:TIMe?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt:
TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt:
TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the exponential waveform occurs. Referenced to t in the 0 Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the exponential waveform on channel 1.

```
ARB:CURR:EXP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:EXP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:EXP:STAR:TIM? (@1)
ARB:SEQ:STEP: CURR:EXP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:EXPonential:STARt[:LEVel] [SOURce:]ARB:CURRent:EXPonential:TIMe

## [SOURce:]ARB:CURRent:EXPonential:TCONstant

## [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TCONstant

### Syntax

```
[SOURce:]ARB:CURRent:EXPonential:TCONstant
<constant>, (@<chanlist>)
[SOURce:]ARB:CURRent:EXPonential:TCONstant?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential
:TCONstant <constant>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential
:TCONstant? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time constant of the curve. Referenced to t c in the Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<constant\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the time constant in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time constant of 1 for channel 1.

```
ARB:CURR:EXP:TCON 1,(@1)
ARB:SEQ:STEP:CURR:EXP:TCON 1, 1,(@1)
```

The following query returns the time constant on channel 1.

```
ARB:CURR:EXP:TCON? (@1)
ARB:SEQ:STEP:CURR:EXP:TCON? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

## [SOURce:]ARB:CURRent:EXPonential:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:EXPonential:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:EXPonential:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the total time for the current to go from the starting level to the ending level in seconds. Referenced to t in the 1 Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time of 10 seconds for the exponential waveform on channel 1.

```
ARB:CURR:EXP:TIM 10,(@1)
ARB:SEQ:STEP:CURR:EXP:TIM 10, 1,(@1)
```

The following query returns the time setting of channel 1.

```
ARB:CURR:EXP:TIM? (@1)
ARB:SEQ:STEP:CURR:EXP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:EXPonential:STARt:TIMe

## [SOURce:]ARB:CURRent:PULSe:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:END:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:PULSe:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:PULSe:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:END:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:END:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the pulse completes, that the start-level current persists. Referenced to t in the Pulse diagram.

2

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the pulse on channel 1.

```
ARB:CURR:PULS:END:TIM 1,(@1)
ARB:SEQ:STEP:CURR:PULS:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:CURR:PULS:END:TIM? (@1)
ARB:SEQ:STEP:CURR:PULS:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:PULSe:STARt[:LEVel] [SOURce:]ARB:CURRent:PULSe:STARt:TIMe [SOURce:]ARB:CURRent:PULSe:TOP:TIMe

## [SOURce:]ARB:CURRent:PULSe:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:PULSe:STARt[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:PULSe:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the current before and after the pulse occurs in amperes. Referenced to I in the Pulse diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a starting and ending current level for the pulse on channel 1.

```
ARB:CURR:PULS:STAR 1,(@1)
ARB:SEQ:STEP:CURR:PULS:STAR 1, 1,(@1)
```

The following query returns the starting and ending current setting of channel 1.

```
ARB:CURR:PULS:STAR? (@1)
ARB:SEQ:STEP:CURR:PULS:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:PULSe:STARt:TIMe [SOURce:]ARB:CURRent:PULse:TOP[:LEVel]

## [SOURce:]ARB:CURRent:PULSe:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:PULSe:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:PULSe:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the pulse occurs. Referenced to t in the Pulse diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the pulse on channel 1.

```
ARB:CURR:PULS:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:PULS:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:PULS:STAR:TIM? (@1)
ARB:SEQ:STEP:CURR:PULS:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:PULSe:STARt[:LEVel] [SOURce:]ARB:CURRent:PULSe:END:TIMe [SOURce:]ARB:CURRent:PULSe:TOP:TIMe

## [SOURce:]ARB:CURRent:PULSe:TOP[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:PULSe:TOP[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:PULSe:TOP[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP[:LEVel]
<current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP[:LEVel]?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the top level current of the pulse in amperes.

Referenced to I in the Pulse diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level current for the pulse on channel 1.

```
ARB:CURR:PULS:TOP 2,(@1)
ARB:SEQ:STEP:CURR:PULS:TOP 2, 1,(@1)
```

The following query returns the top level current setting of channel 1.

```
ARB:CURR:PULS:TOP? (@1)
ARB:SEQ:STEP:CURR:PULS:TOP? 1,(@1)
```

Typical Response:

```
+2.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:PULSe:STARt[:LEVel] [SOURce:]ARB:CURRent:PULSe:TOP:TIMe

## [SOURce:]ARB:CURRent:PULSe:TOP:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:PULSe:TOP:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:PULSe:TOP:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time of the pulse in seconds. Referenced to t 1 in the Pulse diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed top time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top (pulse) time of 1 second on channel 1.

```
ARB:CURR:PULS:TOP:TIM 1,(@1)
ARB:SEQ:STEP:CURR:PULS:TOP:TIM 1, 1,(@1)
```

The following query returns the top time setting of channel 1.

```
ARB:CURR:PULS:TOP:TIM? (@1)
ARB:SEQ:STEP:CURR:PULS:TOP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:PULse:TOP[:LEVel] [SOURce:]ARB:CURRent:PULSe:STARt:TIMe [SOURce:]ARB:CURRent:PULSe:END:TIMe

## [SOURce:]ARB:CURRent:RAMP:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:RAMP:END[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:RAMP:END[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END[:LEVel]
<current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END[:LEVel]?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end-level current (after the ramp occurs) in amperes. Referenced to I in the Ramp diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end current level for the ramp on channel 1.

```
ARB:CURR:RAMP:END 2,(@1)
ARB:SEQ:STEP:CURR:RAMP:END 2, 1,(@1)
```

The following query returns the end current ramp setting of channel 1.

```
ARB:CURR:RAMP:END? (@1)
ARB:SEQ:STEP:CURR:RAMP:END? 1,(@1)
```

Typical Response:

```
+2.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:RAMP:STARt[:LEVel] [SOURce:]ARB:CURRent:RAMP:END:TIMe

## [SOURce:]ARB:CURRent:RAMP:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:RAMP:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:RAMP:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the ramp completes, that the end-level current persists. Referenced to t in the Ramp diagram.

2

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the ramp on channel 1.

```
ARB:CURR:RAMP:END:TIM 1,(@1)
ARB:SEQ:STEP:CURR:RAMP:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:CURR:RAMP:END:TIM? (@1)
ARB:SEQ:STEP:CURR:RAMP:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:RAMP:END[:LEVel] [SOURce:]ARB:CURRent:RAMP:STARt:TIMe [SOURce:]ARB:CURRent:RAMP:RTIMe

## [SOURce:]ARB:CURRent:RAMP:RTIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:RTIMe

### Syntax

```
[SOURce:]ARB:CURRent:RAMP:RTIMe <time>, (@<chanlist>)
[SOURce:]ARB:CURRent:RAMP:RTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:RTIMe <time>,
<step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:RTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the rise time of the ramp in seconds. Referenced to t in the Ramp diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed rise time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a rise time of 10 seconds for the ramp on channel 1.

```
ARB:CURR:RAMP:RTIM 10,(@1)
ARB:SEQ:STEP:CURR:RAMP:RTIM 10, 1,(@1)
```

The following query returns the rise time setting of channel 1.

```
ARB:CURR:RAMP:RTIM? (@1)
ARB:SEQ:STEP:CURR:RAMP:RTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:RAMP:STARt:TIMe [SOURce:]ARB:CURRent:RAMP:END:TIMe

## [SOURce:]ARB:CURRent:RAMP:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:RAMP:STARt[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:RAMP:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial current (before the ramp occurs) in amperes. Referenced to I in the Ramp diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial current level for the ramp on channel 1.

```
ARB:CURR:RAMP:STAR 1,(@1)
ARB:SEQ:STEP:CURR:RAMP:STAR 1, 1,(@1)
```

The following query returns the initial current ramp setting of channel 1.

```
ARB:CURR:RAMP:STAR? (@1)
ARB:SEQ:STEP:CURR:RAMP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:RAMP:STARt:TIMe [SOURce:]ARB:CURRent:RAMP:END[:LEVel]

## [SOURce:]ARB:CURRent:RAMP:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:RAMP:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:RAMP:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the ramp occurs. Referenced to t in the Ramp diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the ramp on channel 1.

```
ARB:CURR:RAMP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:RAMP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:RAMP:STAR:TIM? (@1)
ARB:SEQ:STEP:CURR:RAMP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:RAMP:STARt[:LEVel] [SOURce:]ARB:CURRent:RAMP:END:TIMe [SOURce:]ARB:CURRent:RAMP:RTIMe

## [SOURce:]ARB:CURRent:SINusoid:AMPLitude

## [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:AMPLitude

### Syntax

```
[SOURce:]ARB:CURRent:SINusoid:AMPLitude <amplitude>,
(@<chanlist>)
[SOURce:]ARB:CURRent:SINusoid:AMPLitude? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid
:AMPLitude <amplitude>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid
:AMPLitude? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the amplitude or peak value of the sine wave in amperes. Referenced to I in the Sinusoid diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<amplitude\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed amplitude in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an amplitude of 1 ampere on channel 1.

```
ARB:CURR:SIN:AMPL 1,(@1)
ARB:SEQ:STEP:CURR:SIN:AMPL 1, 1,(@1)
```

The following query returns the amplitude setting of channel 1.

```
ARB:CURR:SIN:AMPL? (@1)
ARB:SEQ:STEP:CURR:SIN:AMPL? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:SINusoid:OFFSet [SOURce:]ARB:CURRent:SINusoid:FREQuency

## [SOURce:]ARB:CURRent:SINusoid:FREQuency

## [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:FREQuency

### Syntax

```
[SOURce:]ARB:CURRent:SINusoid:FREQuency <frequency>,
(@<chanlist>)
[SOURce:]ARB:CURRent:SINusoid:FREQuency? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid
:FREQuency <frequency>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid
:FREQuency? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the frequency of the sine wave in Hertz.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<frequency\> | NRf+ | 3.8147E-5 - 1.0E4 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed amplitude in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a frequency of 10 Hz on channel 1.

```
ARB:CURR:SIN:FREQ 10,(@1)
ARB:SEQ:STEP:CURR:SIN:FREQ 10, 1,(@1)
```

The following query returns the frequency setting of channel 1.

```
ARB:CURR:SIN:FREQ? (@1)
ARB:SEQ:STEP:CURR:SIN:FREQ? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:SINusoid:AMPLitude [SOURce:]ARB:CURRent:SINusoid:OFFSet

## [SOURce:]ARB:CURRent:SINusoid:OFFSet

## [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:OFFSet

### Syntax

```
[SOURce:]ARB:CURRent:SINusoid:OFFSet <offset>,
(@<chanlist>)
[SOURce:]ARB:CURRent:SINusoid:OFFSet? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:OFFSet
<offset>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:OFFSet?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the offset of the sine wave from zero, in amperes.

Referenced to I in the Sinusoid diagram.

1

IMPORTANT: Except for models N678xA SMU, the output cannot generate negative currents. Therefore, the offset value cannot be less than the amplitude of the sine wave.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<offset\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed offset in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an offset of 1 ampere on channel 1.

```
ARB:CURR:SIN:OFFS 10,(@1)
ARB:SEQ:STEP:CURR:SIN:OFFS 10, 1,(@1)
```

The following query returns the offset setting of channel 1.

```
ARB:CURR:SIN:OFFS? (@1)
ARB:SEQ:STEP:CURR:SIN:OFFS? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:SINusoid:AMPLitude [SOURce:]ARB:CURRent:SINusoid:FREQuency

## [SOURce:]ARB:CURRent:STAircase:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:END[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:END[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end level current (after the staircase occurs) in amperes. Referenced to I in the Staircase diagram. The current 1 difference between the starting current and the ending current is divided equally between the steps.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end current level for the staircase on channel 1.

```
ARB:CURR:STA:END 2,(@1)
ARB:SEQ:STEP:CURR:STA:END 2, 1,(@1)
```

The following query returns the end current level setting of channel 1.

```
ARB:CURR:STA:END? (@1)
ARB:SEQ:STEP:CURR:STA:END? 1,(@1)
```

Typical Response:

```
+2.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STAircase:STARt[:LEVel] [SOURce:]ARB:CURRent:STAircase:END:TIMe

## [SOURce:]ARB:CURRent:STAircase:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the staircase completes, that the end-level current persists. Referenced to t in the 2 Staircase diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second for the staircase on channel 1.

```
ARB:CURR:STA:END:TIM 1,(@1)
ARB:SEQ:STEP:CURR:STA:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:CURR:STA:END:TIM? (@1)
ARB:SEQ:STEP:CURR:STA:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STAircase:END[:LEVel] [SOURce:]ARB:CURRent:STAircase:STARt:TIMe [SOURce:]ARB:CURRent:STAircase:TIMe

## [SOURce:]ARB:CURRent:STAircase:NSTeps

## [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:NSTeps

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:NSTeps <steps>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:NSTeps? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:NSTeps
<steps>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:NSTeps?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the number of steps in the staircase.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<steps\> | NRf+ | 0 – 500 \| MIN \| MAX | 10 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the number of steps in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs 10 steps for the staircase on channel 1.

```
ARB:CURR:STA:NST 10,(@1)
ARB:SEQ:STEP:CURR:STA:NST 10, 1,(@1)
```

The following query returns the number of steps of channel 1.

```
ARB:CURR:STA:NST? (@1)
ARB:SEQ:STEP:CURR:STA:NST? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

## [SOURce:]ARB:CURRent:STAircase:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:STARt[:LEVel]
<current>, (@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:STARt
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial current (before the staircase occurs) in amperes. Referenced to I in the Staircase diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial current level for the staircase on channel 1.

```
ARB:CURR:STA:STAR 1,(@1)
ARB:SEQ:STEP:CURR:STA:STAR 1, 1,(@1)
```

The following query returns the initial current staircase setting of channel 1.

```
ARB:CURR:STA:STAR? (@1)
ARB:SEQ:STEP:CURR:STA:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STAircase:END[:LEVel] [SOURce:]ARB:CURRent:STAircase:STARt:TIMe

## [SOURce:]ARB:CURRent:STAircase:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the staircase occurs. Referenced to t in the Staircase diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the staircase on channel 1.

```
ARB:CURR:STA:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:STA:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:STA:STAR:TIM? (@1)
ARB:SEQ:STEP:CURR:STA:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STAircase:STARt[:LEVel] [SOURce:]ARB:CURRent:STAircase:END:TIMe [SOURce:]ARB:CURRent:STAircase:TIMe

## [SOURce:]ARB:CURRent:STAircase:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:STAircase:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STAircase:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the total time to complete all of the staircase steps in seconds. Referenced to t in the Staircase diagram. Each step is 1 of equal time.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time of 10 seconds for the staircase on channel 1.

```
ARB:CURR:STA:TIM 10,(@1)
ARB:SEQ:STEP:CURR:STA:TIM 10, 1,(@1)
```

The following query returns the time setting of channel 1.

```
ARB:CURR:STA:TIM? (@1)
ARB:SEQ:STEP:CURR:STA:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:STAircase:STARt:TIMe [SOURce:]ARB:CURRent:STAircase:END:TIMe

## [SOURce:]ARB:CURRent:STEP:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:END[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:STEP:END[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STEP:END[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:END[:LEVel]
<current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:END[:LEVel]?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the step level in amperes. Referenced to I in the 1 Step diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end current level for the step on channel 1.

```
ARB:CURR:STEP:END 2,(@1)
ARB:SEQ:STEP:CURR:STEP:END 2, 1,(@1)
```

The following query returns the end current step setting of channel 1.

```
ARB:CURR:STEP:END? (@1)
ARB:SEQ:STEP:CURR:STEP:END? 1,(@1)
```

Typical Response:

```
+2.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STEP:STARt[:LEVel] [SOURce:]ARB:CURRent:STEP:STARt:TIMe

## [SOURce:]ARB:CURRent:STEP:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:STEP:STARt[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STEP:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial current level in amperes. Referenced to I in the Step diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial current level for the step on channel 1.

```
ARB:CURR:STEP:STAR 1,(@1)
ARB:SEQ:STEP:CURR:STEP:STAR 1, 1,(@1)
```

The following query returns the initial current step setting of channel 1.

```
ARB:CURR:STEP:STAR? (@1)
ARB:SEQ:STEP:CURR:STEP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STEP:STARt:TIMe [SOURce:]ARB:CURRent:STEP:END[:LEVel]

## [SOURce:]ARB:CURRent:STEP:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:STEP:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:STEP:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the step occurs. Referenced to t in the Step diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the step on channel 1.

```
ARB:CURR:STEP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:STEP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:STEP:STAR:TIM? (@1)
ARB:SEQ:STEP:CURR:STEP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:STEP:STARt[:LEVel] [SOURce:]ARB:CURRent:STEP:END[:LEVel]

## [SOURce:]ARB:CURRent:TRAPezoid:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:END:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:END
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:END
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the trapezoid completes, that the start-level current persists. Referenced to t in the 4 Trapezoid diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the trapezoid on channel 1.

```
ARB:CURR:TRAP:END:TIM 1,(@1)
ARB:SEQ:STEP:CURR:TRAP:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:CURR:TRAP:END:TIM? (@1)
ARB:SEQ:STEP:CURR:TRAP:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe [SOURce:]ARB:CURRent:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:CURRent:TRAPezoid:FTIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:FTIMe

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:FTIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:FTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:FTIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:FTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the fall time of the trapezoid in seconds.

Referenced to t in the Trapezoid diagram.

3

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed fall time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a fall time of 10 seconds for the trapezoid on channel 1.

```
ARB:CURR:TRAP:FTIM 10,(@1)
ARB:SEQ:STEP:CURR:TRAP:FTIM 10, 1,(@1)
```

The following query returns the fall time setting of channel 1.

```
ARB:CURR:TRAP:FTIM? (@1)
ARB:SEQ:STEP:CURR:TRAP:FTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe [SOURce:]ARB:CURRent:TRAPezoid:END:TIMe [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:CURRent:TRAPezoid:RTIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:RTIMe

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:RTIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:RTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:RTIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:RTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the rise time of the trapezoid in seconds.

Referenced to t in the Trapezoid diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed rise time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a rise time of 10 seconds for the trapezoid on channel 1.

```
ARB:CURR:TRAP:RTIM 10,(@1)
ARB:SEQ:STEP:CURR:TRAP:RTIM 10, 1,(@1)
```

The following query returns the rise time setting of channel 1.

```
ARB:CURR:TRAP:RTIM? (@1)
ARB:SEQ:STEP:CURR:TRAP:RTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe [SOURce:]ARB:CURRent:TRAPezoid:END:TIMe [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:CURRent:TRAPeziod:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:TRAPeziod:STARt[:LEVel]
<current>, (@<chanlist>)
[SOURce:]ARB:CURRent:TRAPeziod:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt[:L
EVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt[:L
EVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial and final current level of the trapezoid in amperes. Referenced to I in the Trapezoid diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the initial and final current for the trapezoid on channel 1.

```
ARB:CURR:TRAP:STAR 1,(@1)
ARB:SEQ:STEP:CURR:TRAP:STAR 1, 1,(@1)
```

The following query returns the starting and ending current setting of channel 1.

```
ARB:CURR:TRAP:STAR? (@1)
ARB:SEQ:STEP:CURR:TRAP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe [SOURce:]ARB:CURRent:TRAPezoid:TOP[:LEVel]

## [SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the rising ramp occurs. Referenced to t in the Trapezoid 0 diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the trapezoid on channel 1.

```
ARB:CURR:TRAP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:CURR:TRAP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:CURR:TRAP:STAR:TIM? (@1)
ARB:SEQ:STEP:CURR:TRAP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:CURRent:TRAPezoid:END:TIMe [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:CURRent:TRAPezoid:TOP[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP[:LEVel]

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:TOP[:LEVel] <current>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:TOP[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP
[:LEVel] <current>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the top level current of the trapezoid in amperes.

Referenced to I in the Trapezoid diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level current for the trapezoid on channel 1.

```
ARB:CURR:TRAP:TOP 2,(@1)
ARB:SEQ:STEP:CURR:TRAP:TOP 2, 1,(@1)
```

The following query returns the top level current setting of channel 1.

```
ARB:CURR:TRAP:TOP? (@1)
ARB:SEQ:STEP:CURR:TRAP:TOP? 1,(@1)
```

Typical Response:

```
+2.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP:TIMe

### Syntax

```
[SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:CURRent:TRAPezoid:TOP:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time of the top level of the trapezoid in seconds. Referenced to t in the Trapezoid diagram.

2

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 – 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed top level time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level time of 1 second on channel 1.

```
ARB:CURR:TRAP:TOP:TIM 1,(@1)
ARB:SEQ:STEP:CURR:TRAP:TOP:TIM 1, 1,(@1)
```

The following query returns the top level time setting of channel 1.

```
ARB:CURR:TRAP:TOP:TIM? (@1)
ARB:SEQ:STEP:CURR:TRAP:TOP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:TRAPezoid:RTIMe [SOURce:]ARB:CURRent:TRAPezoid:FTIMe

## [SOURce:]ARB:CURRent:UDEFined:BOSTep[:DATA]

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep[:DATA]

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:BOSTep[:DATA]
<Bool>{,<Bool>}, (@<chanlist>)
[SOURce:]ARB:CURRent:UDEFined:BOSTep[:DATA]?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep
[:DATA] <Bool>{,<Bool>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep
[:DATA]? <step#>, (@<chanlist>)
```

### Description

This command specifies which user-defined ARB points or steps will generate a trigger-out signal at the beginning of the step (BOSTep). A comma-delimited list of up to 511 steps may be programmed. The state is either ON (1) or OFF (0).

A trigger is only generated when the state is set to ON.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | 1 point with a value of OFF |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if no trigger is generated, and 1 if a trigger is generated. Multiple responses are separated by commas.

### Examples

The following command specifies that triggers will be generated at the beginning of each user-defined ARB step. The ARB contains 5 points or steps and is on channel 1.

```
ARB:CURR:UDEF:BOST ON,ON,ON,ON,ON,(@1)
ARB:SEQ:STEP:CURR:UDEF:BOST ON,ON,ON,ON,ON,1,(@1)
```

The following query returns the ARB step trigger settings of channel 1.

```
ARB:CURR:UDEF:BOST? (@1)
ARB:SEQ:STEP:CURR:UDEF:BOST? 1,(@1)
```

Typical Response:

```
1,1,1,1,1
```

## [SOURce:]ARB:CURRent:UDEFined:BOSTep:POINts?

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep:POINts?

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:BOSTep:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of beginning-of-step points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of BOST points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of BOST points in a user-defined ARB for channel 1.

```
ARB:CURR:UDEF:BOST:POIN? (@1)
ARB:SEQ:STEP:CURR:UDEF:BOST:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:CURRent:UDEFined:DWELl

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:DWELl <time>{,<time>},
(@<chanlist>)
[SOURce:]ARB:CURRent:UDEFined:DWELl? (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl
<time>{,<time>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl?
<step#>, (@<chanlist>)
```

### Description

This command specifies the dwell time for each user-defined current ARB point. A comma-delimited list of up to 511 points may be programmed.

Dwell time is the time that the output will remain at a specific point. Dwell times can be programmed from 0 through 262.144 seconds with the following resolution: All Models except N678xA

| Range in seconds | Resolution |
|---|---|
| 0 - 0.262144 | 1 microsecond |
| 0 - 2.62144 | 10 microseconds |
| 0 - 26.2144 | 100 microseconds |
| 0 - 262.144 | 1 millisecond |
| Models N678xA only |  |

| Range in seconds | Resolution |
|---|---|
| 0 - 0.268435 | 1.024 microsecond |
| 0 - 2.68435 | 10.24 microseconds |
| 0 - 26.8435 | 102.4 microseconds |
| 0 - 268.435 | 1.024 millisecond |

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf | 0 - 262.144 (all except N678xA SMU) 0 - 268.435 (N678xA SMU only) | 1 point with a value of 0.001 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

At the end of the dwell time, the output state of the unit depends upon the [SOURce;]ARB:TERMinate:LAST program settings.

The order in which the dwell values are entered determines the sequence of execution.

To create a valid user-defined ARB, the Current level, BOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpolated as having the same length as the maximum length list.

### Return Format

\<NR3\> The query command returns the programmed dwell time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a dwell list. The list contains 5 steps and is on channel 1.

```
ARB:CURR:UDEF:DWEL 0.2,0.8,1.5,0.8,0.2,(@1)
ARB:SEQ:STEP:CURR:UDEF:DWEL
0.2,0.8,1.5,0.8,0.2,1,(@1)
```

The following query returns the dwell list settings of channel 1.

```
ARB:CURR:UDEF:DWEL? (@1)
ARB:SEQ:STEP:CURR:UDEF:DWEL? 1,(@1)
```

Typical Response:

```
+2.000000E-01,+8.000000E-01,+1.500000E+00,+8.000000E-
01,+02.000000E-01
```

### See Also

[SOURce:]ARB:CURRent:UDEFined:LEVel [SOURce:]ARB:CURRent:UDEFined:BOST

## [SOURce:]ARB:CURRent:UDEFined:DWELl:POINts?

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl:POINts?

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:DWELl:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of dwell points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of dwell points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of dwell points in the user-defined ARB for channel 1.

```
ARB:CURR:UDEF:DWEL:POIN? (@1)
ARB:SEQ:STEP:CURR:UDEF:DWEL:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:CURRent:UDEFined:LEVel

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:LEVel
<current>{,<current>}, (@<chanlist>)
[SOURce:]ARB:CURRent:UDEFined:LEVel? (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel
<current>{,<current>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel?
<step#>, (@<chanlist>)
```

### Description

This command specifies the current setting for each user-defined ARB point in amperes. A comma-delimited list of up to 511 points may be programmed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a user-defined current ARB. The ARB contains 5 points and is on channel 1.

```
ARB:CURR:UDEF:LEV 5,4,3,2,1,(@1)
ARB:SEQ:STEP:CURR:UDEF:LEV 5,4,3,2,1,1,(@1)
```

The following query returns the current ARB settings of channel 1.

```
ARB:CURR:UDEF:LEV? (@1)
ARB:SEQ:STEP:CURR:UDEF:LEV? 1,(@1)
```

Typical Response:

```
+5.000000E+00,+4.000000E+00,+3.000000E+00,
+2.000000E+00,+1.000000E+00
```

### See Also

[SOURce:]ARB:CURRent:UDEFined:DWELl [SOURce:]ARB:CURRent:UDEFined:BOST

## [SOURce:]ARB:CURRent:UDEFined:LEVel:POINts?

## [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel:POINts?

### Syntax

```
[SOURce:]ARB:CURRent:UDEFined:LEVel:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of current points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of current points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of current points in a user-defined ARB for channel 1.

```
ARB:CURR:UDEF:LEV:POIN? (@1)
ARB:SEQ:STEP:CURR:UDEF:LEV:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:FUNCtion

### Syntax

```
[SOURce:]ARB:FUNCtion <function>, (@<chanlist>)
[SOURce:]ARB:FUNCtion? (@<chanlist>)
```

### Description

This command sets the function of the arbitrary waveform generator.

STEP Specifies a voltage step.

RAMP Specifies a voltage ramp.

STAircase Specifies a voltage staircase.

SINusoid Specifies a voltage sine wave.

PULSe Specifies a voltage pulse.

TRAPezoid Specifies a voltage trapezoid.

EXPonential Specifies an exponential voltage.

UDVoltage Specifies a user-defined voltage waveform.

UDCurrent Specifies a user-defined current waveform.

NONE Specifies no arbitrary waveform.

> **NOTE** This command has been superceded by [SOURce:]ARB:FUNCtion:SHAPe and [SOURce:]ARB:FUNCtion:TYPE, but is still available for backward compatibility. Use the new commands to select current Arbs, constant-dwell Arbs, and Arb sequences.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<function\> | CPD | STEP \| RAMP \| STAircase \| SINusoid \| PULSe \| TRAPezoid \| EXPonential \| UDVoltage \| UDCurrent \| NONE | NONE |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Select the [SOURce:]VOLTage:MODE ARB parameter to enable the instrument to generate arbitrary voltage waveforms when the transient system is initiated and triggered.

Select the [SOURce:]CURRent:MODE ARB parameter to enable the instrument to generate arbitrary current waveforms when the transient system is initiated and triggered.

### Return Format

\<CRD\> The query command returns STEP, RAMP, STA, SIN, PULS, TRAP, EXP, UDV, UDC, CDW, SEQ, or NONE.

### Example

The following command specifies a voltage step on channel 1.

```
ARB:FUNC STEP,(@1)
```

The following query returns the ARB function that is presently set on channel 2.

```
ARB:FUNC? (@2)
```

Typical Response:

```
NONE
```

### See Also

[SOURce:]ARB:FUNCtion:SHAPe [SOURce:]ARB:FUNCtion:TYPE

## [SOURce:]ARB:FUNCtion:SHAPe

### Syntax

```
[SOURce:]ARB:FUNCtion:SHAPe <function>, (@<chanlist>)
[SOURce:]ARB:FUNCtion:SHAPe? (@<chanlist>)
```

### Description

This command sets the function of the arbitrary waveform generator.

STEP Specifies a step.

RAMP Specifies a ramp.

STAircase Specifies a staircase.

SINusoid Specifies a sine wave.

PULSe Specifies a pulse.

TRAPezoid Specifies a trapezoid.

EXPonential Specifies an exponential waveform.

UDEFined Specifies a user-defined waveform.

CDWell Specifies a constant-dwell waveform.

SEQuence Specifies a sequence of arbitrary waveforms.

NONE Specifies no arbitrary waveform.

> **NOTE** This command replaces the previous [SOURce:]ARB:FUNCtion command and should be used in new applications.

[SOURce:ARB:FUNCtion is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<function\> | CPD | STEP \| RAMP \| STAircase \| SINusoid \| PULSe \| TRAPezoid \| EXPonential \| UDEFined \| CDWell \| SEQuence \|NONE | NONE |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Select the [SOURce:]VOLTage:MODE ARB parameter to enable the instrument to generate arbitrary voltage waveforms when the transient system is initiated and triggered.

Select the [SOURce:]CURRent:MODE ARB parameter to enable the instrument to generate arbitrary current waveforms when the transient system is initiated and triggered.

### Return Format

\<CRD\> The query command returns STEP, RAMP, STA, SIN, PULS, TRAP, EXP, UDEF, CDW, SEQ, or NONE.

### Example

The following command specifies a step on channel 1.

```
ARB:FUNC:SHAP STEP,(@1)
```

The following query returns the ARB function that is presently set on channel 2.

```
ARB:FUNC:SHAP? (@2)
```

Typical Response:

```
NONE
```

### See Also

[SOURce:]ARB:FUNCtion:TYPE

## [SOURce:]ARB:FUNCtion:TYPE

### Syntax

```
[SOURce:]ARB:FUNCtion:TYPE <type>, (@<chanlist>)
[SOURce:]ARB:FUNCtion:TYPE? (@<chanlist>)
```

### Description

This command selects either a voltage or current ARB. Only one type of ARB may be output at a time.

> **NOTE** This command replaces the previous [SOURce:]ARB:FUNCtion command and should be used in new applications. [SOURce:ARB:FUNCtion is still available for backward compatibility.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"type " \> | SPD | CURRent \| VOLTage | VOLTage |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns CURR or VOLT.

### Examples

The following command selects the ARB type on channel 3.

```
ARB:FUNC:TYPE VOLT, (@3)
```

The following query returns the ARB type selected on channel 1.

```
ARB:FUNC:TYPE? (@1)
```

Typical Response:

```
VOLT
```

### See Also

[SOURce:]ARB:FUNCtion:SHAPe

## [SOURce:]ARB:SEQuence:COUNt

### Syntax

```
[SOURce:]ARB:SEQuence:COUNt <count>|INFinity,
(@<chanlist>)
[SOURce:]ARB:SEQuence:COUNt? [MIN|MAX|INFinity,]
(@<chanlist>)
```

### Description

This command sets the number of times that the ARB sequence is repeated. The repeat count range is 1 through 4096.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<count\> | NRf+ | 1 - 4096 \| MIN \| MAX \| INFinity | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Use the INFinity parameter to repeat the sequence continuously. If a value greater than 4096 is programmed, the sequence will also repeat continuously.

Use ABORt:TRANsient to stop the Arb at any time. When the Arb is aborted, the output returns to the settings that were in effect before the Arb started.

### Return Format

\<NR3\> The query command returns the repeat count for each channel specified.

Multiple responses are separated by commas. If a repeat count of 9.9E37 is returned, it means that the sequence is set to repeat continuously.

### Examples

The following command sets the repeat count to 10 on channel 1.

```
ARB:SEQ:COUN 10,(@1)
```

The following query returns the repeat count of channel 1.

```
ARB:SEQ:COUN? (@1)
```

Typical Response:

```
+10
```

## [SOURce:]ARB:SEQuence:LENgth?

### Syntax

```
[SOURce:]ARB:SEQuence:LENgth? (@<chanlist>)
```

### Description

This query returns the total number of steps in the ARB sequence.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of steps in the ARB sequence. Multiple responses are separated by commas.

### Example

The following query returns the number of steps in the ARB sequence defined for channel 1.

```
ARB:SEQ:LEN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:SEQuence:QUALity?

### Syntax

```
[SOURce:]ARB:SEQuence:QUALity? (@<chanlist>)
```

### Description

This query returns the quality of the waveforms in the ARB sequence. This is a number between 16 and 100 that is an indication of how well waveforms are represented. It is the number of points used to represent ARBs that are smooth curves (ramp, trapezoid, exponential, and sine). 16 is the minimum number of points that defines the curve (worst quality).

100 is the maximum number of points that defines the curve (best quality).

Note that the quality of a given waveform is determined by the total number and type of waveforms that comprise the sequence. The maximum number of points allowed in a sequence is 511. As more waveforms are added to the sequence, the quality of the waveforms is reduced to accommodated the 511-point limit.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The quality of the ARB sequence. Returns a number between 16 and 100.

Multiple responses are separated by commas.

### Example

The following query returns the quality of the ARB sequence defined for channel 1.

```
ARB:SEQ:QUAL? (@1)
```

Typical Response:

```
+100
```

## [SOURce:]ARB:SEQuence:RESet

### Syntax

```
[SOURce:]ARB:SEQuence:RESet (@<chanlist>)
```

### Description

This command resets the ARB sequence to its power-on default setting: Step = 1 Shape = PULSe

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command resets the ARB sequence on channel 1.

```
ARB:SEQ:RES (@1)
```

## [SOURce:]ARB:SEQuence:STEP:COUNt

### Syntax

```
[SOURce:]ARB:SEQuence:STEP:COUNt <count>|INFinity,
<step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:COUNt? [MIN|MAX|INFinity,]
<step#>, (@<chanlist>)
```

### Description

This command sets the number of times that the sequence step is repeated. The repeat count range is 1 through \>16 million. The maximum number of steps that can be programmed is 100. This setting is only valid if the [SOURce:]ARB:SEQuence:STEP:PACing is TRIGgered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<count\> | NRf+ | 1 - 16,777,216 \| MIN \| MAX \| INFinity | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Use the INFinity parameter to repeat the sequence step continuously. If MAX, or a value greater than 16,777,216 is programmed, the step will also repeat continuously.

Use ABORt:TRANsient to stop the Arb at any time. When the Arb is aborted, the output returns to the settings that were in effect before the Arb started.

### Return Format

\<NR3\> The query command returns the repeat count for each channel specified.

Multiple responses are separated by commas. If a repeat count of 9.9E37 is returned, it means that the sequence step is set to repeat continuously.

### Examples

The following command sets the a repeat count of 10 for sequence step 1 on channel 1.

```
ARB:SEQ:STEP:COUN 10, 1,(@1)
```

The following query returns the sequence step repeat count of channel 1.

```
ARB:SEQ:STEP:COUN? 1,(@1)
```

Typical Response:

```
+10
```

### See Also

[SOURce:]ARB:SEQuence:STEP:PACing

## [SOURce:]ARB:SEQuence:STEP:CURRent

The [SOURce:]ARB:SEQuence:STEP:CURRent commands program waveform steps within an ARB sequence.

All of the [SOURce:]ARB:CURRent commands that set waveform parameters have corresponding commands that set those same parameters for waveform steps within an ARB sequence. They follow the pattern:

```
[SOURce:]ARB:CURRent:EXPonential:END <level>,
(@<chanlist>)
[SOURce:]ARB :SEQuence:STEP :CURRent:EXPonential:END
<level>, <step#>, (@<chanlist>)
```

where items in bold are added to the sequence step version of the single ARB command. The \<step#\> parameter indicates the step number within the ARB sequence.

### Command Summary

The following links reference the corresponding single ARB command.

> **NOTE** All parameters in the single ARB command match the ARB sequence step version of the command. The only additional parameter in the ARB sequence command is the \<step#\> parameter, which references the step number within the sequence.

[SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TCONstant [SOURce:]ARB:SEQuence:STEP:CURRent:EXPonential:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:END:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:PULSe:TOP:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:END:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:RTIMe [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:RAMP:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:AMPLitude [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:FREQuency [SOURce:]ARB:SEQuence:STEP:CURRent:SINusoid:OFFSet [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:END:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:NSTeps [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:STAircase:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:STEP:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:END:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:FTIMe [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:RTIMe [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP[:LEVel] [SOURce:]ARB:SEQuence:STEP:CURRent:TRAPezoid:TOP:TIMe [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep[:DATA] [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:BOSTep:POINts?

[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:DWELl:POINts?

[SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel [SOURce:]ARB:SEQuence:STEP:CURRent:UDEFined:LEVel:POINts?

## [SOURce:]ARB:SEQuence:STEP:FUNCtion:SHAPe

### Syntax

```
[SOURce:]ARB:SEQuence:STEP:FUNCtion:SHAPe <function>,
<step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:FUNCtion:SHAPe? <step#>,
(@<chanlist>)
```

### Description

This command creates a new ARB sequence step or changes the waveform of an existing sequence step. The maximum number of steps that can be programmed is 100. The following waveforms may be assigned to a sequence step: STEP Specifies a step.

RAMP Specifies a ramp.

STAircase Specifies a staircase.

SINusoid Specifies a sine wave.

PULSe Specifies a pulse.

TRAPezoid Specifies a trapezoid.

EXPonential Specifies an exponential waveform.

UDEFined Specifies a user-defined waveform.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<function\> | CPD | STEP \| RAMP \| STAircase \| SINusoid \| PULSe \| TRAPezoid \| EXPonential \| UDEFined | PULSe |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

If the \<step#\> specified is an existing sequence step, that step will be changed to the specified waveshape with all parameters reset to default values.

New sequence steps must be specified sequentially. To create a new sequence step, \<step#\> should be specified to be the current length of the sequence (see [SOURce:]ARB:SEQuence:LENgth?). When a step is added, all parameters of the step waveform are reset to their default values.

### Return Format

\<CRD\> The query command returns STEP, RAMP, STA, SIN, PULS, TRAP, EXP, or UDEF.

### Example

The following command specifies a shape for sequence step 1 on channel 1.

```
ARB:SEQ:STEP:FUNC:SHAP SIN, 1, (@1)
```

The following query returns the sequence step shape that is presently set on channel 2.

```
ARB:SEQ:STEP:FUNC:SHAP? 1,(@2)
```

Typical Response:

```
PULSe
```

### See Also

[SOURce:]ARB:SEQuence:LENgth?

## [SOURce:]ARB:SEQuence:STEP:PACing

### Syntax

```
[SOURce:]ARB:SEQuence:STEP:PACing <pacing>, <step#>,
(@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:PACing? <step#>,
(@<chanlist>)
```

### Description

This command specifies the type of pacing for the specified step number: DWELl When dwell paced, the step moves to the next step when the dwell time is finished.

TRIGgered When trigger paced, the step waits at the last value of the step until a trigger is received. The next step is started upon receipt of the trigger.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<pacing\> | CPD | DWELl \| TRIGgered | DWELl |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

If the \<step#\> specified is an existing sequence step, that step will be changed to the specified waveshape with all parameters reset to default values..

New sequence steps must be specified sequentially. To create a new sequence step, \<step#\> should be specified to be the current length of the sequence + 1 (see [SOURce:]ARB:SEQuence:LENgth?). When a step is added, all parameters of the step waveform are reset to their default values.

### Return Format

\<CRD\> The query command returns DWEL or TRIG.

### Example

The following command specifies trigger pacing for sequence step 1 on channel 1.

```
ARB:SEQ:STEP:PAC TRIG, 1,(@1)
```

The following query returns the sequence step shape that is presently set on channel 2.

```
ARB:SEQ:STEP:PAC? 1,(@2)
```

Typical Response:

```
DWEL
```

### See Also

[SOURce:]ARB:SEQuence:LENgth?

## [SOURce:]ARB:SEQuence:STEP:VOLTage

The [SOURce:]ARB:SEQuence:STEP:VOLTage commands program waveform steps within an ARB sequence.

All of the [SOURce:]ARB:VOLTage commands that set waveform parameters have corresponding commands that set those same parameters for waveform steps within an ARB sequence. They follow the pattern:

```
[SOURce:]ARB:VOLTage:EXPonential:END <level>,
(@<chanlist>)
[SOURce:]ARB :SEQuence:STEP :VOLTage:EXPonential:END
<level>, <step#>, (@<chanlist>)
```

where items in bold are added to the sequence step version of the single ARB command. The \<step#\> parameter indicates the step number within the ARB sequence.

### Command Summary

The following links reference the corresponding single ARB command.

> **NOTE** All parameters in the single ARB command match the ARB sequence step version of the command. The only additional parameter in the ARB sequence command is the \<step#\> parameter, which references the step number within the sequence.

[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TCONstant [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:END:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:RTIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:AMPLitude [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:FREQuency [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:OFFSet [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:NSTeps [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:END[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:END:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:FTIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:RTIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP[:LEVel] [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP:TIMe [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep[:DATA] [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep:POINts?

[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl:POINts?

[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel:POINts?

## [SOURce:]ARB:SEQuence:TERMinate:LAST

### Syntax

[SOURce:]ARB:SEQuence:TERMinate:LAST \<Bool\>, (@\<chanlist\>)

[SOURce:]ARB:SEQuence:TERMinate:LAST? (@\<chanlist\>)

### Description

This command determines the output value when the ARB sequence terminates. The state is either ON (1) or OFF (0).

When ON, the output voltage or current remains at the last ARB sequence value. The last voltage or current ARB value becomes the IMMediate value when the sequence completes.

When OFF, and also when the ARB sequence is aborted, the output returns to the settings that were in effect before the sequence started.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the output returns to the settings that were in effect before the sequence started, and 1 if the output voltage or current remains at the last sequence value.

### Examples

The following command sets the sequence to terminate with the output voltage or current remaining at the last sequence value on channel 2.

```
ARB:SEQ:TERM:LAST ON,(@2)
```

The following query returns the sequence terminate setting of channel 1.

```
ARB:SEQ:TERM:LAST? (@1)
```

Typical Response:

```
0
```

## [SOURce:]ARB:TERMinate:LAST

### Syntax

[SOURce:]ARB:TERMinate:LAST \<Bool\>, (@\<chanlist\>)

[SOURce:]ARB:TERMinate:LAST? (@\<chanlist\>)

### Description

This command determines the output value when the arbitrary waveform terminates. The state is either ON (1) or OFF (0).

When ON, the output voltage or current remains at the last ARB value.

The last voltage or current ARB value becomes the IMMediate value when the ARB completes.

When OFF, and also when the ARB is aborted, the output returns to the settings that were in effect before the ARB started.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the output returns to the settings that were in effect before the ARB started, and 1 if the output voltage or current remains at the last ARB value.

### Examples

The following command sets the ARB to terminate with the output voltage or current remaining at the last ARB value on channel 2.

```
ARB:TERM:LAST ON,(@2)
```

The following query returns the ARB terminate setting of channel 1.

```
ARB:TERM:LAST? (@1)
```

Typical Response:

```
0
```

## [SOURce:]ARB:VOLTage:CDWell[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:CDWell[:LEVel]
<voltage>{,<voltage>}, (@<chanlist>)
[SOURce:]ARB:VOLTage:CDWell[:LEVel]? (@<chanlist>)
```

### Description

This command specifies the level of each point of a constant dwell ARB.

Current and voltage CD ARBs share settings, so setting the voltage CD ARB resets the current CD ARB level to its default value and vice-versa. A comma-delimited list of up to 65,535 points may be programmed.

For better performance, the list of voltage points can be sent as a definite length binary block instead of an ASCII list.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf | 0 – maximum | 1 point set to the |

or The maximum value is dependent minimum \<block\> on the voltage rating of the power programmable module. value \<chanlist\> Numeric One or more channels. Required (@2) - channel 2 parameter (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3.

### Return Format

The return format depends on the settings of the FORMat:BORDer and FORMat[:DATA] commands. When the data format is set to ASCII, returned values are comma separated. Only one channel can be queried when the format is ASCII. When the data format is set to REAL, data is returned as single precision floating point numbers in definite length arbitrary block response format. Each block contains all the records for one of the channels given in the \<chanlist\> parameter. If multiple channels are given, then each definite length arbitrary block of data is separated by a comma.

\<NR3\> [,\<NR3\>] or \<block\> [,\<block\>]

### Examples

The following command programs a constant-dwell voltage ARB. The ARB contains 5 points and is on channel 1.

```
ARB:VOLT:CDW 5,4,3,2,1,(@1)
```

The following query returns the constant-dwell voltage settings of channel 1.

```
ARB:VOLT:CDW? (@1)
```

### See Also

[SOURce:]ARB:VOLTage:CDWell:DWELl

FORMat:BORDer FORMat[:DATA]

## [SOURce:]ARB:VOLTage:CDWell:DWELl

### Syntax

```
[SOURce:]ARB:VOLTage:CDWell:DWELl <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:CDWell:DWELl? (@<chanlist>)
```

### Description

This command specifies the dwell time for each point of a constant-dwell ARB. Current and voltage CD ARBs share settings, so setting this parameter for a current CD ARB also changes the voltage dwell value and vice versa. Programmed values can range from 10.24 microseconds to 0.30 seconds. Values are rounded to the nearest 10.24-microsecond increment.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf | 0.00001024 - 0.30 | 0.001 seconds |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The maximum repeat count for CD ARBs is 256. See [SOURce:]ARB:COUNt.

### Return Format

\<NR3\> The query command returns the programmed dwell time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs constant-dwell time of 0.2 seconds on channel 1.

```
ARB:VOLT:CDW:DWEL 0.2,(@1)
```

The following query returns the constant-dwell time of channel 1.

```
ARB:VOLT:CDW:DWEL? (@1)
```

Typical Response:

```
+1.000000E-03
```

### See Also

[SOURce:]ARB:VOLTage:CDWell[:LEVel]

## [SOURce:]ARB:VOLTage:CDWell:POINts?

### Syntax

```
[SOURce:]ARB:VOLTage:CDWell:POINts? (@<chanlist>)
```

### Description

This query returns the number of voltage points in a constant-dwell ARB.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> Returns the number of points in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following query returns the number of voltage points of channel 1.

```
ARB:VOLT:CDW:POIN? (@1)
```

Typical Response:

```
+4.376500E+04
```

### See Also

[SOURce:]ARB:CURRent:CDWell:POINts?

## [SOURce:]ARB:VOLTage:CONVert

### Syntax

```
[SOURce:]ARB:VOLTage:CONVert (@<chanlist>)
```

### Description

This command converts the specified arbitrary waveform to a list of points in the user-defined voltage waveform format. This makes it possible to modify/edit one of the "standard" arbitrary waveforms. The command performs the same function as the "Edit Points" button on the front panel ARB Properties dialog windows.

To use this command you must first specify an ARB shape and type using the [SOURce:]ARB:FUNCtion:SHAPe and the [SOURce:]ARB:FUNCtion:TYPE commands.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

If the ARB function of the specified channel is already set to a user-defined voltage waveform, the command is ignored and the conversion is not performed.

If the ARB function of the specified channel is set to "NONE", the command is ignored and the conversion is not performed.

### Example

The following command converts the ARB previously specified on channel 1.

```
ARB:VOLT:CONV (@1)
```

### See Also

[SOURce:]ARB:FUNCtion:SHAPe [SOURce:]ARB:FUNCtion:TYPE

## [SOURce:]ARB:VOLTage:EXPonential:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:END[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:EXPonential:END[:LEVel]
<voltage> (@<chanlist>)
[SOURce:]ARB:VOLTage:EXPonential:END[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:END
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:END
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end level voltage (after the exponential waveform ends) in volts. Referenced to V in the Exponential diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end level voltage for the exponential waveform on channel 1.

```
ARB:VOLT:EXP:END 5,(@1)
ARB:SEQ:STEP:VOLT:EXP:END 5, 1,(@1)
```

The following query returns the end level voltage of channel 1.

```
ARB:VOLT:EXP:END? (@1)
ARB:SEQ:STEP:VOLT:EXP:END? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:EXPonential:STARt[:LEVel]

## [SOURce:]ARB:VOLTage:EXPonential:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:EXPonential:STARt[:LEVel]
<voltage>, (@<chanlist>)
[SOURce:]ARB:VOLTage:EXPonential:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt[
:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt[
:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial voltage (before the exponential waveform starts) in volts. Referenced to V in the Exponential diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an start level voltage for the exponential waveform on channel 1.

```
ARB:VOLT:EXP:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:EXP:STAR 1, 1,(@1)
```

The following query returns the start level voltage of channel 1.

```
ARB:VOLT:EXP:STAR? (@1)
ARB:SEQ:STEP:VOLT:EXP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:EXPonential:STARt:TIMe [SOURce:]ARB:VOLTage:EXPonential:END[:LEVel]

## [SOURce:]ARB:VOLTage:EXPonential:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:EXPonential:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:EXPonential:STARt:TIMe?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt:
TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:STARt:
TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the exponential waveform occurs. Referenced to t in the 0 Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the exponential waveform on channel 1.

```
ARB:VOLT:EXP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:EXP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:EXP:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:EXP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:EXPonential:STARt[:LEVel] [SOURce:]ARB:VOLTage:EXPonential:TIMe

## [SOURce:]ARB:VOLTage:EXPonential:TCONstant

## [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TCONstant

### Syntax

```
[SOURce:]ARB:VOLTage:EXPonential:TCONstant
<constant>, (@<chanlist>)
[SOURce:]ARB:VOLTage:EXPonential:TCONstant?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential
:TCONstant <constant>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential
:TCONstant? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time constant of the curve. Referenced to t c in the Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<constant\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the time constant in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time constant of 1 for channel 1.

```
ARB:VOLT:EXP:TCON 1,(@1)
ARB:SEQ:STEP:VOLT:EXP:TCON 1, 1,(@1)
```

The following query returns the time constant on channel 1.

```
ARB:VOLT:EXP:TCON? (@1)
ARB:SEQ:STEP:VOLT:EXP:TCON? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

## [SOURce:]ARB:VOLTage:EXPonential:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:EXPonential:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:EXPonential:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:EXPonential:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the total time for the voltage to go from the starting level to the ending level in seconds. Referenced to t in the 1 Exponential diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time of 10 seconds for the exponential waveform on channel 1.

```
ARB:VOLT:EXP:TIM 10,(@1)
ARB:SEQ:STEP:VOLT:EXP:TIM 10, 1,(@1)
```

The following query returns the time setting of channel 1.

```
ARB:VOLT:EXP:TIM? (@1)
ARB:SEQ:STEP:VOLT:EXP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:EXPonential:STARt:TIMe

## [SOURce:]ARB:VOLTage:PULSe:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:END:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:PULSe:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:PULSe:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:END:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:END:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the pulse completes, that the start-level voltage persists. Referenced to t in the Pulse 2 diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the pulse on channel 1.

```
ARB:VOLT:PULS:END:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:PULS:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:VOLT:PULS:END:TIM? (@1)
ARB:SEQ:STEP:VOLT:PULS:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel] [SOURce:]ARB:VOLTage:PULSe:STARt:TIMe [SOURce:]ARB:VOLTage:PULSe:TOP:TIMe

## [SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the voltage before and after the pulse occurs in volts. Referenced to V in the Pulse diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a starting and ending voltage level for the pulse on channel 1.

```
ARB:VOLT:PULS:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:PULS:STAR 1, 1,(@1)
```

The following query returns the starting and ending voltage setting of channel 1.

```
ARB:VOLT:PULS:STAR? (@1)
ARB:SEQ:STEP:VOLT:PULS:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:PULSe:STARt:TIMe [SOURce:]ARB:VOLTage:PULse:TOP[:LEVel]

## [SOURce:]ARB:VOLTage:PULSe:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:PULSe:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:PULSe:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the pulse occurs. Referenced to t in the Pulse diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the pulse on channel 1.

```
ARB:VOLT:PULS:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:PULS:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:PULS:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:PULS:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel] [SOURce:]ARB:VOLTage:PULSe:END:TIMe [SOURce:]ARB:VOLTage:PULSe:TOP:TIMe

## [SOURce:]ARB:VOLTage:PULSe:TOP[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:PULSe:TOP[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:PULSe:TOP[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP [:LEVel]
<voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the top level voltage of the pulse in volts.

Referenced to V in the Pulse diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level voltage for the pulse on channel 1.

```
ARB:VOLT:PULS:TOP 5,(@1)
ARB:SEQ:STEP:VOLT:PULS:TOP 5, 1,(@1)
```

The following query returns the top level voltage setting of channel 1.

```
ARB:VOLT:PULS:TOP? (@1)
ARB:SEQ:STEP:VOLT:PULS:TOP? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:PULSe:STARt[:LEVel] [SOURce:]ARB:VOLTage:PULSe:TOP:TIMe

## [SOURce:]ARB:VOLTage:PULSe:TOP:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:PULSe:TOP:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:PULSe:TOP:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:PULSe:TOP:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time of the pulse in seconds. Referenced to t 1 in the Pulse diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed top time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top (pulse) time of 1 second on channel 1.

```
ARB:VOLT:PULS:TOP:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:PULS:TOP:TIM 1, 1,(@1)
```

The following query returns the top time setting of channel 1.

```
ARB:VOLT:PULS:TOP:TIM? (@1)
ARB:SEQ:STEP:VOLT:PULS:TOP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:PULse:TOP[:LEVel] [SOURce:]ARB:VOLTage:PULSe:STARt:TIMe [SOURce:]ARB:VOLTage:PULSe:END:TIMe

## [SOURce:]ARB:VOLTage:RAMP:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:RAMP:END[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:RAMP:END[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END[:LEVel]
<voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END[:LEVel]?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end-level voltage (after the ramp occurs) in volts. Referenced to V in the Ramp diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end voltage level for the ramp on channel 1.

```
ARB:VOLT:RAMP:END 5,(@1)
ARB:SEQ:STEP:VOLT:RAMP:END 5, 1,(@1)
```

The following query returns the end voltage ramp setting of channel 1.

```
ARB:VOLT:RAMP:END? (@1)
ARB:SEQ:STEP:VOLT:RAMP:END? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:RAMP:STARt[:LEVel] [SOURce:]ARB:VOLTage:RAMP:END:TIMe

## [SOURce:]ARB:VOLTage:RAMP:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:RAMP:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:RAMP:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:END:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the ramp completes, that the end-level voltage persists. Referenced to t in the Ramp diagram.

2

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the ramp on channel 1.

```
ARB:VOLT:RAMP:END:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:RAMP:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:VOLT:RAMP:END:TIM? (@1)
ARB:SEQ:STEP:VOLT:RAMP:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:RAMP:END[:LEVel] [SOURce:]ARB:VOLTage:RAMP:STARt:TIMe [SOURce:]ARB:VOLTage:RAMP:RTIMe

## [SOURce:]ARB:VOLTage:RAMP:RTIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:RTIMe

### Syntax

```
[SOURce:]ARB:VOLTage:RAMP:RTIMe <time>, (@<chanlist>)
[SOURce:]ARB:VOLTage:RAMP:RTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:RTIMe <time>,
<step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:RTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the rise time of the ramp in seconds. Referenced to t in the Ramp diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed rise time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a rise time of 10 seconds for the ramp on channel 1.

```
ARB:VOLT:RAMP:RTIM 10,(@1)
ARB:SEQ:STEP:VOLT:RAMP:RTIM 10, 1,(@1)
```

The following query returns the rise time setting of channel 1.

```
ARB:VOLT:RAMP:RTIM? (@1)
ARB:SEQ:STEP:VOLT:RAMP:RTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:RAMP:STARt:TIMe [SOURce:]ARB:VOLTage:RAMP:END:TIMe

## [SOURce:]ARB:VOLTage:RAMP:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:RAMP:STARt[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:RAMP:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial voltage (before the ramp occurs) in volts. Referenced to V in the Ramp diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial voltage level for the ramp on channel 1.

```
ARB:VOLT:RAMP:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:RAMP:STAR 1, 1,(@1)
```

The following query returns the initial voltage ramp setting of channel 1.

```
ARB:VOLT:RAMP:STAR? (@1)
ARB:SEQ:STEP:VOLT:RAMP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:RAMP:STARt:TIMe [SOURce:]ARB:VOLTage:RAMP:END[:LEVel]

## [SOURce:]ARB:VOLTage:RAMP:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:RAMP:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:RAMP:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:RAMP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the ramp occurs. Referenced to t in the Ramp diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the ramp on channel 1.

```
ARB:VOLT:RAMP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:RAMP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:RAMP:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:RAMP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:RAMP:STARt[:LEVel] [SOURce:]ARB:VOLTage:RAMP:END:TIMe [SOURce:]ARB:VOLTage:RAMP:RTIMe

## [SOURce:]ARB:VOLTage:SINusoid:AMPLitude

## [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:AMPLitude

### Syntax

```
[SOURce:]ARB:VOLTage:SINusoid:AMPLitude <amplitude>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:SINusoid:AMPLitude? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid
:AMPLitude <amplitude>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid
:AMPLitude? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the amplitude or peak value of the sine wave in volts. Referenced to V in the Sinusoid diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<amplitude\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed amplitude in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an amplitude of 10 volts on channel 1.

```
ARB:VOLT:SIN:AMPL 10,(@1)
ARB:SEQ:STEP:VOLT:SIN:AMPL 10, 1,(@1)
```

The following query returns the amplitude setting of channel 1.

```
ARB:VOLT:SIN:AMPL? (@1)
ARB:SEQ:STEP:VOLT:SIN:AMPL? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:SINusoid:OFFSet [SOURce:]ARB:VOLTage:SINusoid:FREQuency

## [SOURce:]ARB:VOLTage:SINusoid:FREQuency

## [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:FREQuency

### Syntax

```
[SOURce:]ARB:VOLTage:SINusoid:FREQuency <frequency>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:SINusoid:FREQuency? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid
:FREQuency <frequency>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid
:FREQuency? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the frequency of the sine wave in Hertz.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<frequency\> | NRf+ | 3.8147E-5 - 1.0E4 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed amplitude in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a frequency of 10 Hz on channel 1.

```
ARB:VOLT:SIN:FREQ 10,(@1)
ARB:SEQ:STEP:VOLT:SIN:FREQ 10, 1,(@1)
```

The following query returns the frequency setting of channel 1.

```
ARB:VOLT:SIN:FREQ? (@1)
ARB:SEQ:STEP:VOLT:SIN:FREQ? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:SINusoid:AMPLitude [SOURce:]ARB:VOLTage:SINusoid:OFFSet

## [SOURce:]ARB:VOLTage:SINusoid:OFFSet

## [SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:OFFSet

### Syntax

```
[SOURce:]ARB:VOLTage:SINusoid:OFFSet <offset>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:SINusoid:OFFSet? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:OFFSet
<offset>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:SINusoid:OFFSet?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the offset of the sine wave from zero, in volts.

Referenced to V in the Sinusoid diagram.

1

IMPORTANT: Except for model N6784A, the output cannot generate negative voltages. Therefore, the offset value cannot be less than the amplitude of the sine wave.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<offset\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed offset in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an offset of 10 volts on channel 1.

```
ARB:VOLT:SIN:OFFS 10,(@1)
ARB:SEQ:STEP:VOLT:SIN:OFFS 10, 1,(@1)
```

The following query returns the offset setting of channel 1.

```
ARB:VOLT:SIN:OFFS? (@1)
ARB:SEQ:STEP:VOLT:SIN:OFFS? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:SINusoid:AMPLitude [SOURce:]ARB:VOLTage:SINusoid:FREQuency

## [SOURce:]ARB:VOLTage:STAircase:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:END[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:END[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the end level voltage (after the staircase occurs) in volts. Referenced to V in the Staircase diagram. The voltage difference 1 between the starting voltage and the ending voltage is divided equally between the steps.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end voltage level for the staircase on channel 1.

```
ARB:VOLT:STA:END 5,(@1)
ARB:SEQ:STEP:VOLT:STA:END 5, 1,(@1)
```

The following query returns the end voltage level setting of channel 1.

```
ARB:VOLT:STA:END? (@1)
ARB:SEQ:STEP:VOLT:STA:END? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STAircase:STARt[:LEVel] [SOURce:]ARB:VOLTage:STAircase:END:TIMe

## [SOURce:]ARB:VOLTage:STAircase:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:END
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the staircase completes, that the end-level voltage persists. Referenced to t in the 2 Staircase diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second for the staircase on channel 1.

```
ARB:VOLT:STA:END:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:STA:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:VOLT:STA:END:TIM? (@1)
ARB:SEQ:STEP:VOLT:STA:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STAircase:END[:LEVel] [SOURce:]ARB:VOLTage:STAircase:STARt:TIMe [SOURce:]ARB:VOLTage:STAircase:TIMe

## [SOURce:]ARB:VOLTage:STAircase:NSTeps

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:NSTeps

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:NSTeps <steps>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:NSTeps? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:NSTeps
<steps>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:NSTeps?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the number of steps in the staircase.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<steps\> | NRf+ | 0 - 500 \| MIN \| MAX | 10 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the number of steps in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs 10 steps for the staircase on channel 1.

```
ARB:VOLT:STA:NST 10,(@1)
ARB:SEQ:STEP:VOLT:STA:NST 10, 1,(@1)
```

The following query returns the number of steps of channel 1.

```
ARB:VOLT:STA:NST? (@1)
ARB:SEQ:STEP:VOLT:STA:NST? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

## [SOURce:]ARB:VOLTage:STAircase:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:STARt[:LEVel]
<voltage>, (@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial voltage (before the staircase occurs) in volts. Referenced to V in the Staircase diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial voltage level for the staircase on channel 1.

```
ARB:VOLT:STA:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:STA:STAR 1, 1,(@1)
```

The following query returns the initial voltage staircase setting of channel 1.

```
ARB:VOLT:STA:STAR? (@1)
ARB:SEQ:STEP:VOLT:STA:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STAircase:STARt:TIMe [SOURce:]ARB:VOLTage:STAircase:END[:LEVel]

## [SOURce:]ARB:VOLTage:STAircase:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the staircase occurs. Referenced to t in the Staircase diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the staircase on channel 1.

```
ARB:VOLT:STA:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:STA:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:STA:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:STA:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STAircase:STARt[:LEVel] [SOURce:]ARB:VOLTage:STAircase:END:TIMe [SOURce:]ARB:VOLTage:STAircase:TIMe

## [SOURce:]ARB:VOLTage:STAircase:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:STAircase:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STAircase:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STAircase:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the total time to complete all of the staircase steps in seconds. Referenced to t in the Staircase diagram. Each step is 1 of equal time.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a time of 10 seconds for the staircase on channel 1.

```
ARB:VOLT:STA:TIM 10,(@1)
ARB:SEQ:STEP:VOLT:STA:TIM 10, 1,(@1)
```

The following query returns the time setting of channel 1.

```
ARB:VOLT:STA:TIM? (@1)
ARB:SEQ:STEP:VOLT:STA:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:STAircase:STARt:TIMe [SOURce:]ARB:VOLTage:STAircase:END:TIMe

## [SOURce:]ARB:VOLTage:STEP:END[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:END[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:STEP:END[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STEP:END[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:END[:LEVel]
<voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:END[:LEVel]?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the step level in volts. Referenced to V in the 1 Step diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the end voltage level for the step on channel 1.

```
ARB:VOLT:STEP:END 5,(@1)
ARB:SEQ:STEP:VOLT:STEP:END 5, 1,(@1)
```

The following query returns the end voltage step setting of channel 1.

```
ARB:VOLT:STEP:END? (@1)
ARB:SEQ:STEP:VOLT:STEP:END? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STEP:STARt[:LEVel] [SOURce:]ARB:VOLTage:STEP:STARt:TIMe

## [SOURce:]ARB:VOLTage:STEP:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:STEP:STARt[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STEP:STARt[:LEVel]? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial voltage level in volts. Referenced to V 0 in the Step diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an initial voltage level for the step on channel 1.

```
ARB:VOLT:STEP:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:STEP:STAR 1, 1,(@1)
```

The following query returns the initial voltage step setting of channel 1.

```
ARB:VOLT:STEP:STAR? (@1)
ARB:SEQ:STEP:VOLT:STEP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STEP:STARt:TIMe [SOURce:]ARB:VOLTage:STEP:END[:LEVel]

## [SOURce:]ARB:VOLTage:STEP:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:STEP:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:STEP:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:STEP:STARt:TIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the step occurs. Referenced to t in the Step diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the step on channel 1.

```
ARB:VOLT:STEP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:STEP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:STEP:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:STEP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:STEP:STARt[:LEVel] [SOURce:]ARB:VOLTage:STEP:END[:LEVel]

## [SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:END:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:END
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:END
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time in seconds, after the trapezoid completes, that the start-level voltage persists. Referenced to t in the 4 Trapezoid diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed end time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs an end time of 1 second after the trapezoid on channel 1.

```
ARB:VOLT:TRAP:END:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:TRAP:END:TIM 1, 1,(@1)
```

The following query returns the end time setting of channel 1.

```
ARB:VOLT:TRAP:END:TIM? (@1)
ARB:SEQ:STEP:VOLT:TRAP:END:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:VOLTage:TRAPezoid:FTIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:FTIMe

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:FTIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:FTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:FTIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:FTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the fall time of the trapezoid in seconds.

Referenced to t in the Trapezoid diagram.

3

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed fall time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a fall time of 10 seconds for the trapezoid on channel 1.

```
ARB:VOLT:TRAP:FTIM 10,(@1)
ARB:SEQ:STEP:VOLT:TRAP:FTIM 10, 1,(@1)
```

The following query returns the fall time setting of channel 1.

```
ARB:VOLT:TRAP:FTIM? (@1)
ARB:SEQ:STEP:VOLT:TRAP:FTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:VOLTage:TRAPezoid:RTIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:RTIMe

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:RTIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:RTIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:RTIMe
<time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:RTIMe?
[MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the rise time of the trapezoid in seconds.

Referenced to t in the Trapezoid diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed rise time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a rise time of 10 seconds for the trapezoid on channel 1.

```
ARB:VOLT:TRAP:RTIM 10,(@1)
ARB:SEQ:STEP:VOLT:TRAP:RTIM 10, 1,(@1)
```

The following query returns the rise time setting of channel 1.

```
ARB:VOLT:TRAP:RTIM? (@1)
ARB:SEQ:STEP:VOLT:TRAP:RTIM? 1,(@1)
```

Typical Response:

```
+1.000000E+01
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:VOLTage:TRAPeziod:STARt[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPeziod:STARt[:LEVel]
<voltage>, (@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPeziod:STARt[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the initial and final voltage level of the trapezoid in volts. Referenced to V in the Trapezoid diagram.

0

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs the initial and final voltage for the trapezoid on channel 1.

```
ARB:VOLT:TRAP:STAR 1,(@1)
ARB:SEQ:STEP:VOLT:TRAP:STAR 1, 1,(@1)
```

The following query returns the starting and ending voltage setting of channel 1.

```
ARB:VOLT:TRAP:STAR? (@1)
ARB:SEQ:STEP:VOLT:TRAP:STAR? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:TOP[:LEVel]

## [SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:STARt:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:STARt
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the delay in seconds after the trigger is received, but before the rising ramp occurs. Referenced to t in the Trapezoid 0 diagram.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 0 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed start time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a start time of 1 second for the trapezoid on channel 1.

```
ARB:VOLT:TRAP:STAR:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:TRAP:STAR:TIM 1, 1,(@1)
```

The following query returns the start time setting of channel 1.

```
ARB:VOLT:TRAP:STAR:TIM? (@1)
ARB:SEQ:STEP:VOLT:TRAP:STAR:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:VOLTage:TRAPezoid:END:TIMe [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:VOLTage:TRAPezoid:TOP[:LEVel]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP[:LEVel]

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:TOP[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:TOP[:LEVel]?
[MIN|MAX,] (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP
[:LEVel] <voltage>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP
[:LEVel]? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the top level voltage of the trapezoid in volts.

Referenced to V in the Trapezoid diagram.

1

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level voltage for the trapezoid on channel 1.

```
ARB:VOLT:TRAP:TOP 5,(@1)
ARB:SEQ:STEP:VOLT:TRAP:TOP 5, 1,(@1)
```

The following query returns the top level voltage setting of channel 1.

```
ARB:VOLT:TRAP:TOP? (@1)
ARB:SEQ:STEP:VOLT:TRAP:TOP? 1,(@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:STARt[:LEVel] [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe

## [SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP:TIMe

### Syntax

```
[SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe <time>,
(@<chanlist>)
[SOURce:]ARB:VOLTage:TRAPezoid:TOP:TIMe? [MIN|MAX,]
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP
:TIMe <time>, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:TRAPezoid:TOP
:TIMe? [MIN|MAX,] <step#>, (@<chanlist>)
```

### Description

This command specifies the time of the top level of the trapezoid in seconds. Referenced to t in the Trapezoid diagram.

2

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 262.144 \| MIN \| MAX | 1 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed top level time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a top level time of 1 second on channel 1.

```
ARB:VOLT:TRAP:TOP:TIM 1,(@1)
ARB:SEQ:STEP:VOLT:TRAP:TOP:TIM 1, 1,(@1)
```

The following query returns the top level time setting of channel 1.

```
ARB:VOLT:TRAP:TOP:TIM? (@1)
ARB:SEQ:STEP:VOLT:TRAP:TOP:TIM? 1,(@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:TRAPezoid:RTIMe [SOURce:]ARB:VOLTage:TRAPezoid:FTIMe

## [SOURce:]ARB:VOLTage:UDEFined:BOSTep[:DATA]

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep[:DATA]

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:BOSTep[:DATA]
<Bool>{,<Bool>}, (@<chanlist>)
[SOURce:]ARB:VOLTage:UDEFined:BOSTep[:DATA]?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep
[:DATA] <Bool>{,<Bool>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep
[:DATA]? <step#>, (@<chanlist>)
```

### Description

This command specifies which user-defined ARB points or steps generate a trigger-out signal at the beginning of the step (BOSTep). A comma-delimited list of up to 511 steps may be programmed. The state is either ON (1) or OFF (0).

A trigger is only generated when the state is set to ON.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | 1 point with a value of OFF |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if no trigger is generated, and 1 if a trigger is generated. Multiple responses are separated by commas.

### Examples

The following command specifies that triggers will be generated at the beginning of each user-defined ARB step. The ARB contains 5 points or steps and is on channel 1.

```
ARB:VOLT:UDEF:BOST ON,ON,ON,ON,ON,(@1)
ARB:SEQ:STEP:VOLT:UDEF:BOST ON,ON,ON,ON,ON,1,(@1)
```

The following query returns the ARB step trigger settings of channel 1.

```
ARB:VOLT:UDEF:BOST? (@1)
ARB:SEQ:STEP:VOLT:UDEF:BOST? 1,(@1)
```

Typical Response:

```
1,1,1,1,1
```

## [SOURce:]ARB:VOLTage:UDEFined:BOSTep:POINts?

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep:POINts?

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:BOSTep:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:BOSTep
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of beginning-of-step points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of BOST points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of BOST points in a user-defined ARB for channel 1.

```
ARB:VOLT:UDEF:BOST:POIN? (@1)
ARB:SEQ:STEP:VOLT:UDEF:BOST:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:VOLTage:UDEFined:DWELl

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:DWELl <time>{,<time>},
(@<chanlist>)
[SOURce:]ARB:VOLTage:UDEFined:DWELl? (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl
<time>{,<time>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl?
<step#>, (@<chanlist>)
```

### Description

This command specifies the dwell time for each user-defined voltage ARB point. A comma-delimited list of up to 511 points may be programmed.

Dwell time is the time that the output will remain at a specific point. Dwell times can be programmed from 0 through 262.144 seconds with the following resolution: All Models except N678xA

| Range in seconds | Resolution |
|---|---|
| 0 - 0.262144 | 1 microsecond |
| 0 - 2.62144 | 10 microseconds |
| 0 - 26.2144 | 100 microseconds |
| 0 - 262.144 | 1 millisecond |
| Models N678xA only |  |

| Range in seconds | Resolution |
|---|---|
| 0 - 0.268435 | 1.024 microsecond |
| 0 - 2.68435 | 10.24 microseconds |
| 0 - 26.8435 | 102.4 microseconds |
| 0 - 268.435 | 1.024 millisecond |

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf | 0 - 262.144 (all except N678xA SMU) 0 - 268.435 (N678xA SMU only) | 1 point with a value of 0.001 |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

At the end of the dwell time, the output state of the unit depends upon the [SOURce:]ARB:TERMinate:LAST program settings.

The order in which the dwell values are entered determines the sequence when the list executes.

To create a valid user-defined ARB, the Voltage level, BOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpolated as having the same length as the maximum length list.

### Return Format

\<NR3\> The query command returns the programmed dwell time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a dwell list. The list contains 5 steps and is on channel 1.

```
ARB:VOLT:UDEF:DWEL 0.2,0.8,1.5,0.8,0.2,(@1)
ARB:SEQ:STEP:VOLT:UDEF:DWEL
0.2,0.8,1.5,0.8,0.2,1,(@1)
```

The following query returns the dwell list settings of channel 1.

```
ARB:VOLT:UDEF:DWEL? (@1)
ARB:SEQ:STEP:VOLT:UDEF:DWEL? 1,(@1)
```

Typical Response:

```
+2.000000E-01,+8.000000E-01,+1.500000E+00,+8.000000E-
01,+02.000000E-01
```

### See Also

[SOURce:]ARB:VOLTage:UDEFined:LEVel [SOURce:]ARB:VOLTage:UDEFined:BOST

## [SOURce:]ARB:VOLTage:UDEFined:DWELl:POINts?

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl:POINts?

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:DWELl:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:DWELl
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of dwell points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of dwell points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of dwell points in the user-defined ARB for channel 1.

```
ARB:VOLT:UDEF:DWEL:POIN? (@1)
ARB:SEQ:STEP:VOLT:UDEF:DWEL:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]ARB:VOLTage:UDEFined:LEVel

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:LEVel
<voltage>{,<voltage>}, (@<chanlist>)
[SOURce:]ARB:VOLTage:UDEFined:LEVel? (@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel
<voltage>{,<voltage>}, <step#>, (@<chanlist>)
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel?
<step#>, (@<chanlist>)
```

### Description

This command specifies the voltage setting for each user-defined ARB point in volts. A comma-delimited list of up to 511 points may be programmed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | 1 point set to the minimum programmable value |
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a user-defined voltage ARB. The ARB contains 5 points and is on channel 1.

```
ARB:VOLT:UDEF:LEV 5,4,3,2,1,(@1)
ARB:SEQ:STEP:VOLT:UDEF:LEV 5,4,3,2,1,1,(@1)
```

The following query returns the voltage ARB settings of channel 1.

```
ARB:VOLT:UDEF:LEV? (@1)
ARB:SEQ:STEP:VOLT:UDEF:LEV? 1,(@1)
```

Typical Response:

```
+5.000000E+00,+4.000000E+00,+3.000000E+00,
+2.000000E+00,+1.000000E+00
```

### See Also

[SOURce:]ARB:VOLTage:UDEFined:DWELl [SOURce:]ARB:VOLTage:UDEFined:BOST

## [SOURce:]ARB:VOLTage:UDEFined:LEVel:POINts?

## [SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel:POINts?

### Syntax

```
[SOURce:]ARB:VOLTage:UDEFined:LEVel:POINts?
(@<chanlist>)
For ARB sequence steps:
[SOURce:]ARB:SEQuence:STEP:VOLTage:UDEFined:LEVel
:POINts? <step#>, (@<chanlist>)
```

### Description

This query returns the number of voltage points in the user-defined ARB, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<step#\> | NR1 | 1 - 100 | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of voltage points in the user-defined ARB. Multiple responses are separated by commas.

### Example

The following query returns the number of voltage points in a user-defined ARB for channel 1.

```
ARB:VOLT:UDEF:LEV:POIN? (@1)
ARB:SEQ:STEP:VOLT:UDEF:LEV:POIN? 1,(@1)
```

Typical Response:

```
+1
```

## [SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude]
current
< >, (@<chanlist>)
[SOURce:]CURRent[:LEVel][:IMMediate][:AMPLitude]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the immediate current level of the specified output channel. Units are in amperes. The immediate level is the output current setting.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | 80 mA |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with [SOURce:]CURRent:RANGe.

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the output current to 3 A on channels 1 and 2.

```
CURR 3,(@1,2)
```

The following query returns the programmed current level on channels 1 and 2.

```
CURR? (@1,2)
```

Typical Response:

```
+3.000000E+00,+3.000000E+00
```

### See Also

[SOURce:]CURRent:RANGe

## [SOURce:]CURRent[:LEVel]:TRIGgered[:AMPLitude]

### Syntax

```
[SOURce:]CURRent[:LEVel]:TRIGgered[:AMPLitude]
current
< >, (@<chanlist>)
[SOURce:]CURRent[:LEVel]:TRIGgered[:AMPLitude]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the triggered current level of the specified output channel. Units are in amperes. The triggered level is a stored value that is transferred to the output when an output Step is triggered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the current rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with [SOURce:]CURRent:RANGe.

### Return Format

\<NR3\> The query command returns the programmed triggered level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the triggered current to 2 A on channels 1 and 2.

```
CURR:TRIG 2,(@1,2)
```

The following query returns the programmed triggered level on channels 1 and 2.

```
CURR:TRIG? (@1,2)
```

Typical Response:

```
+2.000000E+00,+2.000000E+00
```

### See Also

[SOURce:]CURRent[:LEVel][:IMMediate] [SOURce:]CURRent:MODE

TRIGger:TRANsient[:IMMediate]

## [SOURce:]CURRent:LIMit[:POSitive][:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]CURRent:LIMit[:POSitive][:IMMediate]
[:AMPLitude] <limit>, (@<chanlist>)
[SOURce:]CURRent:LIMit[:POSitive][:IMMediate]
[:AMPLitude]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the positive current limit of the specified output channel. Units are in amperes. If [SOURce:]CURRent:LIMit:COUPle is enabled, this command also sets the value of the negative current limit.

Refer to chapter 6 in the N6705 User's Guide under "Voltage Priority" for more information about current limit operation.

> **NOTE** This command only applies to models N678xA SMU and N6783A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<limit\> | NRf+ | 0 - 3.06 \| MIN \| MAX | MAX (of selected range) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the current limit in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the current limit to 3 A on channels 1 and 2.

```
CURR:LIM 3,(@1,2)
```

The following query returns the current limit on channels 1 and 2.

```
CURR:LIM? (@1,2)
```

Typical Response:

```
+3.000000E+00,+3.000000E+00
```

### See Also

[SOURce:]CURRent:LIMit COUPle [SOURce:]CURRent:LIMit:NEGative

## [SOURce:]CURRent:LIMit:COUPle

### Syntax

```
[SOURce:]CURRent:LIMit:COUPle <Bool>, (@<chanlist>)
[SOURce:]CURRent:LIMit:COUPle? (@<chanlist>)
```

### Description

This command sets the current limit tracking state. The enabled state is On (1); the disabled state is Off (0). If limit tracking is enabled, the negative current limit tracks the positive current limit setting. The [SOURce:]CURRent:LIMit command sets the value of the positive and negative current limits.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 1 if the current limit coupling is enabled, and 0 if the current limit coupling is disabled.

### Examples

The following command sets the current limit coupling on for channel 4.

```
CURR:LIM:COUP ON,(@4)
```

The following query returns the current limit coupling state for channel 1.

```
CURR:LIM:COUP? (@1)
```

Typical Response:

```
0
```

### See Also

[SOURce:]CURRent:LIMit [SOURce:]CURRent:LIMit:NEGative

## [SOURce:]CURRent:LIMit:NEGative[:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]CURRent:LIMit:NEGative[:IMMediate]
[:AMPLitude] <limit>, (@<chanlist>)
[SOURce:]CURRent:LIMit:NEGative[:IMMediate]
[:AMPLitude]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the negative current limit of the specified output channel. Units are in amperes. If [SOURce:]CURRent:LIMit:COUPle is enabled, this command also sets the value of the positive current limit.

Refer to chapter 6 in the N6705 User's Guide under "Voltage Priority" for more information about current limit operation.

> **NOTE** This command only applies to models N678xA SMU and N6783A-BAT.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<limit\> | NRf+ | -3.06 to 0 \| MIN \| MAX (N678xA SMU) -2 to 0 \| MIN \| MAX (N6783A-BAT) | MIN (of selected range) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

MIN refers to the most negative value of the range. MAX refers to the least negative value of the range.

### Return Format

\<NR3\> The query command returns the negative current limit in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the negative current limit to -3 A on channels 1 and 2.

```
CURR:LIM:NEG -3,(@1,2)
```

The following query returns the negative current limit on channels 1 and 2.

```
CURR:LIM:NEG? (@1,2)
```

Typical Response:

```
-3.000000E+00,-3.000000E+00
```

### See Also

[SOURce:]CURRent:LIMit:COUPle [SOURce:]CURRent:LIMit

## [SOURce:]CURRent:MODE

### Syntax

```
[SOURce:]CURRent:MODE <mode>, (@<chanlist>)
[SOURce:]CURRent:MODE? (@<chanlist>)
```

### Description

This command determines what happens to the output current when the transient system is initiated and triggered.

FIXed Nothing happens. The output current remains at the immediate value.

STEP The output goes to the triggered level when a trigger occurs.

LIST The output follows the list values when a trigger occurs.

ARB The output follows the arbitrary waveform values when a trigger occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | FIXed \| STEP \| LIST \| ARB | FIXed |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the current mode for each channel specified.

Multiple responses are separated by commas.

### Examples

The following command sets the current mode of channel 4.

```
CURR:MODE STEP,(@4)
```

The following query returns the current mode of channel 1.

```
CURR:MODE? (@1)
```

Typical Response:

```
FIX
```

### See Also

[SOURce:]VOLTage:MODE INITiate[:IMMediate]:TRANsient

TRIGger:TRANsient[:IMMediate]

## [SOURce:]CURRent:PROTection:DELay[:TIME]

### Syntax

```
[SOURce:]CURRent:PROTection:DELay[:TIME] <time>,
(@<chanlist>)
[SOURce:]CURRent:PROTection:DELay[:TIME]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the over-current protection delay. The over-current protection function will not be triggered on the specified output channel during the delay time. After the delay time has expired, the over-current protection function will be active. This prevents momentary changes in output status from triggering the over-current protection function.

Programmed values can range from 0 to 255 milliseconds in increments of 1 millisecond.

The operation of over-current protection is affected by the setting of the current protection delay start event, which is specified by [SOURce:]CURRent:PROTection:DELay:STARt.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf+ | 0 - 0.255 \| MIN \| MAX | 20 ms |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is the same as OUTPut:PROTection:DELay.

### Return Format

\<NR3\> The query command returns the programmed delay time. The reading is in the form +n.nnnnnnE+nn.

### Example

The following command sets a current protection delay of 0.5 seconds for channel 2.

```
CURR:PROT:DEL 0.5,(@2)
```

The following query returns the maximum allowable current protection delay of channel 1.

```
CURR:PROT:DEL? MAX,(@1)
```

Typical Response:

```
+2.550000E-01
```

### See Also

[SOURce:]CURRent:PROTection:DELay [SOURce:]CURRent:PROTection:DELay:STARt [SOURce:]CURRent:PROTection:STATe

OUTPut:PROTection:CLEar

## [SOURce:]CURRent:PROTection:DELay:STARt

### Syntax

[SOURce:]CURRent:PROTection:DELay:STARt \<mode\>, (@\<chanlist\>)

[SOURce:]CURRent:PROTection:DELay:STARt? (@\<chanlist\>)

### Description

This command specifies the conditions under which the over-current protection delay timer starts: SCHange Transitions into constant current mode are automatically ignored during a programmed settings change in voltage, current, or output state. At the end of the settings change, the delay timer is started, allowing for additional protection delay time. There is no protection delay outside of these time windows. This is how the OUTPut:PROTection:DELay command functioned prior to the availability of the CCTRans function.

CCTRans The over-current protection delay timer is started by any transition of the output into constant current mode.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | SCHange \| CCTRans | SCHange |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns SCH or CCTR.

### Example

The following selects CCTRans as the current protection delay mode.

```
CURR:PROT:DEL:STAR CCTR,(@1)
```

The following query returns the current protection delay mode.

```
CURR:PROT:DEL:STAR? (@2)
```

Typical Response:

```
SCH
```

### See Also

[SOURce:]CURRent:PROTection:DELay [SOURce:]CURRent:PROTection:STATe

## [SOURce:]CURRent:PROTection:STATe

### Syntax

```
[SOURce:]CURRent:PROTection:STATe <Bool>,
(@<chanlist>)
[SOURce:]CURRent:PROTection:STATe? (@<chanlist>)
```

### Description

This command enables or disables the over-current protection (OCP) function. The enabled state is On (1); the disabled state is Off (0). If the over-current protection function is enabled and the output goes into constant current operation, the output is disabled and the Questionable Condition status register OCP bit is set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The current limit setting determines when the output channel goes into constant current operation.

An over-current condition can be cleared with OUTPut:PROTection:CLEar after the cause of the condition is removed.

### Return Format

\<NR1\> The query command returns 0 if the current protection state is OFF, and 1 if the current protection state is ON.

### Examples

The following command sets the current protection state of channel 4.

```
CURR:PROT:STAT ON,(@4)
```

The following query returns the current protection state of channel 1.

```
CURR:PROT:STAT? (@1)
```

Typical Response:

```
0
```

### See Also

OUTPut:PROTection:CLEar

## [SOURce:]CURRent:RANGe

### Syntax

[SOURce:]CURRent:RANGe \<range\>, (@\<chanlist\>)

[SOURce:]CURRent:RANGe? [MIN|MAX,] (@\<chanlist\>)

### Description

This command sets the output current range on models that have multiple ranges. The value that you enter must be the highest value in amperes that you expect to source. The instrument selects the range with the best resolution for the value entered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with the [SOURce:]CURRent command. This means that if a range command is sent that places an output on a range with a lower maximum current than the present current level, an error is generated. This also occurs if a current level is programmed with a value too large for the present range.

These types of errors can be avoided by sending the both level and range commands in the same SCPI message. When the range and setting information is received as a set, no range/setting conflict occurs.

If programming a range value causes a range change to occur while the output is enabled, the output will be temporarily disabled while the range switch occurs. The transition from on-to-off and then from off-to-on will also be delayed by the settings of OUTPut:DELay:FALL and OUTPut:DELay:RISE.

### Return Format

\<NR3\> The query command returns the maximum current that can be output on the range that is presently set. The current level is in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the output current range to 1 A on channels 1 and 2.

```
CURR:RANG 1,(@1,2)
```

The following query returns the programmed current range on channels 1 and 2.

```
CURR:RANG? (@1,2)
```

Typical Response:

```
+1.000000E+00,+1.000000E+00
```

### See Also

[SOURce:]CURRent[:LEVel][:IMMediate]

## [SOURce:]CURRent:SLEW[:IMMediate]

### Syntax

```
[SOURce:]CURRent:SLEW[:IMMediate] <slew>|INFinity,
(@<chanlist>)
[SOURce:]CURRent:SLEW[:IMMediate]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the current slew rate in amps per second. The slew rate setting affects all programmed current changes, including those due to the output state turning on or off. The slew rate can be set to any value between 0 and 9.9E+37. For very large values, the slew rate will be limited by the analog performance of the output circuit. The keywords MAX or INFinity set the slew rate to maximum.

The query returns the value that was sent, unless the value was less than the minimum slew rate, in which case the minimum value is returned. The LSB weight of the 24-bit register can be queried using CURRent:SLEW?

MIN. The exact value varies slightly according to the current calibration.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slew\> | NRf+ | 0 - 9.9E+37 \| MIN \| MAX \| INFinity | 9.9E+37 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed slew rate in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas. If a slew rate of 9.9E37 is returned, it means that the maximum or fastest slew rate has been set.

### Examples

The following command sets the slew rate to 1 amp per second on channel 1.

```
CURR:SLEW 1,(@1)
```

The following query returns the programmed slew rate on channel 1.

```
CURR:SLEW? (@1)
```

Typical Response:

```
+1.000000E+00
```

### See Also

[SOURce:]VOLTage:SLEW [SOURce:]CURRent:SLEW:MAX

## [SOURce:]CURRent:SLEW:MAXimum

### Syntax

```
[SOURce:]CURRent:SLEW:MAXimum <Bool>, (@<chanlist>)
[SOURce:]CURRent:SLEW:MAXimum? (@<chanlist>)
```

### Description

This command sets the current slew rate maximum override. When enabled (ON), the power module's slew rate is set to its maximum value.

When disabled (OFF), the power module's slew rate is set to the immediate value set by the [SOURce:]CURRent:SLEW command.

[SOURce:]CURRent:SLEW:MAX does not affect the [SOURce:]CURRent:SLEW setting.

Use [SOURce:]CURRent:SLEW? MAX to query the maximum slew rate that was set.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The [SOURce:]CURRent:SLEW:MAX command is coupled to the [SOURce:]CURRent:SLEW command. If [SOURce:]CURRent:SLEW sets the rate to MAX or INFinity, [SOURce:]CURRent:SLEW:MAX is enabled. If the slew rate is set to any other value, [SOURce:]CURRent:SLEW:MAX is disabled.

### Return Format

\<NR1\> The query command returns 0 if the slew rate override is disabled, and 1 if the slew rate override is enabled.

### Examples

The following command enables the slew rate maximum override on channel 1.

```
CURR:SLEW:MAX ON,(@1)
```

The following query returns the state of the slew rate override on channel 1.

```
CURR:SLEW:MAX? (@1)
```

Typical Response:

```
1
```

### See Also

[SOURce:]CURRent:SLEW [SOURce:]VOLTage:SLEW:MAXimum

## [SOURce:]DIGital:INPut:DATA?

### Syntax

```
[SOURce:]DIGital:INPut:DATA?
```

### Description

This query reads the state of the digital control port.

### Return Format

\<NR1\> The query returns the binary-weighted value of the state of pins 1 through 7 in bits 0 through 6 respectively.

### Example

The following query returns the state of the digital control port pins.

```
DIG:INP:DATA?
```

Typical Response:

```
+0
```

### See Also

[SOURce:]DIGital:OUTput:DATA

## [SOURce:]DIGital:OUTPut:DATA

### Syntax

```
[SOURce:]DIGital:OUTPut:DATA <value>
[SOURce:]DIGital:OUTPut:DATA?
```

### Description

This command sets the output data on the digital control port when that port is configured for Digital I/O operation. The port has seven signal pins and a digital ground pin. In the binary-weighted value that is written to the port, the pins are controlled according to the following bit assignments: Pin Bit Number Decimal Value 1 0 1 2 1 2 3 2 4 4 3 8 5 4 16 6 5 32 7 6 64

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | 0 - 127 | 0 |

### Return Format

\<NR1\> The query returns the last programmed value of the bits. To read the actual state of the pin, use [SOURce:]DIGital:INPut:DATA?

### Example

The following command programs pins 1, 3, and 5 on. (bit 0 = 1; bit 2 = 4; bit 4 = 16) (1 + 4 + 16 = 21)

```
DIG:OUTP:DATA 21
```

The following query returns the state of the digital control port pins.

```
DIG:OUTP:DATA?
```

Typical Response:

```
+21
```

### See Also

[SOURce:]DIGital:INPut:DATA?

## [SOURce:]DIGital:PIN\<1-7\>:FUNCtion

### Syntax

```
[SOURce:]DIGital:PIN<1-7>:FUNCtion <function>
[SOURce:]DIGital:PIN<1-7>:FUNCtion?
```

### Description

This command sets the functions of the digital port pins. The pin functions are saved in non-volatile memory.

DIO The pin is a general-purpose ground-referenced digital input/output.

The output can be set with [SOURce:]DIGital:OUTPut:DATA.

DINPut The pin is in digital input-only mode. The digital output data of the corresponding pin is ignored.

TOUTput The pin is configured as a trigger output. When configured as a trigger output, the pin will only generate output triggers if the Step or List transient system has been configured to generated trigger signals.

See: [SOURce:]STEP:TOUTput, [SOURce:]LIST:TOUTput:BOSTep, and [SOURce:]LIST:TOUTput:EOSTep

TINPut The pin is configured as a trigger input. When configured as a trigger input, the pin can be selected as the source for measurement and transient trigger signals. See TRIGger:ACQuire:SOURce and TRIGger:TRANsient:SOURce

FAULt Applies only to pin 1. Setting FAULt means that pin 1 functions as an isolated fault output. The fault signal is true when any output is in a protected state (from OC, OV, OT, INH, PF, or CP+ on some models).

Note also that Pin 2 serves as the isolated common for pin 1. When pin 1 is set to the FAULt function, the instrument ignores any commands to program pin 2. Queries of pin 2 will return FAULt. If pin 1 is changed from FAULt to another function, pin 2 is set to DINPut.

INHibit Applies only to pin 3. When pin 3 is configured as an inhibit input, a true signal at the pin will disable all output channels.

ONCouple Applies only to pins 4 -7. When configured as an On control, the pin will synchronize the output On state between mainframes. Only one pin can be configured as an On control. The pin will function as both an input and an output. The polarity of the pin is fixed and cannot be programmed.

OFFCouple Applies only to pins 4-7. When configured as an Off control, the pin will synchronize the output Off state between mainframes. Only one pin can be configured as an Off control. The pin will function as both an input and an output. The polarity of the pin is fixed and cannot be programmed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<function\> | CPD | DIO \| DINPut \| TOUTput \| TINPut \| FAULt \| INHibit \| ONCouple \| OFFCouple | Required parameter |

### Return Format

\<CRD\> The query command returns DIO, DINP, TOUT, TINP, FAUL, INH, ONC, or OFFC.

### Example

The following command sets pin 1 to Fault mode.

```
DIG:PIN1:FUNC FAUL
```

The following query returns the setting of pin 7.

```
DIG:PIN7:FUNC?
```

Typical Response:

```
DIO
```

### See Also

[SOURce:]DIGital:PIN\<1-7\>:POLarity

## [SOURce:]DIGital:PIN\<1-7\>:POLarity

### Syntax

```
[SOURce:]DIGital:PIN<1-7>:POLarity <polarity>
[SOURce:]DIGital:PIN<1-7>:POLarity?
```

### Description

This command sets the polarity of the digital port pins. The pin polarities are saved in non-volatile memory.

POSitive Setting a polarity to POSitive means that a logical true signal is a voltage high at the pin. For trigger inputs and outputs, POSitive means a rising edge.

NEGative Setting the polarity NEGative means that a logical true signal is a voltage low at the pin. For trigger inputs and outputs, NEGative means a falling edge.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<polarity\> | CPD | POSitive \| NEGative | Required parameter |

### Return Format

\<CRD\> The query command returns POS or NEG.

### Example

The following command sets pin 1 to negative polarity.

```
DIG:PIN1:POL NEGative
```

The following query returns the polarity of pin 7.

```
DIG:PIN7:POL?
```

Typical Response:

```
POS
```

### See Also

[SOURce:]DIGital:PIN\<1-7\>:FUNCtion

## [SOURce:]DIGital:TOUTput:BUS[:ENABle]

### Syntax

```
[SOURce:]DIGital:TOUTput:BUS[:ENABle] <Bool>
[SOURce:]DIGital:TOUTput:BUS[:ENABle]?
```

### Description

This command allows a BUS trigger to be sent to any digital port pin that has been configured as a trigger output. The state is either ON (1) or OFF (0). A trigger is generated when the state is True (ON). A BUS trigger is generated using the \*TRG command.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |

### Remarks

Pins 1 – 7 must be configured as trigger outputs before they can generate a trigger signal. See [SOURce:]DIGital:PIN\<1-7\>:FUNCtion and [SOURce:]DIGital:PIN\<1-7\>:POLarity.

### Return Format

\<NR1\> The query command returns 0 (OFF) if the trigger signal will NOT be generated when a BUS trigger command occurs, and 1(ON) if a trigger signal will be generated when a BUS trigger command occurs.

### Examples

The following command enables BUS-generated trigger signals on the digital pins.

```
DIG:TOUT:BUS ON
```

The following query returns the state BUS-generated trigger signals on the digital pins.

```
DIG:TOUT:BUS?
```

Typical Response:

```
0
```

### See Also

[SOURce:]DIGital:PIN\<1-7\>:FUNCtion [SOURce:]DIGital:PIN\<1-7\>:POLarity

## [SOURce:]EMULation

### Syntax

```
[SOURce:]EMULation <type>, (@<chanlist>)
[SOURce:]EMULation? (@<chanlist>)
```

### Description

This command specifies the emulation type for models N678xA. Refer to Emulation Mode Settings for information on the default parameter settings for each of the following emulation modes.

PS4Q Four-quadrant bipolar power supply (model N6784A only). Power supply operation is available in all four output quadrants with no restrictions.

PS2Q Two-quadrant bipolar power supply. In this mode operation is restricted to two quadrants (+V/+I and +V/- I).

PS1Q Unipolar, one-quadrant power supply. This mode emulates a typical one quadrant or unipolar power supply with limited down-programming.

BATTery Two-quadrant battery emulator. A battery emulator imitates a battery’s charging and discharging functions.

CHARger One-quadrant battery charger. A battery charger imitates a battery charger; it cannot sink current like a battery.

CCLoad One-quadrant load. This mode emulates a constant-current load.

CVLoad One-quadrant load. This mode emulates a constant-voltage load.

VMETer Voltage measurement. The voltage measurement emulates a voltmeter.

AMETer Current measurement. The current measurement emulates a zero-burden ammeter.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<type\> | CPD | PS4Q \| PS2Q \| PS1Q \| BATTery \| CHARger \| CCLoad \| CVLoad \| VMETer \| AMETer | PS4Q (N6784A) PS2Q (N6781A, N6782A, N6785A, N6786A) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the emulation type for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets LOAD as the emulation type for channel 4.

```
EMUL LOAD,(@4)
```

The following query returns the emulation type of channel 4.

```
EMUL? (@4)
```

Typical Response:

```
PS4Q
```

### See Also

[SOURce:]FUNCtion

## [SOURce:]FUNCtion

### Syntax

```
[SOURce:]FUNCtion <mode>, (@<chanlist>)
[SOURce:]FUNCtion? (@<chanlist>)
```

### Description

This command selects whether the output regulation on models N678xA is in voltage priority or current priority mode. In voltage priority mode the output is controlled by a bi-polar constant voltage feedback loop, which maintains the output voltage at its positive or negative programmed setting. In current priority mode the output is controlled by a bi-polar constant current feedback loop, which maintains the output sourcing or sinking current at its programmed setting. Refer to chapter 6 in the N6705 User's Guide for more information about priority mode operation.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | CURRent \| VOLTage | VOLTage |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the priority mode setting for each channel specified. Multiple responses are separated by commas.

### Examples

The following command selects voltage priority mode on channel 3.

```
FUNC VOLT, (@3)
```

The following query returns the mode selected on channel 1.

```
FUNC? (@1)
```

Typical Response:

```
"VOLT"
```

### See Also

[SOURce:]EMULation

## [SOURce:]LIST:COUNt

### Syntax

```
[SOURce:]LIST:COUNt <count>|INFinity, (@<chanlist>)
[SOURce:]LIST:COUNt? [MIN|MAX|INFinity,]
(@<chanlist>)
```

### Description

This command sets the number of times that the list is executed before it is completed. The list count range is 1 through 256.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<count\> | NRf+ | 1 - 256 \| MIN \| MAX \| INFinity | 1 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Use the INFinity parameter to execute a list continuously.

Use ABORt:TRANsient to stop the list at any time. When the list is aborted, the output returns to the settings that were in effect before the list started.

### Return Format

\<NR1\> The query command returns the list count for each channel specified.

Multiple responses are separated by commas. If a repeat count of 9.9E37 is returned, it means the list is set to repeat continuously.

### Examples

The following command sets the list count to 10 on channel 1.

```
LIST:COUN 10,(@1)
```

The following query returns the list count of channel 1.

```
LIST:COUN? (@1)
```

Typical Response:

```
+10
```

## [SOURce:]LIST:CURRent[:LEVel]

### Syntax

```
[SOURce:]LIST:CURRent[:LEVel] <current>{,<current>},
(@<chanlist>)
[SOURce:]LIST:CURRent[:LEVel]? (@<chanlist>)
```

### Description

This command specifies the current setting for each list step in amperes.

A comma-delimited list of up to 512 steps may be programmed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<current\> | NRf | 0 – maximum The maximum value is dependent on the current rating of the power module. | 1 step set to the min-imum programmable value |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The order in which the current values are entered determines the sequence when the list executes.

To create a valid list, the Voltage, Current, BOST, EOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpreted as having the same length as the list with the maximum length.

This command overwrites any previously programmed current list; it does not append to the previous list.

### Return Format

\<NR3\> The query command returns the programmed current level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a current list. The list contains 5 steps and is on channel 1.

```
LIST:CURR 5,4,3,2,1,(@1)
```

The following query returns the current list settings of channel 1.

```
LIST:CURR? (@1)
```

Typical Response:

```
+5.000000E+00,+4.000000E+00,+3.000000E+00,+2.000000E
+00,+1.000000E+00
```

### See Also

[SOURce:]LIST:DWELl [SOURce:]LIST:VOLTage[:LEVel]

## [SOURce:]LIST:CURRent:POINts?

### Syntax

```
[SOURce:]LIST:CURRent:POINts? (@<chanlist>)
```

### Description

This query returns the number of points (steps) in the current list, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of points in the current list. Multiple responses are separated by commas.

### Example

The following query returns the number of points in a current list for channel 1.

```
LIST:CURR:POIN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]LIST:DWELl

### Syntax

```
[SOURce:]LIST:DWELl <time>{,<time>}, (@<chanlist>)
[SOURce:]LIST:DWELl? (@<chanlist>)
```

### Description

This command specifies the dwell time for each list step. A comma-delimited list of up to 512 steps may be programmed. Dwell time is the time that the output will remain at a specific step. Dwell times can be programmed from 0 through 262.144 seconds with the following resolution:

All Models except N678xA

| Range in seconds | Resolution |
|---|---|
| 0 - 0.262144 | 1 microsecond |
| 0 - 2.62144 | 10 microseconds |
| 0 - 26.2144 | 100 microseconds |
| 0 - 262.144 | 1 millisecond |
| Models | N678xA only |

| Range in seconds | Resolution |
|---|---|
| 0 - 0.268435 | 1.024 microsecond |
| 0 – 2.68435 | 10.24 microseconds |
| 0 – 26.8435 | 102.4 microseconds |
| 0 – 268.435 | 1.024 millisecond |

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<time\> | NRf | 0 - 262.144 (all except N678xA SMU) 0 - 268.435 (N678xA SMU only) | 1 step with a value of 0.001 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

At the end of the dwell time, the output state of the unit depends upon the [SOURce:]LIST:STEP program settings.

The order in which the dwell values are entered determines the sequence when the list executes.

To create a valid list, the Voltage, Current, BOST, EOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpreted as having the same length as the list with the maximum length.

This command overwrites any previously programmed dwell list; it does not append to the previous list.

### Return Format

\<NR3\> The query command returns the programmed dwell time in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a dwell list. The list contains 5 steps and is on channel 1.

```
LIST:DWEL 0.2,0.8,1.5,0.8,0.2,(@1)
```

The following query returns the dwell list settings of channel 1.

```
LIST:DWEL? (@1)
```

Typical Response:

```
+2.000000E-01,+8.000000E-01,+1.500000E+00,+8.000000E-
01,+02.000000E-01
```

### See Also

[SOURce:]LIST:CURRent[:LEVel] [SOURce:]LIST:VOLTage[:LEVel]

## [SOURce:]LIST:DWELl:POINts?

### Syntax

```
[SOURce:]LIST:DWELl:POINts? (@<chanlist>)
```

### Description

This query returns the number of points (steps) in the dwell list, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of points in the dwell list. Multiple responses are separated by commas.

### Example

The following query returns the number of points in a dwell list for channel 1.

```
LIST:DWEL:POIN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]LIST:STEP

### Syntax

```
[SOURce:]LIST:STEP <response>, (@<chanlist>)
[SOURce:]LIST:STEP? (@<chanlist>)
```

### Description

This command specifies how the list responds to triggers.

ONCE Causes the output to remain at the present step until a trigger advances it to the next step. Triggers that arrive during the dwell time are ignored.

AUTO Causes the output to automatically advance to each step, after the receipt of an initial starting trigger. The steps are paced by the dwell list. As each dwell time elapses, the next step is immediately output.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<response\> | CPD | ONCE \| AUTO | AUTO |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the list step setting. Multiple responses are separated by commas.

### Examples

The following command sets the list step setting of channel 1 to ONCE, causing the list steps to be paced by trigger signals.

```
LIST:STEP ONCE,(@1)
```

The following query returns the list step setting of channel 1.

```
VOLT:MODE? (@4)
```

Typical Response:

```
ONCE
```

### See Also

[SOURce:]LIST:TERMinate:LAST

## [SOURce:]LIST:TERMinate:LAST

### Syntax

```
[SOURce:]LIST:TERMinate:LAST <Bool>, (@<chanlist>)
[SOURce:]LIST:TERMinate:LAST? (@<chanlist>)
```

### Description

This command determines the output value when the list terminates. The state is either ON (1) or OFF (0).

When ON, the output voltage or current remains at the value of the last list step. The value of the last voltage or current list step becomes the IMMediate value when the list completes.

When OFF, and also when the list is aborted, the output returns to the settings that were in effect before the list started.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the output returns to the settings that were in effect before the list started, and 1 if the output voltage or current remains at the value of the last list step.

### Examples

The following command sets the list to terminate with the output voltage or current remaining at the value of the last list step on channel 2.

```
LIST:TERM:LAST ON,(@2)
```

The following query returns the list terminate setting of channel 1.

```
LIST:TERM:LAST? (@1)
```

Typical Response:

```
0
```

### See Also

[SOURce:]LIST:STEP

## [SOURce:]LIST:TOUTput:BOSTep[:DATA]

### Syntax

```
[SOURce:]LIST:TOUTput:BOSTep[:DATA] <Bool>{,<Bool>},
(@<chanlist>)
[SOURce:]LIST:TOUTput:BOSTep[:DATA]? (@<chanlist>)
```

### Description

This command specifies which list steps generate a trigger signal at the beginning of the step (BOSTep). A comma-delimited list of up to 512 steps may be programmed. The state is either ON (1) or OFF (0).

A trigger is only generated when the state is set to ON. The trigger signal can be used as a trigger source for measurements and transients of other channels, and for digital port pins configured as trigger outputs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | 1 step with a value of OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The order in which the BOSTep values are entered determines the sequence when the list executes.

To create a valid list, the Voltage, Current, BOST, EOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpreted as having the same length as the list with the maximum length.

This command overwrites any previously programmed BOSTep list; it does not append to the previous list.

### Return Format

\<NR1\> The query command returns 0 if no trigger is generated, and 1 if a trigger is generated. Multiple responses are separated by commas.

### Examples

The following command specifies that triggers will be generated at the beginning of each list step. The list contains 5 steps and is on channel 1.

```
LIST:TOUT:BOST ON,ON,ON,ON,ON,(@1)
```

The following query returns the list step trigger settings of channel 1.

```
LIST:TOUT:BOST? (@1)
```

Typical Response:

```
1,1,1,1,1
```

### See Also

[SOURce:]LIST:TOUTput:EOSTep[:DATA]

## [SOURce:]LIST:TOUTput:BOST:POINts?

### Syntax

```
[SOURce:]LIST:TOUTput:BOST:POINts? (@<chanlist>)
```

### Description

This query returns the number of points (steps) in the beginning of the step trigger list (BOSTep), not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of points in the BOSTep list. Multiple responses are separated by commas.

### Example

The following query returns the number of points in a BOSTep list for channel 1.

```
LIST:TOUT:BOST:POIN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]LIST:TOUTput:EOSTep[:DATA]

### Syntax

```
[SOURce:]LIST:TOUTput:EOSTep[:DATA] <Bool>{,<Bool>},
(@<chanlist>)
[SOURce:]LIST:TOUTput:EOSTep[:DATA]? (@<chanlist>)
```

### Description

This command specifies which list steps generate a trigger signal at the end of the step (EOSTep). A comma-delimited list of up to 512 steps may be programmed. The state is either ON (1) or OFF (0).

A trigger is only generated when the state is set to ON. The trigger signal can be used as a trigger source for measurements and transients of other channels, and for digital port pins configured as trigger outputs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | 1 step with a value of OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The order in which the EOSTep values are entered determines the sequence when the list executes.

To create a valid list, the Voltage, Current, BOST, EOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpreted as having the same length as the list with the maximum length.

This command overwrites any previously programmed EOSTep list; it does not append to the previous list.

### Return Format

\<NR1\> The query command returns 0 if no trigger is generated, and 1 if a trigger is generated. Multiple responses are separated by commas.

### Examples

The following command specifies that triggers will be generated at the end of each list step. The list contains 5 steps and is on channel 1.

```
LIST:TOUT:EOST ON,ON,ON,ON,ON,(@1)
```

The following query returns the list step trigger settings of channel 1.

```
LIST:TOUT:EOST? (@1)
```

Typical Response:

```
1,1,1,1,1
```

### See Also

[SOURce:]LIST:TOUTput:BOSTep[:DATA]

## [SOURce:]LIST:TOUTput:EOST:POINts?

### Syntax

```
[SOURce:]LIST:TOUTput:EOST:POINts? (@<chanlist>)
```

### Description

This query returns the number of points (steps) in the end of the step trigger list (EOSTep), not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of points in the EOSTep list. Multiple responses are separated by commas.

### Example

The following query returns the number of points in a EOSTep list for channel 1.

```
LIST:TOUT:EOST:POIN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]LIST:VOLTage[:LEVel]

### Syntax

```
[SOURce:]LIST:VOLTage[:LEVel] <voltage>{,<voltage>},
(@<chanlist>)
[SOURce:]LIST:VOLTage[:LEVel]? (@<chanlist>)
```

### Description

This command specifies the voltage setting for each list step in volts. A comma-delimited list of up to 512 steps may be programmed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf | 0 – maximum The maximum value is dependent on the voltage rating of the power module. | 1 step set to the min-imum programmable value |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The order in which the voltage values are entered determines the sequence when the list executes.

To create a valid list, the Voltage, Current, BOST, EOST, and Dwell lists must either all be the same length, or have a length of 1, which is interpreted as having the same length as the list with the maximum length.

This command overwrites any previously programmed voltage list; it does not append to the previous list.

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn. Multiple responses are separated by commas.

### Examples

The following command programs a voltage list. The list contains 5 steps and is on channel 1.

```
LIST:VOLT 10,20,30,40,50,(@1)
```

The following query returns the voltage list settings of channel 1.

```
LIST:VOLT? (@1)
```

Typical Response:

```
+1.000000E+01,+2.000000E+01,+3.000000E+01,+4.000000E
+01,+5.000000E+01
```

### See Also

[SOURce:]LIST:DWELl [SOURce:]LIST:CURRent[:LEVel]

## [SOURce:]LIST:VOLTage:POINts?

### Syntax

```
[SOURce:]LIST:VOLTage:POINts? (@<chanlist>)
```

### Description

This query returns the number of points (steps) in the voltage list, not the point values.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The number of points in the voltage list. Multiple responses are separated by commas.

### Example

The following query returns the number of points in a voltage list for channel 1.

```
LIST:VOLT:POIN? (@1)
```

Typical Response:

```
+1
```

## [SOURce:]POWer:LIMit

### Syntax

```
[SOURce:]POWer:LIMit <power>, (@<chanlist>)
[SOURce:]POWer:LIMit? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the power limit on output channels. Units are in Watts.

For the majority of Keysight N6705 configurations, full power is available from all installed power modules. However, it is possible to configure a mainframe in which the combined ratings of the power modules exceed the power rating of the mainframe.

For these instrument configurations, the power allocation lets you programmatically limit the output power of some of the power modules so that the combined output power does not exceed the power rating of the mainframe. Refer to Appendix C in the User’s Guide for more information.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<power\> | NRf+ | 0 - maximum \| MIN \| MAX | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Setting a power limit of MAX on an output channel sets the output channel to its maximum rated power limit. If the power limit is left at the maximum rating, then the power module will not enable its power limit function.

Querying MAX on an output channel returns the maximum rated power limit.

### Return Format

\<NR3\> The query command returns the programmed power level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the power limit to 75 W on channels 1 and 2.

```
POW:LIM 75,(@1,2)
```

The following query returns the programmed power limit on channels 1 and 2.

```
POW:LIM? (@1,2)
```

Typical Response:

```
+7.500000E+01,+7.500000E+01
```

## [SOURce:]RESistance[:LEVel][:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]RESistance[:LEVel][:IMMediate][:AMPLitude]
resistance
< >, (@<chanlist>)
[SOURce:]RESistance[:LEVel][:IMMediate][:AMPLitude]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the resistance level of the specified output channel.

Units are in ohms. Resistance programming is enabled with [SOURce:]RESistance:STATe.

> **NOTE** This command only applies to models N6781A and N6785A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<resistance\> | NRf+ | –40 mΩ to + 1Ω \| MIN \| MAX | 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed resistance in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the output resistance to 0.5 A on channel 1.

```
RES 0.5,(@1)
```

The following query returns the programmed resistance level on channels 1 and 2.

```
RES? (@1)
```

Typical Response:

```
+5.000000E-01
```

### See Also

[SOURce:]RESistance:STATe

## [SOURce:]RESistance:STATe

### Syntax

```
[SOURce:]RESistance:STATe <Bool>, (@<chanlist>)
[SOURce:]RESistance:STATe? (@<chanlist>)
```

### Description

This command enables or disables output resistance programming. The enabled state is ON (1); the disabled state is OFF (0). The output resistance level is set with [SOURce:]RESistance.

> **NOTE** This command only applies to model N6781A and N6785A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if resistance programming is disabled, and 1 if the resistance programing is enabled.

### Examples

The following command enables resistance programming for channel 2.

```
RES:STAT ON,(@2)
```

The following query returns the resistance programming state of channel 1.

```
RES:STAT? (@1)
```

Typical Response:

```
0
```

### See Also

[SOURce:]RESistance

## [SOURce:]STEP:TOUTput

### Syntax

```
[SOURce:]STEP:TOUTput <Bool>, (@<chanlist>)
[SOURce:]STEP:TOUTput? (@<chanlist>)
```

### Description

This command specifies whether an output trigger signal is generated when a transient voltage or current step occurs. The state is either ON (1) or OFF (0). A trigger is generated when the state is True (ON).

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if the trigger signal will NOT be generated (OFF) when a step occurs, and 1 if a trigger signal will be generated (ON) when a step occurs.

### Examples

The following command sets the step trigger signal ON for channel 2.

```
STEP:TOUT ON,(@2)
```

The following query returns the step trigger signal state of channel 1.

```
STEP:TOUT? (@1)
```

Typical Response:

```
0
```

### See Also

TRIGger:ACQuire:SOURce

TRIGger:TRANsient:SOURce

## [SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude]
<voltage>, (@<chanlist>)
[SOURce:]VOLTage[:LEVel][:IMMediate][:AMPLitude]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the immediate voltage level of the specified output channel. Units are in volts. The immediate level is the output voltage setting.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with [SOURce:]VOLTage:RANGe.

### Return Format

\<NR3\> The query command returns the programmed voltage level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the output voltage to 50 V on channels 1 and 2.

```
VOLT 50,(@1,2)
```

The following query returns the programmed voltage level on channels 1 and 2.

```
VOLT? (@1,2)
```

Typical Response:

```
+5.000000E+01,+5.000000E+01
```

### See Also

[SOURce:]VOLTage:RANGe

## [SOURce:]VOLTage[:LEVel]:TRIGgered[:AMPLitude]

### Syntax

```
[SOURce:]VOLTage[:LEVel]:TRIGgered[:AMPLitude]
<voltage>, (@<chanlist>)
[SOURce:]VOLTage[:LEVel]:TRIGgered[:AMPLitude]?
[MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the triggered voltage level of the specified output channel. Units are in volts. The triggered level is a stored value that is transferred to the output when an output Step is triggered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with [SOURce:]VOLTage:RANGe.

### Return Format

\<NR3\> The query command returns the programmed triggered level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the triggered voltage to 40 V on channels 1 and 2.

```
VOLT:TRIG 40,(@1,2)
```

The following query returns the programmed triggered level on channels 1 and 2.

```
VOLT:TRIG? (@1,2)
```

Typical Response:

```
+4.000000E+01,+4.000000E+01
```

### See Also

[SOURce:]VOLTage[:LEVel][:IMMediate] [SOURce:]VOLTage:MODE

TRIGger:TRANsient[:IMMediate]

## [SOURce:]VOLTage:BWIDth

### Syntax

[SOURce:]VOLTage:BWIDth \<mode\>, (@\<chanlist\>)

[SOURce:]VOLTage:BWIDth? (@\< chanlist \>)

### Description

This command specifies a voltage bandwidth, which lets you optimize output response time with capacitive loads. These compensation modes only apply when the unit is operating in Voltage Priority mode. The default bandwidth is optimized for stability with a wide range of output capacitors. Three additional bandwidth modes provide faster output response when the output capacitance is restricted to the indicated values.

Bandwidth Mode Output Capacitance Output sensing LOW 0 - 150 microfarads Local or Remote HIGH1 0 - 1 microfarads Remote only HIGH2 1 - 7 microfarads Remote only HIGH3 7 - 150 microfarads Remote only

> **NOTE** This command only applies to model N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | LOW \| HIGH1 \| HIGH2 \| HIGH3 | LOW |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The HIGH compensation modes can only be used in conjunction with remote voltage sensing. See [SOURce:]VOLTage:SENSs:SOURce.

Connecting capacitive loads that fall outside the indicated ranges will result in output instability or oscillation. If output oscillation occurs, a protection function will detect the oscillation and latch the output off. The condition is annunciated by the OSC status bit. The oscillation detect function is always enabled.

To clear the OSC protection, first remove that condition that caused the oscillation by selecting a different bandwidth mode. Then send OUTPut:PROTection:CLEAR .

### Return Format

\<CRD\> The query command returns the bandwidth selection for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets a bandwidth selection of 1 - 7 microfarads for channel 4.

```
VOLT:BWID HIGH2,(@4)
```

The following query returns the bandwidth selection of channel 1.

```
VOLT:BWID? (@1)
```

Typical Response:

```
LOW
```

### See Also

OUTPut:PROTection:OSCillation

## [SOURce:]VOLTage:LIMit:COUPle

### Syntax

```
[SOURce:]VOLTage:LIMit:COUPle <Bool>, (@<chanlist>)
[SOURce:]VOLTage:LIMit:COUPle? (@<chanlist>)
```

### Description

This command sets the voltage limit tracking state. The enabled state is On (1); the disabled state is Off (0). If limit tracking is enabled, The negative voltage limit tracks the positive voltage limit setting. The [SOURce:]VOLTage:LIMit command sets the value of the positive and negative voltage limits.

> **NOTE** This command only applies to model N6784A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 1 if the voltage limit coupling is enabled, and 0 if the voltage limit coupling is disabled.

### Examples

The following command sets the voltage limit coupling on for channel 4.

```
VOLT:LIM:COUP ON,(@4)
```

The following query returns the voltage limit coupling state for channel 1.

```
VOLT:LIM:COUP? (@1)
```

Typical Response:

```
0
```

### See Also

[SOURce:]VOLTage:LIMit [SOURce:]VOLTage:LIMit:NEGative

## [SOURce:]VOLTage:LIMit[:POSitive][:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]VOLTage:LIMit[:POSitive][:IMMediate]
[:AMPLitude] <limit>, (@<chanlist>)
[SOURce:]VOLTage:LIMit[:POSitive][:IMMediate]
[:AMPLitude]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the positive voltage limit of the specified output channel. Units are in volts. If [SOURce:]VOLTage:LIMit:COUPle is enabled, this command also sets the value of the negative voltage limit. Refer to chapter 6 in the N6705 User's Guide under "Current Priority" for more information about voltage limit operation.

> **NOTE** This command only applies to model N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<limit\> | NRf+ | 0 - 20.4 \| MIN \| MAX | MAX (of selected range) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the voltage limit in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the voltage limit to 20 V on channels 1 and 2.

```
VOLT:LIM 20,(@1,2)
```

The following query returns the voltage limit on channels 1 and 2.

```
VOLT:LIM? (@1,2)
```

Typical Response:

```
+2.000000E+01;+2.000000E+01
```

### See Also

[SOURce:]VOLTage:LIMit:COUPle [SOURce:]VOLTage:LIMit:NEGative

## [SOURce:]VOLTage:LIMit:NEGative[:IMMediate][:AMPLitude]

### Syntax

```
[SOURce:]VOLTage:LIMit:NEGative[:IMMediate]
[:AMPLitude] <limit>, (@<chanlist>)
[SOURce:]VOLTage:LIMit:NEGative[:IMMediate]
[:AMPLitude]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the negative voltage limit of the specified output channel. Units are in volts. If [SOURce:]VOLTage:LIMit:COUPle is enabled, this command also sets the value of the positive voltage limit. Refer to chapter 6 in the N6705 User's Guide under "Current Priority" for more information about voltage limit operation.

> **NOTE** This command only applies to model N6784A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<limit\> | NRf+ | -20.4 to 0 \| MIN \| MAX | MIN (of selected range) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

MIN refers to the most negative value of the range. MAX refers to the least negative value of the range.

### Return Format

\<NR3\> The query command returns the negative voltage limit in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the negative voltage limit to -19 V on channels 1 and 3.

```
VOLT:LIM:NEG -19,(@1,3)
```

The following query returns the negative voltage limit on channels 1 and 2.

```
VOLT:LIM:NEG? (@1,3)
```

Typical Response:

```
-1.900000E+01,-1.900000E+01
```

### See Also

[SOURce:]VOLTage:LIMit:COUPle [SOURce:]VOLTage:LIMit

## [SOURce:]VOLTage:MODE

### Syntax

```
[SOURce:]VOLTage:MODE <mode>, (@<chanlist>)
[SOURce:]VOLTage:MODE? (@<chanlist>)
```

### Description

This command determines what happens to the output voltage when the transient system is initiated and triggered.

FIXed The output voltage remains at the immediate value.

STEP The output goes to the triggered level when a trigger occurs.

LIST The output follows the programmed list values when a trigger occurs.

ARB The output follows the arbitrary waveform values when a trigger occurs.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | FIXed \| STEP \| LIST \| ARB | FIXed |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns the voltage mode for each channel specified.

Multiple responses are separated by commas.

### Examples

The following command sets the voltage mode of channel 4.

```
VOLT:MODE STEP,(@4)
```

The following query returns the voltage mode of channel 1.

```
VOLT:MODE? (@4)
```

Typical Response:

```
FIX
```

### See Also

[SOURce:]CURRent:MODE INITiate[:IMMediate]:TRANsient

TRIGger:TRANsient[:IMMediate]

## [SOURce:]VOLTage:PROTection[:LEVel]

### Syntax

```
[SOURce:]VOLTage:PROTection[:LEVel] <voltage>,
(@<chanlist>)
[SOURce:]VOLTage:PROTection[:LEVel]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the over-voltage protection (OVP) level of the output channel. The values are programmed in volts. If the output voltage exceeds the OVP level, the output is disabled and the Questionable Condition status register OV bit is set.

> **NOTE** This command does NOT apply to models N678xA SMU. For these models, refer to VOLTage:PROTection:REMote and VOLTage:PROTection:REMote:NEGative.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - maximum \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

An over-voltage condition can be cleared with the OUTput:PROTection:CLEar command after the condition that caused the OVP trip is removed.

### Return Format

\<NR3\> The query command returns the programmed protection level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the voltage protection level to 45 V on channel 1.

```
VOLT:PROT 45,(@1)
```

The following query returns the programmed voltage protection level on channel 1.

```
VOLT:PROT? (@1)
```

Typical Response:

```
+4.500000E+01
```

### See Also

OUTPut:PROTection:CLEar

## [SOURce:]VOLTage:PROTection:DELay[:TIME]

### Syntax

```
[SOURce:]VOLTage:PROTection:DELay[:TIME] <time>,
(@<chanlist>)
[SOURce:]VOLTage:PROTection:DELay[:TIME]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the over-voltage protection delay. The over-voltage protection function will not be triggered on the specified output channel during the delay time. After the delay time has expired, the over-voltage protection function will be active. This prevents momentary changes in output status from triggering the over-current protection function.

Programmed values can range from 60 microseconds to 5 milliseconds with a resolution of 20.48 microseconds.

> **NOTE** This command only applies to models N6783A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 60 µs - 5 ms \| MIN \| MAX The maximum value is dependent on the voltage rating of the power module. | 0 (zero) |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR3\> The query command returns the programmed delay time. The reading is in the form +n.nnnnnnE+nn.

### Examples

The following command sets the voltage protection delay to 1 millisecond on channel 1.

```
VOLT:PROT:DEL 0.001,(@1)
```

The following query returns the programmed voltage protection delay on channel 1.

```
VOLT:PROT:DEL? (@1)
```

Typical Response:

```
+1.000000E-03
```

### See Also

OUTPut:PROTection:CLEar

## [SOURce:]VOLTage:PROTection:REMote[:POSitive][:LEVel]

### Syntax

```
[SOURce:]VOLTage:PROTection:REMote[:POSitive]
[:LEVel] <voltage>, (@<chanlist>)
[SOURce:]VOLTage:PROTection:REMote[:POSitive]
[:LEVel]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the positive over-voltage remote protection (OVP) level of the output channel. The values are programmed in volts. If the output voltage exceeds the OVP level, the output is disabled and the Questionable Condition status register OV bit is set.

For Models N678xA only, the OVP circuit senses the 4-wire sense terminals rather than the output terminals. This allows for more precise overvoltage monitoring directly at the load. Since incorrect sense terminal wiring such as reversed or open sense wires could defeat this feature, the OVP will automatically trip if the voltage at the output terminals rises more than 1.5 V above the voltage at the sense terminals.

> **NOTE** This command only applies to models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | 0 - 22 \| MIN \| MAX | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

An over-voltage condition can be cleared with the OUTput:PROTection:CLEar command after the condition that caused the OVP trip is removed.

### Return Format

\<NR3\> The query command returns the over-voltage remote protection level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the over-voltage remote protection level to 15 V on channel 1.

```
VOLT:PROT:REM 15,(@1)
```

The following query returns the over-voltage remote protection level on channel 1.

```
VOLT:PROT:REM? (@1)
```

Typical Response:

```
+1.500000E+01
```

### See Also

OUTPut:PROTection:CLEar [SOURce:]VOLTage:PROTection:REMote:NEGative

## [SOURce:]VOLTage:PROTection:REMote:NEGative[:LEVel]

### Syntax

```
[SOURce:]VOLTage:PROTection:REMote:NEGative[:LEVel]
<voltage>, (@<chanlist>)
[SOURce:]VOLTage:PROTection:REMote:NEGative]
[:LEVel]? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the negative over-voltage remote protection (OVP) level of the output channel. The values are programmed in volts. If the output voltage exceeds the OVP level, the output is disabled and the Questionable Condition status register OV bit is set.

For Models N678xA only, the OVP circuit senses the 4-wire sense terminals rather than the output terminals. This allows for more precise overvoltage monitoring directly at the load. Since incorrect sense terminal wiring such as reversed or open sense wires could defeat this feature, the OVP will automatically trip if the voltage at the output terminals rises more than 1.5 V above the voltage at the sense terminals.

> **NOTE** This command only applies to model N6784A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<voltage\> | NRf+ | -22 to 0 \| MIN \| MAX | MIN |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

An over-voltage condition can be cleared with the OUTput:PROTection:CLEar command after the condition that caused the OVP trip is removed.

MIN refers to the most negative value of the range. MAX refers to the least negative value of the range.

### Return Format

\<NR3\> The query command returns the negative over-voltage remote protection level in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the negative over-voltage remote protection level to -15 V on channel 1.

```
VOLT:PROT:REM:NEG -15,(@1)
```

The following query returns the negative over-voltage remote protection level on channel 1.

```
VOLT:PROT:REM:NEG? (@1)
```

Typical Response:

```
-1.500000E+01
```

### See Also

OUTPut:PROTection:CLEar [SOURce;]VOLTage:PROTection:REMote

## [SOURce:]VOLTage:RANGe

### Syntax

[SOURce:]VOLTage:RANGe \<range\>, (@\<chanlist\>)

[SOURce:]VOLTage:RANGe? [MIN|MAX,] (@\<chanlist\>)

### Description

This command sets the output voltage range on models that have multiple ranges. The value that you enter must be the highest value in volts that you expect to source. The instrument selects the range with the best resolution for the value entered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<range\> | NRf+ | 0 - maximum \| MIN \| MAX Values entered are model dependent. | MAX |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is coupled with the [SOURce:]VOLTage command. This means that if a range command is sent that places an output on a range with a lower maximum voltage than the present voltage level, an error is generated. This also occurs if a voltage level is programmed with a value too large for the present range.

These types of errors can be avoided by sending the both level and range commands in the same SCPI message. When the range and setting information is received as a set, no range/setting conflict occurs.

If programming a range value causes a range change to occur while the output is enabled, the output will be temporarily disabled while the range switch occurs. The transition from on-to-off and then from off-to-on will also be delayed by the settings of OUTPut:DELay:FALL and OUTPut:DELay:RISE.

### Return Format

\<NR3\> The query command returns the maximum voltage that can be output on the range that is presently set. The voltage level is in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas.

### Examples

The following command sets the output voltage range to 5 V on channels 1 and 2.

```
VOLT:RANG 5,(@1,2)
```

The following query returns the programmed voltage range on channels 1 and 2.

```
VOLT:RANG? (@1,2)
```

Typical Response:

```
+5.500000E+00,+5.500000E+00
```

### See Also

[SOURce:]VOLTage[:LEVel][:IMMediate]

## [SOURce:]VOLTage:SENSe:SOURce

### Syntax

```
[SOURce:]VOLTage:SENSe:SOURce <state>, (@<chanlist>)
[SOURce:]VOLTage:SENSe:SOURce? (@<chanlist>)
```

### Description

This command sets the state of the remote sense relays.

INTernal Internal sets the remote sense relays to local sensing.

The front panel remote sense terminals are internally connected to the output terminals. The 4 wire indicator is off.

EXTernal External sets the remote sense relays to remote sensing.

The front panel remote sense terminals are not internally connected to the output terminals and must be connected to the external load. The 4 wire indicator is on.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<state\> | CPD | INTernal \| EXTernal | INTernal |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns INT or EXT.

### Examples

The following selects EXTernal as the remote relay state.

```
VOLT:SENS:SOUR EXT,(@1)
```

The following query returns the remote sense relay state.

```
VOLT:SENS:SOUR? (@1)
```

Typical Response:

```
INT
```

## [SOURce:]VOLTage:SLEW[:IMMediate]

### Syntax

```
[SOURce:]VOLTage:SLEW[:IMMediate] <slew>|INFinity,
(@<chanlist>)
[SOURce:]VOLTage:SLEW[:IMMediate]? [MIN|MAX,]
(@<chanlist>)
```

### Description

This command sets the voltage slew rate in volts per second. The slew rate setting affects all programmed voltage changes, including those due to the output state turning on or off. The slew rate can be set to any value between 0 and 9.9E+37. For very large values, the slew rate will be limited by the analog performance of the output circuit. The keywords MAX or INFinity set the slew rate to maximum.

The query returns the value that was sent, unless the value was less than the minimum slew rate, in which case the minimum value is returned. The LSB weight of the 24-bit register can be queried using [SOURce:]VOLTage:SLEW? MIN. The exact value varies slightly according to the voltage calibration.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<slew\> | NRf+ | 0 - 9.9E+37 \| MIN \| MAX \| INFinity | 9.9E+37 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Internally, the slew rate is controlled by a 24-bit register. The slowest or minimum slew rate is a function of the full-scale voltage range. For a model with a 50 V range, the minimum slew rate is about 4.76 V/s. For other voltage ranges the minimum slew rate is proportional to this value, so for a model with a 5 V range the minimum slew rate is about 0.476 V/s.

The unit accepts slew rates as low as 0 V/s, but values sent to the 24-bit register will be limited at 1 count.

### Return Format

\<NR3\> The query command returns the programmed slew rate in the form +n.nnnnnnE+nn for each channel specified. Multiple responses are separated by commas. If a slew rate of 9.9E37 is returned, it means that the maximum or fastest slew rate has been set.

### Examples

The following command sets the slew rate to 5 volts per second on channel 1.

```
VOLT:SLEW 5,(@1)
```

The following query returns the programmed slew rate on channel 1.

```
VOLT:SLEW? (@1)
```

Typical Response:

```
+5.000000E+00
```

### See Also

[SOURce:]CURRent:SLEW [SOURce:]VOLTage:SLEW:MAXimum

## [SOURce:]VOLTage:SLEW:MAXimum

### Syntax

```
[SOURce:]VOLTage:SLEW:MAXimum <Bool>, (@<chanlist>)
[SOURce:]VOLTage:SLEW:MAXimum? (@<chanlist>)
```

### Description

This command sets the voltage slew rate maximum override. When enabled (ON), the power module's slew rate is set to its maximum value.

When disabled (OFF), the power module's slew rate is set to the immediate value set by the [SOURce:]VOLTage:SLEW command.

[SOURce:]VOLTage:SLEW:MAX does not affect the [SOURce:]VOLTage:SLEW setting.

Use [SOURce:]VOLTage:SLEW? MAX to query the maximum slew rate that was set.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The [SOURce:]VOLTage:SLEW:MAX command is coupled to the [SOURce:]VOLTage:SLEW command. If [SOURce:]VOLTage:SLEW sets the rate to MAX or INFinity, [SOURce:]VOLTage:SLEW:MAXimum is enabled. If the slew rate is set to any other value, [SOURce:]VOLTage:SLEW:MAXimum is disabled.

### Return Format

\<NR1\> The query command returns 0 if the slew rate override is disabled, and 1 if the slew rate override is enabled.

### Examples

The following command enables the slew rate maximum override on channel 1.

```
VOLT:SLEW:MAX ON,(@1)
```

The following query returns the state of the slew rate override on channel 1.

```
VOLT:SLEW:MAX? (@1)
```

Typical Response:

```
1
```

### See Also

[SOURce:]VOLTage:SLEW [SOURce:]CURRent:SLEW:MAXimum
