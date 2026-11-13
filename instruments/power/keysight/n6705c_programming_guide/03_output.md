# OUTPut Subsystem Introduction

The Output subsystem controls the output, power-on, protection, and relay functions.

| SCPI Command | Description |
|---|---|
| OUTPut |  |
| [:STATe] \<Bool\> [,NORelay], (@chanlist) | Enables/disables the specified output channel(s) |
| :COUPle |  |
| [:STATe] \<Bool\> | Enables/disables channel coupling for output synchronization |
| :CHANNel [\<NR1\> {,\<NR1\>}] | Selects which channels are coupled |
| :DOFFset \<NRf\> | Specifies a maximum delay offset to synchronize output changes |
| :MODE AUTO \| MANual | Specifies the output delay coupling mode |
| :MAX |  |
| :DOFFset? | Returns the maximum delay offset required for a mainframe |
| :DELay |  |
| :FALL \<NRf+\>, (@chanlist) | Sets the output turn-off sequence delay |
| :RISE \<NRf+\>, (@chanlist) | Sets the output turn-on sequence delay |
| :PMODe VOLTage \| CURRent, (@chanlist) | Sets the mode for turn on/off transitions (N6761A, N6762A) |
| :TMODe HIGHZ \| LOWZ, (@chanlist) | Specifies the turn-on/turn-off impedance (only on N678xA SMU) |
| :INHibit |  |
| :MODE LATChing \| LIVE \| OFF | Sets the remote inhibit input |
| :PON |  |
| :STATe RST \| RCL0 | Programs the power-on state |
| :PROTection |  |
| :CLEar (@chanlist) | Resets latched protection |
| :COUPle \<Bool\> | Enables/disables channel coupling for protection faults |
| :DELay \<NRf+\>, (@chanlist) | Sets over-current protection programming delay |
| :OSCillation \<Bool\>, (@chanlist) | Enables/disables output oscillation protection (N678xA SMU) |
| :WDOG |  |
| [:STATe] \<Bool\> | Enables/disables the I/O watchdog timer |
| :DELay \<NRf+\> | Sets the watchdog timer delay |
| :RELay |  |
| :POLarity NORMal \| REVerse, (@chanlist) | Sets the output relay polarity (Option 760) |

## OUTPut[:STATe]

### Syntax

```
OUTPut[:STATe] <Bool> [,NORelay], (@<chanlist>)
OUTPut[:STATe]? (@<chanlist>)
```

### Description

This command enables or disables the specified output channel(s). The enabled state is ON (1); the disabled state is OFF (0). The state of a disabled output is a condition of zero output voltage and zero source current. If output and sense relays are installed (Option 761), the relays will open when the output is disabled and close when the output is enabled.

The optional NORelay parameter lets you turn the output state on or off and leave the state of the relays unchanged. When not specified, the relays open and close as the output is turned off and on. Relays only open and close when the output is at zero voltage; zero current.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Separate delays can be programmed for the off-to-on and the on-to-off transition using OUTPut:DELay:RISE and OUTput:DELay:FALL.

Because of internal circuit start-up procedures and any installed relay options, the OUTPut ON command may take between 35 and 50 milliseconds to complete its function. The OUTPut OFF command may take between 20 and 25 milliseconds to complete its function. To mitigate this built-in delay, you can program the output to zero volts rather than using the output on/off command.

### Return Format

\<NR1\> The query command returns 0 if the output is OFF, and 1 if the output is ON.

### Example

The following command turns the output of channel 2 on.

```
OUTP ON,(@2)
```

The following query returns the output state of channel 4.

```
OUTP? (@4)
```

Typical Response:

```
0
```

### See Also

OUTPut:PON:STATe OUTPut[:STATe]:DELay:FALL OUTPut[:STATe]:DELay:RISE

## OUTPut[:STATe]:COUPle:CHANnel

### Syntax

```
OUTPut[:STATe]:COUPle:CHANnel [<channel>
{,<channel>}]
OUTPut[:STATe]:COUPle:CHANnel?
```

### Description

