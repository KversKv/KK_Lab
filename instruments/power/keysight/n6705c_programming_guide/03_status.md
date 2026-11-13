# STATus Subsystem Introduction

Status register programming lets you determine the operating condition of the instrument at any time. The instrument has three groups of status registers; Operation, Questionable, and Standard Event. The Operation and Questionable status groups each consist of the Condition, Enable, and Event registers as well as NTR and PTR filters.

The Status subsystem is also programmed using Common commands.

Common commands control additional status functions such as the Service Request Enable and the Status Byte registers.

Refer to the Status System diagram.

| SCPI Command | Description |
|---|---|
| STATus |  |
| :OPERation |  |
| [:EVENt]? (@chanlist) | Returns the value of the operation event register |
| :CONDition? (@chanlist) | Returns the value of the operation condition register |
| :ENABle \<NRf\>, (@chanlist) | Enables specific bits in the Event register |
| :NTRansition \<NRf\>, (@chanlist) | Sets the Negative transition filter |
| :PTRansition \<NRf\>, (@chanlist) | Sets the Positive transition filter |
| :PRESet | Presets all enable and transition registers to power-on |
| :QUEStionable |  |
| [:EVENt]? (@chanlist) | Returns the value of the questionable event register |
| :CONDition? (@chanlist) | Returns the value of the questionable condition register |
| :ENABle \<NRf\>, (@chanlist) | Enables specific bits in the Event register |
| :NTRansition \<NRf\>, (@chanlist) | Sets the Negative transition filter |
| :PTRansition \<NRf\>, (@chanlist) | Sets the Positive transition filter |

### Operation Status Group

These registers record signals that occur during normal operation. The group consists of a Condition, PTR/NTR, Event, and Enable register. The outputs of the Operation Status register group are logically-ORed into the OPERation summary bit (7) of the Status Byte register.

### Questionable Status Group

These registers record signals that indicate abnormal operation. The group consists of the same register types as the Operation Status group. The outputs of the Questionable Status group are logically-ORed into the QUEStionable summary bit (3) of the Status Byte register.

### Standard Event Status Group

These registers are programmed by Common commands. The Standard Event event register latches events relating to communication status. It is a read-only register that is cleared when read. The Standard Event enable register functions similarly to the enable registers of the Operation and Questionable status groups.

### Status Byte Register

This register summarizes the information from all other status groups as defined in the IEEE 488.2 Standard Digital Interface for Programmable Instrumentation .

### MSS and RQS Bits

MSS is a real-time (unlatched) summary of all Status Byte register bits that are enabled by the Service Request Enable register. MSS is set whenever the instrument has one or more reasons for requesting service.

\*STB? reads the MSS in bit position 6 of the response but does not clear any of the bits in the Status Byte register.

The RQS bit is a latched version of the MSS bit. Whenever the instrument requests service, it sets the SRQ interrupt line true and latches RQS into bit 6 of the Status Byte register. When the controller does a serial poll, RQS is cleared inside the register and returned in bit position 6 of the response. The remaining bits of the Status Byte register are not disturbed.

### MAV Bit and Output Queue

The Output Queue is a first-in, first-out (FIFO) data register that stores instrument-to-controller messages until the controller reads them.

Whenever the queue holds one or more bytes, it sets the MAV bit (4) of the Status Byte register.

### Status System Diagram

QUESTIONABLE STATUS GROUP (IDENTICAL REGISTERS FOR EACH CHANNEL)

CONDITION PTR/NTR EVENT ENABLE 0 1 1 1 1 OV 1 2 2 2 OC 2 2 4 4 4 4 PF CP+ 3 8 8 8 8 OT 4 16 16 16 16 CHAN 1 QSUM 5 32 32 32 32 LOGICAL CP -6 64 64 64 64 OR QSUM LOGICAL OV- CHAN 2 7 128 128 128 128 OR LIM+ SAME QSUM AS CHAN 3 LIM - 8 256 256 256 256 9 CHAN 1 QSUM INH 512 512 512 CHAN 4 512 10 UNR 1024 1024 1024 1024 11 PROT 2048 2048 2048 2048 12 OSC 4096 4096 4096 4096

