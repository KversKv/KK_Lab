# Common Commands Introduction

The common commands are defined by the IEEE 488.2 standard. They generally control overall instrument functions, such as reset, status, and synchronization. All common commands consist of a three-letter mnemonic preceded by an asterisk: \*RST \*IDN? \*SRE 8.

| SCPI Command | Description |
|---|---|
| \*CLS | Clear status |
| \*ESE \<NRf\> | Standard event status enable |
| \*ESR? | Return event status register |
| \*IDN? | Return instrument identification |
| \*OPC | Enable "operation complete" bit in ESR |
| \*OPT? | Return option number |
| \*RCL \<NRf\> | Recalls a saved instrument state |
| \*RDT? | Return output channel descriptions |
| \*RST | Reset |
| \*SAV \<NRf\> | Saves an instrument state |
| \*SRE \<NRf\> | Set service request enable register |
| \*STB? | Return status byte |
| \*TRG | Trigger |
| \*TST? | Performs self-test, then returns result |
| \*WAI | Pauses additional command processing until all device commands are done |

## \*CLS

### Syntax

```
*CLS
```

### Description

This command causes the following actions on the status system: Clears the Standard Event Status, Operation Status Event, and Questionable Status Event registers.

Clears the Status Byte and the Error Queue.

If \*CLS immediately follows a program message terminator (\<NL\>), then the output queue and the MAV bit are also cleared.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Example

The following command clears the event register bits.

```
*CLS
```

## \*ESE

### Syntax

```
*ESE <value>
*ESE?
```

### Description

This command programs the Standard Event Status Enable register bits.

The programming determines which events of the Standard Event Status Event register (see \*ESR?) are allowed to set the ESB (Event Summary Bit) of the Status Byte register. A 1 in the bit position enables the corresponding event.

The query reads the enable register and returns a decimal value which corresponds to the binary-weighted sum of all bits set in the register.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Required parameter. |

For example, to enable bit 2 (decimal value = 4), bit 3 (decimal value = 8), and bit 7 (decimal value = 128), the corresponding decimal value would be 140 (4 + 8 + 128).

### Remarks

The following table lists the bit definitions for the Standard Event Register.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 Operation Complete | 1 | All commands prior to and including \*OPC have been executed. |
| 1 Not Used | Not Used | 0 is returned. |
| 2 Query Error | 4 | The instrument tried to read the output buffer but it was empty. Or, a new command line was received before a previous query has been read. Or, both the input and output buffers are full. |
| 3 Device-Dependent Error | 8 | A self-test or calibration error occurred. For a complete listing of the error messages, see SCPI Error Messages. |

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 4 Execution Error | 16 | An execution error occurred (an error in the -200 range has been generated). |
| 5 Command Error | 32 | A command syntax error occurred (an error in the -100 range has been generated). |
| 6 Not Used | Not Used | 0 is returned. |
| 7 Power On | 128 | Power has been turned off and on since the last time the event register was read or cleared. |

All of the enabled events of the Standard Event Status Event Register are logically ORed to cause the Event Summary Bit (ESB) of the Status Byte Register to be set.

The \*CLS (clear status) command will not clear the enable register but it does clear all bits in the event register.

A STATus:PRESet command does not clear the bits in the Status Byte register.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 7 (decimal value = 128) are enabled, the query command will return .

```
136
```

### Example

The following command enables bit 4 (decimal value = 16) in the enable register.

```
*ESE 16
```

The following query returns which bits are enabled in the register.

```
*ESE?
```

Typical Response:

```
+16
```

### See Also

\*ESR?

## \*ESR?

### Syntax

```
*ESR?
```

### Description

This query returns the value of the Event register of the Standard Event Status group. The Event register is a read-only register, which stores (latches) all standard events. Reading the Standard Event Status Event register clears it.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Remarks

The following table lists the bit definitions for the Standard Event Register.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 Operation Complete | 1 | All commands prior to and including \*OPC have been executed. |
| 1 Not Used | Not Used | 0 is returned. |
| 2 Query Error | 4 | The instrument tried to read the output buffer but it was empty. Or, a new command line was received before a previous query has been read. Or, both the input and output buffers are full. |
| 3 Device-Dependent Error | 8 | A self-test or calibration error occurred. For a complete listing of the error messages, see SCPI Error Messages. |
| 4 Execution Error | 16 | An execution error occurred (an error in the -200 range has been generated). |
| 5 Command Error | 32 | A command syntax error occurred (an error in the -100 range has been generated). |
| 6 Not Used | Not Used | 0 is returned. |
| 7 Power On | 128 | Power has been turned off and on since the last time the event register was read or cleared. |