This command specifies which output channels in the mainframe are controlled by the output synchronization function. The output channels that have been synchronized or coupled will turn on and off together when any one of them is turned on or off, or when a signal is received from a digital connector pin that has been configured as an On couple or an Off couple pin. Refer to Appendix C in the User's Guide for detailed information.

There can be only one set of coupled channels in a mainframe. If another coupled set is programmed, the existing set is deleted and the new set applies. If you do not specify an output channel, this command will uncouple all output channels on the mainframe.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<channel\> | NR1 | 1 \| 2 \| 3 \| 4 | Required parameter |

### Remarks

When this command is sent, all output channels in the mainframe will go to the output Off state.

This setting is non-volatile and not affected by \*RST.

### Return Format

\<NR1\> The query command returns the channels that are coupled. Multiple responses are separated by commas.

### Example

The following command couples channels 1, 2, and 4.

```
OUTP:COUP:CHAN 1,2,4
```

The following query returns the output coupling state.

```
OUTP:COUP:CHAN?
```

Typical Response:

```
1,2,4
```

### See Also

OUTPut[:STATe]:COUPle:DOFFset [SOURce:]DIGital:PIN\<1-7\>:FUNCtion

## OUTPut[:STATe]:COUPle:DOFFset

### Syntax

```
OUTPut[:STATe]:COUPle:DOFFset <delay>
OUTPut[:STATe]:COUPle:DOFFset?
```

### Description

This command specifies a maximum delay offset to synchronize the output state changes. Units are in seconds. Setting this time to the maximum delay offset specified for any output channel that is being coupled will cause all of the output channels to synchronize to the turn-on times specified by OUTput:DELay:RISE. This delay only applies to coupled channels, provided OUTput:COUPle is enabled. Refer to Appendix C in the User's Guide for detailed information.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<delay\> | NRf | 0 - 1.023 | Required parameter |

### Remarks

When this command is sent, all output channels in the mainframe will go to the output Off state.

This setting is non-volatile and not affected by \*RST.

### Return Format

\<NR3\> The query command returns the programmed delay offset in the form +n.nnnnnnE+nn.

### Example

The following specifies a delay offset of 60 milliseconds.

```
OUTP:COUP:DOFF 0.06
```

The following query returns the delay offset.

```
OUTP:COUP:DOFF?
```

Typical Response:

```
+6.000000E-02
```

### See Also

OUTPut[:STATe]:COUPle:CHANnel OUTPut[:STATe]:DELay:RISE

## OUTPut[:STATe]:COUPle:DOFFset:MODE

### Syntax

```
OUTPut[:STATe]:COUPle:DOFFset:MODE <mode>
OUTPut[:STATe]:COUPle:DOFFset:MODE?
```

### Description

This command sets the mode that determines where the output coupling delay value comes from when outputs are synchronized.

Normally, all outputs in a mainframe are included in an output on/off delay sequence. Additionally, a delay offset is automatically calculated and applied by the firmware to synchronize the output turn-on delays.

The output synchronization function lets you select specific outputs to be synchronized as well as manually specify the delay offset, which serves as a reference for the user-programmed turn-on delays. Refer to Appendix C in the User's Guide for detailed information.

AUTO The power system automatically calculates the maximum delay offset value for all output channels in the mainframe.

MANual The power system uses the delay offset value set by OUTPut:COUPle:DOFFSet.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | AUTO \| MANual | AUTO |

### Remarks

When this command is sent, all output channels in the mainframe will go to the output Off state.

This setting is non-volatile and not affected by \*RST.

### Return Format

\<CRD\> The query command returns AUTO or MAN.

### Example

The following selects Manual as the delay offset mode.

```
OUTP:COUP:DOFF:MODE MAN
```

The following query returns the delay offset mode.

```
OUTP:COUP:DOFF:MODE?
```

Typical Response:

```
MAN
```

### See Also

OUTPut[:STATe]:COUPle:DOFFset

## OUTPut[:STATe]:COUPle:MAX:DOFFset?

### Syntax

```
OUTPut[:STATe]:COUPle:MAX:DOFFset?
```

### Description

This query returns the largest delay offset that is required for the output channels installed in this mainframe. Refer to Appendix C in the User's Guide for detailed information.

### Return Format

\<NR3\> The query command returns the maximum delay offset in the form +n.nnnnnnE+nn.