STAT:QUES:COND? STAT:QUES:ENAB \<n\>

STAT:QUES:PTR |:NTR \<n\> STAT:QUES:ENAB

STAT:QUES:PTR |:NTR ?

ERROR QUEUE

STAT:QUES:EVEN?

SERVICE STANDARD EVENT STATUS GROUP Error QUEUE REQUEST STATUS Error NOT ENABLE EVENT ENABLE BYTE EMPTY 2 ERR Error 4 4 OPC 0 1 1 QUES 3

SYST:ERR? 8 8

QYE 2 MAV 4 4 4 16 16 LOGICAL 3 DDE 8 8 OR LOGICAL ESB 5 4 32 32 EXE 16 16 OR 5 OUTPUT QUEUE MSS 6 RQS CME 32 32 64

OPER 7 128 128 7 Data PON 128 128 QUEUE NOT \*STB? \*SRE\<n\> Data

\*SRE?

\*ESR? \*ESE\<n\> EMPTY

\*ESE? Data

OPERATION STATUS GROUP (IDENTICAL REGISTERS FOR EACH CHANNEL)

SERVICE CONDITION PTR/NTR EVENT ENABLE REQUEST GENERATION 0 CV 1 1 1 1 1 2 2 2 CC 2 CHAN 1 OSUM 2 OFF 4 4 4 4 LOGICAL WTG 3 8 8 8 8 OR OSUM meas LOGICAL WTG 4 16 16 16 CHAN 2 16 OR trans 5 OSUM MEAS 32 32 32 32 CHAN 3 active TRAN 6 64 64 64 64 OSUM active CHAN 4

STAT:OPER:COND? STAT:OPER:ENAB \<n\>

STAT:OPER:PTR |:NTR \<n\> STAT:OPER:ENAB SAME

STAT:OPER:PTR |:NTR ? AS

STAT:OPER:EVEN? CHAN 1

## STATus:OPERation[:EVENt]?

### Syntax

```
STATus:OPERation[:EVENt]? (@<chanlist>)
```

### Description

This query returns the value of the Operation Status Event register. The Event register is a read-only register, which stores (latches) all events that are passed by the Operation NTR and/or PTR filter. Reading the Operation Status Event register clears it.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The following table lists the bit definitions for the Operation Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 CV | 1 | The output is in constant voltage. |
| 1 CC | 2 | The output is in constant current. |
| 2 OFF | 4 | The output is programmed off. |
| 3 WTG-meas | 8 | The measurement system is waiting for a trigger. |
| 4 WTG-tran | 16 | The transient system is waiting for a trigger. |
| 5 MEAS-active | 32 | The measurement system is initiated. |
| 6 TRAN-active | 64 | The transient system is initiated. |
| 7-15 Not Used | Not Used | 0 is returned. |

Once a bit is set, it remains set until cleared by reading the event register or the \*CLS (clear status) command.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 4 (decimal value = 16) are set, this command will return .

```
24
```

### Example

The following command reads the Operation Status Event register.

```
STAT:OPER? (@1)
```

Typical Response:

```
+24
```

### See Also

STATus:OPERation:ENABle

\*CLS

## STATus:OPERation:CONDition?

### Syntax

```
STATus:OPERation:CONDiton? (@<chanlist>)
```

### Description

This query returns the value of the Operation Status Condition register.