To be reported to the Standard Event Register, the corresponding bits in the event register must be enabled using the \*ESE command.

Once a bit is set, it remains set until cleared by reading the event register or the \*CLS (clear status) command.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 7 (decimal value = 128) are enabled, the query command will return .

```
136
```

### Example

The following command reads the event register (bits 3 and 4 are set).

```
*ESR?
```

Typical Response:

```
+24
```

### See Also

\*ESE

## \*IDN?

### Syntax

```
*IDN?
```

### Description

This command reads the instrument's (mainframe) identification string which contains four comma-separated fields. The first field is the manufacturer's name, the second field is the instrument model number, the third field is the serial number, and the fourth field is the firmware revision.

Keysight Manufacturer Technologies N67xxX Mainframe model number MYxxxxxxxx Mainframe serial number if available, or zero X.xx.xx Revision levels of firmware

### Return Format

\<AARD\> The command returns an arbitrary ASCII string with four comma-separated fields. To read the string into your computer, be sure to dimension a string variable with at least 50 characters.

### Example

The following query returns the instrument's identification string.

```
*IDN?
```

Typical Response:

```
KEYSIGHT TECHNOLOGIES,N6705B,MY00123456,B.00.00
```

## \*OPC

### Syntax

```
*OPC
*OPC?
```

### Description

The command is mainly used for program synchronization. It causes the instrument to set the OPC bit (bit 0) of the Standard Event Status register when the instrument has completed all pending operations sent before \*OPC. Pending operations are complete when: 1. All commands sent before \*OPC, including paralleled commands, have been completed. Most commands are sequential and are completed before the next command is executed. Commands that affect output voltage, current, or state, relays, and trigger actions are executed in parallel with subsequent commands. \*OPC provides notification that all parallel commands have completed.

2. All triggered actions are completed.

The query returns 1 to the output buffer.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Remarks

\*OPC does not prevent processing of subsequent commands, but the OPC bit will not be set until all pending operations are completed.

\*OPC? causes the instrument to place a 1 in the output buffer when all pending operations are completed. \*OPC? does not suspend processing of commands.

### Return Format

\<NR1\> Returns 1 to the output buffer.

### Example

The following command sets the operation complete bit.

```
*OPC
```

The following command waits until the completion of the current command and then sends 1 to the output buffer.

```
*OPC?
```

## \*OPT?

### Syntax

```
*OPT?
```

### Description

This query requests the mainframe to identify any installed options.

### Remarks

A 0 indicates no options are installed.

### Return Format

\<CRD\> The option number.

### Example

The following command returns the option number.

```
*OPT?
```

Typical Response:

```
+0
```

## \*RCL

### Syntax

```
*RCL 0 | 1
```

### Description

This command restores the instrument to a state that was previously stored in memory locations 0 through 1 with the \*SAV command. All instrument states are recalled except for the following: The trigger system is set to the Idle state by an implied ABORt command (this cancels any uncompleted trigger actions).

Calibration is disabled by setting CALibration:STATe to OFF.

All list settings are set to their \*RST values.

### Remarks

The device state stored in location 0 is automatically recalled at power turn-on when the Output Power-On state is set to RCL 0.

You cannot recall the instrument state from a storage location that is empty or was deleted. You can only recall a state from a location that contains a previously stored state.

A Factory Reset (\*RST command) does not affect the configurations stored in memory. Once a state is stored, it remains until it is overwritten or specifically deleted.

### Example

The following command recalls the instrument state previously stored in location 1.

```
*RCL 1
```

### See Also

\*SAV

\*RST

## \*RDT?

### Syntax

```
*RDT?
```

### Description

This query returns a description of all the power modules (channels) installed in a mainframe. Semicolons separate multiple channel descriptions.

CHAN\<c\>:description \<c\> refers to the channel number.

Description returns the model number of the power modules.

### Return Format