### Example

The following query returns the maximum delay offset.

```
OUTP:COUP:MAX:DOFF?
```

Typical Response:

```
+3.000000E-02
```

### See Also

OUTPut[:STATe]:COUPle:DOFFset

## OUTPut[:STATe]:DELay:FALL

### Syntax

```
OUTPut[:STATe]:DELay:FALL <delay>, (@<chanlist>)
OUTPut[:STATe]:DELay:FALL? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the delay in seconds that the instrument waits before disabling the specified output. This allows multiple output channels to turn off in sequence. Each output will not turn off until its delay time has elapsed. This command affects on-to-off transitions including changes in the OUTPut[:STATe] as well as transitions due to changes in the voltage range or current range. It does NOT affect transitions to off caused by protection functions. Delay times can be programmed from 0 to 1023 seconds with the following resolution:

| Range in seconds | Resolution |
|---|---|
| 0 to 1.023E-4 | 100 nanoseconds |
| 1.03E-4 to 1.023E-3 | 1 microsecond |
| 1.03E-3 to 1.023E-2 | 10 microseconds |
| 1.03E-2 to 1.023E-1 | 100 microseconds |
| 1.03E-1 to 1.023E+0 | 1 millisecond |
| 1.03E+0 to 1.023E+1 | 10 milliseconds |
| 1.03E+1 to 1.023E+2 | 100 milliseconds |
| 1.03E+2 to 1.023E+3 | 1 second |

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<delay\> | NRf+ | 0 - 1.023 \| MIN \| MAX | 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Refer to chapter 3 of the N6705 User's Guide for more information about configuring a turn-on/turn-off turn-on sequence..

### Return Format

\<NR3\> The query command returns the programmed delay time. The reading is in the form +n.nnnnnnE+nn.

### Example

The following command sets a delay of 0.5 seconds before turning off the output of channel 2.

```
OUTP:DEL:FALL 0.5,(@2)
```

The following query returns the maximum allowable delay time of channel 1.

```
OUTP:DEL:FALL? MAX,(@1)
```

Typical Response:

```
+1.023000E+00
```

### See Also

OUTPut[:STATe] OUTPut[:STATe]:DELay:RISE

## OUTPut[:STATe]:DELay:RISE

### Syntax

```
OUTPut[:STATe]:DELay:RISE <delay>, (@<chanlist>)
OUTPut[:STATe]:DELay:RISE? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the delay in seconds that the instrument waits before enabling the specified output. This allows multiple output channels to turn on in sequence. Each output will not turn on until its delay time has elapsed. This command affects all off-to-on transitions including changes in the OUTPut[:STATe] as well as transitions due to OUTPut:PROTection:CLEar. Delay times can be programmed from 0 to 1023 seconds with the following resolution:

| Range in seconds | Resolution |
|---|---|
| 0 to 1.023E-4 | 100 nanoseconds |
| 1.03E-4 to 1.023E-3 | 1 microsecond |
| 1.03E-3 to 1.023E-2 | 10 microseconds |
| 1.03E-2 to 1.023E-1 | 100 microseconds |
| 1.03E-1 to 1.023E+0 | 1 millisecond |
| 1.03E+0 to 1.023E+1 | 10 milliseconds |
| 1.03E+1 to 1.023E+2 | 100 milliseconds |
| 1.03E+2 to 1.023E+3 | 1 second |

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<delay\> | NRf+ | 0 - 1.023 \| MIN \| MAX | 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

Output channel turn-on characteristics vary across the three power module types - DC Power, Auto ranging, and Precision. Refer to chapter 3 of the N6705 User's Guide for more information about configuring a turn-on/turn-off turn-on sequence. When several channels of the same module type are programmed off-to-on by this command, output sequencing is precisely determined by the programmed turn-on delays.

When outputs of different module types are sequenced using this command, there may be an additional offset of a few milliseconds from one output to another. This offset is the same for each module type and is repeatable. Once you have characterized this offset, using an oscilloscope for example, you can adjust the programmed delays to compensate for the offset and give the desired output sequencing.

Outputs within the same module type can also have an offset if one model has output relays (Option 761) and another does not. These offsets are also repeatable and can be compensated by adjusting the programmed delay values.