The Condition register is a read-only register, which holds the live (unlatched) operational status of the instrument. Reading the Operation Condition register does not clear it.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The following table lists the bit definitions for the Operation Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 CV | 1 | The output is in constant voltage. |
| 1 CC | 2 | The output is in constant current. |
| 2 OFF | 4 | The output is programmed off. |
| 3 WTG-meas | 8 | The measurement system is waiting for a trigger. |
| 4 WTG-tran | 16 | The transient system is waiting for a trigger. |
| 5 MEAS-active | 32 | The measurement system is initiated. |
| 6 TRAN-active | 64 | The transient system is initiated. |
| 7-15 Not Used | Not Used | 0 is returned. |

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 4 (decimal value = 16) are set, this command will return .

```
24
```

### Example

The following command reads the Operation Status Condition register.

```
STAT:OPER:COND? (@1)
```

Typical Response:

```
+24
```

## STATus:OPERation:ENABle

### Syntax

```
STATus:OPERation:ENABle <value>, (@<chanlist>)
STATus:OPERation:ENABle? (@<chanlist>)
```

### Description

This command and its query set and read the value of the Operation Status Enable register. The Enable register is a mask for enabling specific bits from the Operation Event register to set the operation summary bit (OPER) of the Status Byte register. This bit (bit 7) is the logical OR of all the Operational Event register bits that are enabled by the Operation Status Enable register.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 4 (decimal value = 16), the corresponding decimal value would be 24 (8 + 16).

### Remarks

The following table lists the bit definitions for the Operation Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 CV | 1 | The output is in constant voltage. |
| 1 CC | 2 | The output is in constant current. |
| 2 OFF | 4 | The output is programmed off. |
| 3 WTG-meas | 8 | The measurement system is waiting for a trigger. |
| 4 WTG-tran | 16 | The transient system is waiting for a trigger. |
| 5 MEAS-active | 32 | The measurement system is initiated. |
| 6 TRAN-active | 64 | The transient system is initiated. |
| 7-15 Not Used | Not Used | 0 is returned. |

The STATus:PRESet command will clear all bits in the enable register.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 4 (decimal value = 16) are set, this command will return .

```
24
```

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the enable register.

```
STAT:OPER:ENAB 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:OPER:ENAB? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:OPERation[:EVENt]?

STATus:PRESet

## STATus:OPERation:NTRansition

### Syntax

```
STATus:OPERation:NTRansition <value>, (@<chanlist>)
STATus:OPERation:NTRansition? (@<chanlist>)
```

### Description

These command sets and reads the value of the Operation NTR (Negative-Transition) register. This register serves as a polarity filter between the Operation Condition and Operation Event registers. When a bit in the Operation NTR register is set to 1, then a 1-to-0 transition of the corresponding bit in the Operation Condition register causes that bit in the Operation Event register to be set.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 4 (decimal value = 16), the corresponding decimal value would be 24 (8 + 16).

### Remarks

The following table lists the bit definitions for the Operation Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 CV | 1 | The output is in constant voltage. |
| 1 CC | 2 | The output is in constant current. |
| 2 OFF | 4 | The output is programmed off. |
| 3 WTG-meas | 8 | The measurement system is waiting for a trigger. |
| 4 WTG-tran | 16 | The transient system is waiting for a trigger. |
| 5 MEAS-active | 32 | The measurement system is initiated. |
| 6 TRAN-active | 64 | The transient system is initiated. |
| 7-15 Not Used | Not Used | 0 is returned. |

If the same bits in both NTR and PTR registers are set to 1, then any transition of that bit at the Operation Condition register sets the corresponding bit in the Operation Event register.

If the same bits in both NTR and PTR registers are set to 0, then no transition of that bit at the Operation Condition register can set the corresponding bit in the Operation Event register.

The STATus:PRESet command will set all bits in the NTR register to 0.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register.

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the NTR register.

```
STAT:OPER:NTR 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:OPER:NTR? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:OPERation:PTRansition

STATus:PRESet

## STATus:OPERation:PTRansition

### Syntax

```
STATus:OPERation:PTRansition <value>, (@<chanlist>)
STATus:OPERation:PTRansition? (@<chanlist>)
```

### Description