\<AARD\> The command returns an arbitrary ASCII string with up to four semicolon-separated fields. To read the string into your computer, be sure to dimension a string variable with at least 50 characters.

### Example

The following query identifies the mainframe's installed power modules.

```
*RDT?
```

Typical Response:

```
CHAN1:N6751A;CHAN2:N6752A
```

## \*RST

### Syntax

```
*RST
```

### Description

This command resets the volatile memory of the instrument to a factory-defined state. Refer to Factory Reset State for a complete listing of the instrument's factory configuration.

### Remarks

\*RST also forces the ABORt:ACQuire and ABORt:TRANsient commands.

This cancels any measurement or output trigger actions presently in process, and resets the two WTG bits in the Status Operation Condition register.

### Example

The following command resets the instrument.

```
*RST
```

### See Also

ABORt:ACQuire

ABORT:DLOG ABORt::ELOG

ABORt:TRANsient

## \*SAV

### Syntax

```
*SAV 0 | 1
```

### Description

This command stores the present state of the instrument to the specified location in non-volatile memory. Up to 2 states can be stored - in locations 0 and 1. Any state previously stored in the same location will be overwritten. Use the \*RCL command to retrieve instrument states. Refer to Factory Reset State for a list of instrument settings that can be saved.

### CAUTION This command causes a write cycle to nonvolatile memory. Nonvolatile

memory has a finite maximum number of write cycles. Programs that repeatedly cause write cycles to nonvolatile memory can eventually exceed the maximum number of write cycles and cause the memory to fail.

### Remarks

If a particular state is desired at power-on, it should be stored in location 0. It will then be automatically recalled at power turn-on if the Output Power-On state is set to RCL0.

List data and the calibration state is NOT saved as part of the \*SAV operation. This means that all list data that is sent to the instrument will be lost when the instrument is turned off.

Data saved in non-volatile memory, described in the Non-volatile Factory Settings, is not affected by the \*SAV command.

A Factory Reset (\*RST command) does not affect the configurations stored in memory. Once a state is stored, it remains until it is overwritten or specifically deleted.

### Example

The following command stores the current instrument state in location 1.

```
*SAV 1
```

### See Also

\*RCL

\*RST

## \*SRE

### Syntax

```
*SRE <value>
*SRE?
```

### Description

This command sets the value of the Service Request Enable register. This register determines which bits from the Status Byte register are summed to set the Master Status Summary (MSS) bit and the Request for Service (RQS) summary bit. A 1 in the bit position enables the corresponding event.

The query reads the enable register and returns a decimal value which corresponds to the binary-weighted sum of all bits set in the register.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<value\> | NRf | A decimal value which corresponds to the binary-weighted sum of the bits in the register (see table below). | Required parameter. |

For example, to enable bit 1 (decimal value = 2), bit 3 (decimal value = 8), and bit 6 (decimal value = 64), the corresponding decimal value would be 74 (2 + 8 + 64).

### Remarks

The following table lists the bit definitions for the Status Byte Register.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 Not Used | Not Used | 0 is returned. |
| 1 Not Used | Not Used | 0 is returned. |
| 2 Error Queue not empty | 4 | One or more errors have been stored in the Error Queue (see SYSTem:ERRor? command). |
| 3 Questionable Status summary | 8 | One or more bits are set in the Questionable Data Register (bits must be enabled, see STATus:QUEStionable:ENABle command). |
| 4 Message Available | 16 | Data is available in the instrument's output buffer. |

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 5 Event Status Byte summary | 32 | One or more bits are set in the Standard Event Register (bits must be enabled, see \*ESE command). |
| 6 Master Status summary (Request for Service) | 64 | One or more bits are set in the Status Byte Register (bits must be enabled, see \*SRE command). Also used to indicate a request for service. |
| 7 Operation Status summary | 128 | One or more bits are set in the Standard Operation Register (bits must be enabled, see STATus:OPERation:ENABle command). |

All of the enabled events of the Standard Event Status Event Register are logically ORed to cause the Event Summary Bit (ESB) of the Status Byte Register to be set. All such enabled bits are then logically ORed to cause the MSS bit (bit 6) of the Status Byte Register to be set.

When the controller conducts a serial poll in response to SRQ, the RQS bit is cleared, but the MSS bit is not. When \*SRE is cleared (by programming it with 0), the power system cannot generate an SRQ to the controller.