### Return Format

\<NR3\> The query command returns the programmed delay time. The reading is in the form +n.nnnnnnE+nn.

### Example

The following command sets a delay of 0.5 seconds before turning on the output of channel 2.

```
OUTP:DEL:RISE 0.5,(@2)
```

The following query returns the maximum allowable delay time of channel 1.

```
OUTP:DEL:RISE? MAX,(@1)
```

Typical Response:

```
+1.023000E+00
```

### See Also

OUTPut[:STATe] OUTPut[:STATe]:DELay:FALL

## OUTPut[:STATe]:PMODe

### Syntax

```
OUTPut[:STATe]:PMODe <mode>, (@<chanlist>)
OUTPut[:STATe]:PMODe? (@<chanlist>)
```

### Description

This command sets the preferred mode for output on or output off transitions. It allows output state transitions to be optimized for either constant voltage or constant current operation. Turn-on and turn-off overshoots are minimized for the preferred mode of operation.

VOLTage Minimizes output on/off voltage overshoots in constant voltage operation.

CURRent Minimizes output on/off current overshoots in constant current operation.

> **NOTE** This command is used only with models N6761A and N6762A.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | VOLTage \| CURRent | VOLTage |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns VOLT or CURR.

### Example

The following command sets the preferred mode of channel 1 to CURRent.

```
OUTP:PMOD CURR,(@1)
```

The following query returns the setting of the preferred mode of channel 2.

```
OUTP:PMOD? (@2)
```

Typical Response:

```
VOLT
```

### See Also

OUTPut[:STATe]

## OUTPut[:STATe]:TMODe

### Syntax

```
OUTPut[:STATe]:TMODe <mode>, (@<chanlist>)
OUTPut[:STATe]:TMODe? (@<chanlist>)
```

### Description

This command specifies the output impedance mode at turn-off.

HIGHZ Sets the output to a high impedance mode at turn-off.

In high impedance mode, the output relays are opened while the output remains at its set value.

LOWZ Sets the output to a low impedance mode at turn-off. In low impedance mode, the output is first down-programmed to zero, after which the output relays are opened.

> **NOTE** This command is used only with models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | HIGHZ \| LOWZ | HIGHZ |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns HIGHZ or LOWZ.

### Example

The following command sets the turn-off mode of channel 1 to high impedance.

```
OUTP:TMOD HIGHZ,(@1)
```

The following query returns the setting of the turn-off mode of channel 2.

```
OUTP:TMOD? (@2)
```

Typical Response:

```
LOWZ
```

### See Also

OUTPut[:STATe]

## OUTPut:INHibit:MODE

### Syntax

```
OUTPut:INHibit:MODE <mode>
OUTPut:INHibit:MODE?
```

### Description

This command selects the mode of operation of the Inhibit input (INH).

The inhibit function shuts down ALL output channels in response to an external signal on the Inhibit input. If an output channel has been turned off by OUTPut[:STATe], the inhibit function does not affect the output channel while it is in the OFF state. The Inhibit mode setting is stored in non-volatile memory.

The following modes can be selected: LATChing Causes a logic-true transition on the Inhibit input to disable all outputs. The outputs remain disabled until the Inhibit input is returned to logic-false and the latched INH status bit is cleared by sending the OUTPut:PROTection:CLEar command or a protection clear command from the front panel.

LIVE Allows the enabled outputs to follow the state of the Inhibit input. When the Inhibit input is true, the outputs are disabled. When the Inhibit input is false, the outputs are re-enabled.

OFF The Inhibit input is ignored.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<mode\> | CPD | LATChing \| LIVE \| OFF | Required parameter |

### Return Format

\<CRD\> The query command returns LATC, LIVE, or OFF.

### Example

The following command sets the Inhibit Input to Live mode.

```
OUTP:INH:MODE LIVE
```

The following query returns the setting of the Inhibit Input.

```
OUTP:INH:MODE?
```

Typical Response:

```
OFF
```

### See Also

OUTPut[:STATe]

OUTPut:PROTection:CLEar

## OUTPut:PON:STATe

### Syntax