These command sets and reads the value of the Operation PTR (Positive-Transition) register. This register serves as a polarity filter between the Operation Condition and Operation Event registers. When a bit in the Operation PTR register is set to 1, then a 0-to-1 transition of the corresponding bit in the Operation Condition register causes that bit in the Operation Event register to be set.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 127 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 4 (decimal value = 16), the corresponding decimal value would be 24 (8 + 16).

### Remarks

The following table lists the bit definitions for the Operation Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 CV | 1 | The output is in constant voltage. |
| 1 CC | 2 | The output is in constant current. |
| 2 OFF | 4 | The output is programmed off. |
| 3 WTG-meas | 8 | The measurement system is waiting for a trigger. |
| 4 WTG-tran | 16 | The transient system is waiting for a trigger. |
| 5 MEAS-active | 32 | The measurement system is initiated. |
| 6 TRAN-active | 64 | The transient system is initiated. |
| 7-15 Not Used | Not Used | 0 is returned. |

If the same bits in both NTR and PTR registers are set to 1, then any transition of that bit at the Operation Condition register sets the corresponding bit in the Operation Event register.

If the same bits in both NTR and PTR registers are set to 0, then no transition of that bit at the Operation Condition register can set the corresponding bit in the Operation Event register.

The STATus:PRESet command will set all bits in the PTR register to 1.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register.

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the PTR register.