The \*CLS (clear status) command will not clear the enable register but it does clear all bits in the event register.

A STATus:PRESet command does not clear the bits in the Status Byte register.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 3 (decimal value = 8) and bit 7 (decimal value = 128) are enabled, the query command will return " ".

```
+136
```

### Examples

The following command enables bit 4 (decimal value = 16) in the enable register.

```
*SRE 16
```

The following query returns which bits are enabled in the register.

```
*SRE?
```

Typical Response:

```
+16
```

### See Also

\*STB?

## \*STB?

### Syntax

```
*STB?
```

### Description

This query reads the Status Byte register, which contains the status summary bits and the Output Queue MAV bit. The Status Byte is a read-only register and the bits are not cleared when it is read.

> **NOTE** For more information on the SCPI Status System, see the Status System diagram

### Remarks

The following table lists the bit definitions for the Status Byte Register.

| Bit Number | Decimal Value | Definition |
|---|---|---|
| 0 Not Used | Not Used | 0 is returned. |
| 1 Not Used | Not Used | 0 is returned. |
| 2 Error Queue not empty | 4 | One or more errors have been stored in the Error Queue (see SYSTem:ERRor? command). |
| 3 Questionable Status summary | 8 | One or more bits are set in the Questionable Data Register (bits must be enabled, see STATus:QUEStionable:ENABle command). |
| 4 Message Available | 16 | Data is available in the instrument's output buffer. |
| 5 Event Status Byte summary | 32 | One or more bits are set in the Standard Event Register (bits must be enabled, see \*ESE command). |
| 6 Master Status summary (Request for Service) | 64 | One or more bits are set in the Status Byte Register (bits must be enabled, see \*SRE command). Also used to indicate a request for service. |
| 7 Operation Status summary | 128 | One or more bits are set in the Standard Operation Register (bits must be enabled, see STATus:OPERation:ENABle command). |

The input summary bits are cleared when the appropriate event registers are read. The MAV bit is cleared at power-on, by \*CLS, or when there is no more response data available.

A serial poll also returns the value of the Status Byte register, except that bit 6 returns Request for Service (RQS) instead of Master Status Summary (MSS). A serial poll clears RQS, but not MSS. When MSS is set, it indicates that the instrument has one or more reasons for requesting service.

### Return Format

\<NR1\> The value returned is the binary-weighted sum of all bits set in the register. For example, if bit 1 (decimal value = 2) and bit 4 (decimal value = 16) are set (and the corresponding bits are enabled), this command will return .

```
18
```

### Example

The following command reads the condition register (bits 3 and 4 are set).

```
*STB?
```

Typical Response:

```
+24
```

### See Also

\*SRE

## \*TRG

### Syntax

```
*TRG
```

### Description

This common command generates a trigger when the trigger subsystem has BUS selected as its source. The command has the same affect as the Group Execute Trigger (\<GET\>) command.

### Example

The following command generates a trigger.

```
*TRG
```

### See Also

INITiate[:IMMediate]:ACQuire INITiate[:IMMediate]:TRANsient INITiate[:IMMediate]:DLOG INITiate[:IMMediate]:ELOG

## \*TST?

### Syntax

```
*TST?
```

### Description

This query causes the instrument to do a self-test and report any errors.

A 0 indicates the instrument passed self-test. If all tests pass, you can have a high confidence that the instrument is operational.

### Remarks

If one or more tests fail, a 1 is returned and an error is stored in the error queue. For a complete listing of the error messages related to self-test failures, see SCPI Error Messages.

If one or more tests fail, see the Service Guide for instructions on returning the instrument to Keysight for service.

\*TST? also forces an \*RST command.

### Return Format

\<NR1\> The command returns 0 (all tests passed) or 1 (one or more tests failed).

### Example

The following command performs a self-test and returns a pass/fail indication.

```
*TST?
```

Typical Response:

```
+0
```

## \*WAI

### Syntax

```
*WAI
```

### Description

This command instructs the instrument not to process any further commands until all pending operations are completed. Pending operations are as defined under the \*OPC command.

### Remarks

\*WAI can be aborted only by sending the instrument a Device Clear command.

### Example

The following command waits for pending operations to complete.

```
*WAI
```

### See Also

\*OPC