```
OUTPut:PON:STATe <state>
OUTPut:PON:STATe?
```

### Description

This command determines if the power-on state is set to the \*RST (RST) state or the instrument state stored in memory location 0 (RCL0). The parameter is saved in non-volatile memory. Instrument states can be stored using the \*SAV command.

When shipped from the factory, the \*RSTcommand is issued at power-on.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<state\> | CPD | RST \| RCL0 | Required parameter |

### Return Format

\<CRD\> The query command returns RST or RCL0.

### Example

The following command sets the power-on state to the \*RST state.

```
OUTP:PON:STAT RST
```

The following query returns the setting of the power-on state.

```
OUTP:PON:STAT?
```

Typical Response:

```
RST
```

### See Also

\*RCL

\*RST

\*SAV

## OUTPut:PROTection:CLEar

### Syntax

```
OUTPut:PROTection:CLEar (@<chanlist>)
```

### Description

This command clears the latched protection status that disables the output when an over-voltage, over-temperature, over-current, inhibit signal, power-fail condition, or on some models, a power-limit condition is detected.

All conditions that generate the fault must be removed before the latched status can be cleared. The output is restored to the state it was in before the fault condition occurred.

> **NOTE** If a protection shutdown occurs during an output list, the list continues running even though the output is disabled. When the protection status is cleared and the output becomes enabled again, the output will be set to the values of the step that the list is presently at.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command clears the latched protection status of channel 1.

```
OUTP:PROT:CLE (@1)
```

### See Also

OUTPut:PROTection:COUPle

OUTPut:PROTection:DELay

## OUTPut:PROTection:COUPle

### Syntax

```
OUTPut:PROTection:COUPle <Bool>
OUTPut:PROTection:COUPle?
```

### Description

This command enables or disables output coupling for protection faults.

When enabled, ALL output channels are disabled when a protection fault occurs on any output channel. The enabled state is On (1); the disabled state is Off (0). When disabled, only the affected output channel is disabled when a protection fault is triggered.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |

### Return Format

\<NR1\> The query command returns 0 if the protection coupling is OFF (disabled), and 1 if the protection coupling is ON (enabled).

### Example

The following command enables protection coupling.

```
OUTP:PROT:COUP ON
```

The following query returns the protection coupling setting.

```
OUTP:PROT:COUP?
```

Typical Response:

```
0
```

### See Also

OUTPut:PROTection:CLEar

OUTPut:PROTection:DELay

## OUTPut:PROTection:DELay

### Syntax

```
OUTPut:PROTection:DELay <delay>, (@<chanlist>)
OUTPut:PROTection:DELay? [MIN|MAX,] (@<chanlist>)
```

### Description

This command sets the over-current protection delay. The over-current protection function will not be triggered on the specified output channel during the delay time. After the delay time has expired, the over-current protection function will be active. This prevents momentary changes in output status from triggering the over-current protection function.

Programmed values can range from 0 to 255 milliseconds in increments of 1 millisecond.

The operation of over-current protection is affected by the setting of the current protection delay start event, which is specified by [SOURce:]CURRent:PROTection:DELay:STARt.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<delay\> | NRf+ | 0 - 0.255 \| MIN \| MAX | 20 ms |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

This command is the same as [SOURce:]CURRent:PROTection:DELay.

### Return Format

\<NR3\> The query command returns the programmed delay time. The reading is in the form +n.nnnnnnE+nn.

### Example

The following command sets a current protection delay of 0.2 seconds for channel 2.

```
OUTP:PROT:DEL 0.2,(@2)
```

The following query returns the maximum allowable current protection delay of channel 1.

```
OUTP:PROT:DEL? MAX,(@1)
```

Typical Response:

```
+2.550000E-01
```

### See Also

[SOURce:]CURRent:PROTection:DELay [SOURce:]CURRent:PROTection:DELay:STARt [SOURce:]CURRent:PROTection:STATe

OUTPut:PROTection:CLEar

## OUTPut:PROTection:OSCillation[:STATe]

### Syntax

```
OUTPut:PROTection:OSCillation[:STATe] <Bool>,
(@<chanlist>)
OUTPut:PROTection:OSCillation[:STATe]? (@<chanlist>)
```