```
STAT:OPER:PTR 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:OPER:PTR? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:OPERation:NTRansition

STATus:PRESet

## STATus:PRESet

### Syntax

```
STATus:PRESet
```

### Description

This command sets all defined bits in the status system's PTR registers and clears all bits in the NTR and Enable registers.

Operation Register Questionable Register Preset setting STAT:OPER:ENAB STAT:QUES:ENAB 0 - all bits disabled STAT:OPER:NTR STAT:QUES:NTR 0 - all bits disabled STAT:OPER:PTR 127 all defined bits enabled STAT:QUES:PTR 8191 all defined bits enabled

### Example

The following command presets the Operation and Questionable status registers.

```
STAT:PRES
```

## STATus:QUEStionable[:EVENt]?

### Syntax

```
STATus:QUEStionable[:EVENt]? (@<chanlist>)
```

### Description

This query returns the value of the Questionable Status Event register.

The Event register is a read-only register, which stores (latches) all events that are passed by the Questionable NTR and/or PTR filter. Reading the Questionable Status Event register clears it.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The following table lists the bit definitions for the Questionable Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|

0 OV 1 The output is disabled by the over-voltage protection.

1 OC 2 The output is disabled by the over-current protection.

2 PF 4 The output is disabled by the power-fail - which may be caused by a low-line or brownout condition on the AC line.

3 CP+ 8 The output is limited (or disabled) by the positive power limit.

4 OT 16 The over-temperature protection has tripped.

5 CP– 32 The output is limited by the negative power limit.

6 OV– 64 The negative over-voltage protection has tripped.

7 LIM+ 128 The output is in positive voltage or current limit.

8 LIM– 256 The output is in negative voltage or current limit.

9 INH 512 The output is inhibited by an external signal.

10 UNR 1024 The output is unregulated.

11 PROT 2048 The output has been disabled because it is coupled to a protection condition that occurred on another channel.

12 OSC 4096 The oscillation detector has tripped.

13-15 Not Not 0 is returned.

Used Used Once a bit is set, it remains set until cleared by reading the event register or the \*CLS (clear status) command.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 10 is set, this command will return 10 .

```
24
```

### Example

The following command reads the Questionable Status Event register.

```
STAT:QUES?
```

Typical Response:

```
+1024
```

### See Also

STATus:QUEStionable:ENABle?

\*CLS

## STATus:QUEStionable:CONDition?

### Syntax

```
STATus:QUEStionable:CONDition? (@<chanlist>)
```

### Description

This query returns the value of the Questionable Status Condition register. The Condition register is a read-only register, which holds the live (unlatched) questionable status of the instrument. Reading the Questionable Condition register does not clear it.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

The following table lists the bit definitions for the Questionable Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|

0 OV 1 The output is disabled by the over-voltage protection.

1 OC 2 The output is disabled by the over-current protection.

2 PF 4 The output is disabled by the power-fail - which may be caused by a low-line or brownout condition on the AC line.

3 CP+ 8 The output is limited (or disabled) by the positive power limit.

4 OT 16 The over-temperature protection has tripped.

5 CP– 32 The output is limited by the negative power limit.

6 OV– 64 The negative over-voltage protection has tripped.

7 LIM+ 128 The output is in positive voltage or current limit.

8 LIM– 256 The output is in negative voltage or current limit.

9 INH 512 The output is inhibited by an external signal.

10 UNR 1024 The output is unregulated.

11 PROT 2048 The output has been disabled because it is coupled to a protection condition that occurred on another channel.

12 OSC 4096 The oscillation detector has tripped.

13-15 Not Not 0 is returned.

Used Used

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 10 is set, this command will return 10 .

```
24
```

### Example

The following command reads the Questionable Status Condition register.

```
STAT:QUES:COND? (@1)
```

Typical Response:

```
+1024
```

## STATus:QUEStionable:ENABle

### Syntax

```
STATus:QUEStionable:ENABle <value>, (@<chanlist>)
STATus:QUEStionable:ENABle? (@<chanlist>)
```

### Description

This command and its query set and read the value of the Questionable Status Enable register. The Enable register is a mask for enabling specific bits from the Questionable Event register to set the questionable summary bit (QUES) of the Status Byte register. This bit (bit 3) is the logical OR of all the Questionable Event register bits that are enabled by the Questionable Status Enable register.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 5 (decimal value = 32), the corresponding decimal value would be 40 (8 + 32).

### Remarks

The following table lists the bit definitions for the Questionable Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|

0 OV 1 The output is disabled by the over-voltage protection.

1 OC 2 The output is disabled by the over-current protection.

2 PF 4 The output is disabled by the power-fail - which may be caused by a low-line or brownout condition on the AC line.

3 CP+ 8 The output is limited (or disabled) by the positive power limit.

4 OT 16 The over-temperature protection has tripped.

5 CP– 32 The output is limited by the negative power limit.

6 OV– 64 The negative over-voltage protection has tripped.

| Bit Number | Decimal Value | Definition |
|---|---|---|

7 LIM+ 128 The output is in positive voltage or current limit.

8 LIM– 256 The output is in negative voltage or current limit.

9 INH 512 The output is inhibited by an external signal.

10 UNR 1024 The output is unregulated.

11 PROT 2048 The output has been disabled because it is coupled to a protection condition that occurred on another channel.

12 OSC 4096 The oscillation detector has tripped.

13-15 Not Not 0 is returned.

Used Used

The STATus:PRESet command will clear all bits in the enable register.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register.

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the enable register.

```
STAT:QUES:ENAB 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:QUES:ENAB? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:QUEStionable[:EVENt]?

STATus:PRESet

## STATus:QUEStionable:NTRansition

### Syntax

```
STATus:QUEStionable:NTRansition <value>,
(@<chanlist>)
STATus:QUEStionable:NTRansition? (@<chanlist>)
```

### Description

These command sets and reads the value of the Questionable NTR (Negative-Transition) register. This register serves as a polarity filter between the Questionable Condition and Questionable Event registers.

When a bit in the Questionable NTR register is set to 1, then a 1-to-0 transition of the corresponding bit in the Questionable Condition register causes that bit in the Questionable Event register to be set.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 0 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 5 (decimal value = 32), the corresponding decimal value would be 40 (8 + 32).

### Remarks

The following table lists the bit definitions for the Questionable Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|

0 OV 1 The output is disabled by the over-voltage protection.

1 OC 2 The output is disabled by the over-current protection.