### Description

This command enables/disables output oscillation for protection. The enabled state is On (1); the disabled state is Off (0). If capacitive loads cause the output to oscillate on the default or any of the other bandwidth settings, this protection function will detect the oscillation and latch the output off.

> **NOTE** This command is used only with models N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if oscillation protection is OFF (disabled), and 1 if oscillation protection is ON (enabled).

### Example

The following command enables oscillation protection of channel 1.

```
OUTP:PROT:OSC ON,(@1)
```

The following query returns the oscillation protection setting.

```
OUTP:PROT:OSC? (@1)
```

Typical Response:

```
1
```

### See Also

[SOURce:]VOLTage:BWIDth

## OUTPut:PROTection:WDOG[:STATe]

### Syntax

```
OUTPut:PROTection:WDOG[:STATe] <Bool>
OUTPut:PROTection:WDOG[:STATe]?
```

### Description

This command enables/disables the output watchdog timer. The enabled state is On (1); the disabled state is Off (0). When enabled, the watchdog timer causes all outputs to go into protection mode if there is no SCPI I/O activity on the remote interfaces (USB, LAN, GPIB) within the delay time specified by the OUTput:PROTection:WDOG:DELay comamnd.

After the specified delay time has expired, the outputs are disabled, but the programmed output state is not changed. This protection condition is annunciated by the PROT status bit.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |

### Return Format

\<NR1\> The query command returns 0 if the watchdog timer is OFF (disabled), and 1 if the watchdog timer is ON (enabled).

### Example

The following command enables the output watchdog timer.

```
OUTP:PROT:WDOG ON
```

The following query returns the output watchdog timer setting.

```
OUTP:PROT:WDOG?
```

Typical Response:

```
0
```

### See Also

OUTput:PROTection:WDOG:DELay

## OUTPut:PROTection:WDOG:DELay

### Syntax

```
OUTPut:PROTection:WDOG:DELay <delay>
OUTPut:PROTection:WDOG:DELay? [MIN|MAX]
```

### Description

This command sets the output watchdog timer delay in seconds. The watchdog timer causes all outputs to go into protection mode if there is no SCPI I/O activity on the remote interfaces (USB, LAN, GPIB) within the specified delay time. Whenever there is I/O activity on the interfaces the watchdog timer is reset. However, the watchdog timer is NOT reset by activity on the front panel or when using the Web server.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<delay\> | NRf+ | 1 - 3600 \| MIN \| MAX | 60 seconds |

### Return Format

\<NR3\> The query command returns the output watchdog delay time. The reading is in the form +n.nnnnnnE+nn.

### Example

The following command sets an output watchdog delay of 600 seconds.

```
OUTP:PROT:WDOG:DEL 600
```

The following query returns the maximum allowable output watchdog delay.

```
OUTP:PROT:WDOG:DEL? MAX
```

Typical Response:

```
+3.600000+E3
```

### See Also

OUTPut:PROTection:WDOG

## OUTPut:RELay:POLarity

### Syntax

```
OUTPut:RELay:POLarity <polarity>, (@<chanlist>)
OUTPut:RELay:POLarity? (@<chanlist>)
```

### Description

This command sets the output polarity on power modules with polarity reversal relays installed (Option 760). Polarity reversal affects both the output and the sense terminals.

NORMal Causes the output polarity to be the same as the output connector labeling.

REVerse Causes the output polarity to be the reverse of the output connector labeling. This command briefly turns the output off while the output and sense terminal polarities are switched.

> **NOTE** When installed on models N6742B and N6773A, Option 760 (Polarity Reversal) will limit the output current of these models to a maximum of 10 A. Option 760 is not available on models N6741B, N6751A, N6752A, N676xA, or N678xA SMU.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<polarity\> | CPD | NORMal \| REVerse | NORMal |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<CRD\> The query command returns NORM or REV.

### Example

The following command sets the output polarity of channel 1 to REVerse.

```
OUTP:REL:POL REV,(@1)
```

The following query returns the setting of the output polarity of channel 2.

```
OUTP:REL:POL? (@2)
```

Typical Response:

```
NORM
```

### See Also

OUTPut[:STATe]