2 PF 4 The output is disabled by the power-fail - which may be caused by a low-line or brownout condition on the AC line.

3 CP+ 8 The output is limited (or disabled) by the positive power limit.

4 OT 16 The over-temperature protection has tripped.

5 CP– 32 The output is limited by the negative power limit.

| Bit Number | Decimal Value | Definition |
|---|---|---|

6 OV– 64 The negative over-voltage protection has tripped.

7 LIM+ 128 The output is in positive voltage or current limit.

8 LIM– 256 The output is in negative voltage or current limit.

9 INH 512 The output is inhibited by an external signal.

10 UNR 1024 The output is unregulated.

11 PROT 2048 The output has been disabled because it is coupled to a protection condition that occurred on another channel.

12 OSC 4096 The oscillation detector has tripped.

13-15 Not Not 0 is returned.

Used Used

If the same bits in both NTR and PTR registers are set to 1, then any transition of that bit at the Questionable Condition register sets the corresponding bit in the Questionable Event register.

If the same bits in both NTR and PTR registers are set to 0, then no transition of that bit at the Questionable Condition register can set the corresponding bit in the Questionable Event register.

The STATus:PRESet command will set all bits in the NTR register to 0.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register.

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the NTR register.

```
STAT:QUES:NTR 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:QUES:NTR? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:QUEStionable:PTRansition

STATus:PRESet

## STATus:QUEStionable:PTRansition

### Syntax

```
value
STATus:QUEStionable:PTRansition < >,
(@<chanlist>)
STATus:QUEStionable:PTRansition? (@<chanlist>)
```

### Description

These command sets and reads the value of the Questionable PTR (Positive-Transition) register. This register serves as a polarity filter between the Questionable Condition and Questionable Event registers.

When a bit in the Questionable PTR register is set to 1, then a 0-to-1 transition of the corresponding bit in the Questionable Condition register causes that bit in the Questionable Event register to be set.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NR1 | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Preset = 8191 |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

For example, to enable bit 3 (decimal value = 8) and bit 5 (decimal value = 32), the corresponding decimal value would be 40 (8 + 32).

### Remarks

The following table lists the bit definitions for the Questionable Status registers.

| Bit Number | Decimal Value | Definition |
|---|---|---|

0 OV 1 The output is disabled by the over-voltage protection.

1 OC 2 The output is disabled by the over-current protection.

2 PF 4 The output is disabled by the power-fail - which may be caused by a low-line or brownout condition on the AC line.

3 CP+ 8 The output is limited (or disabled) by the positive power limit.

4 OT 16 The over-temperature protection has tripped.

5 CP– 32 The output is limited by the negative power limit.

| Bit Number | Decimal Value | Definition |
|---|---|---|

6 OV– 64 The negative over-voltage protection has tripped.

7 LIM+ 128 The output is in positive voltage or current limit.

8 LIM– 256 The output is in negative voltage or current limit.

9 INH 512 The output is inhibited by an external signal.

10 UNR 1024 The output is unregulated.

11 PROT 2048 The output has been disabled because it is coupled to a protection condition that occurred on another channel.

12 OSC 4096 The oscillation detector has tripped.

13-15 Not Not 0 is returned.

Used Used

If the same bits in both NTR and PTR registers are set to 1, then any transition of that bit at the Questionable Condition register sets the corresponding bit in the Questionable Event register.

If the same bits in both NTR and PTR registers are set to 0, then no transition of that bit at the Questionable Condition register can set the corresponding bit in the Questionable Event register.

The STATus:PRESet command will set all bits in the PTR register to 1.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register.

### Examples

The following command enables bits 0 and 1 (decimal value = 3) in the PTR register.

```
STAT:QUES:PTR 3,(@1)
```

The following query returns which bits are enabled in the register.

```
STAT:QUES:PTR? (@1)
```

Typical Response:

```
+3
```

### See Also

STATus:QUEStionable:NTRansition

STATus:PRESet
