# INITiate Subsystem Introduction

Initiate commands initialize the trigger system. This enables the trigger system to receive triggers.

| SCPI Command | Description |
|---|---|
| INITiate |  |
| [:IMMediate] |  |
| :ACQuire (@chanlist) | Enables measurement triggers |
| :DLOG \<“filename”\> | Enables the data logger function |
| :ELOG (@chanlist) | Enables external data logger measurements |
| :HISTogram (@chanlist) | Enables histogram measurements (N6781A, N6782A, N6785A, and N6786A) |
| :TRANsient (@chanlist) | Enables output triggers |
| :CONTinuous |  |
| :TRANsient \<Bool\>, | Enables/disables continuous transient triggers |
| (@chanlist) |  |

## INITiate[:IMMediate]:ACQuire

### Syntax

```
INITiate[:IMMediate]:ACQuire (@<chanlist>)
```

### Description

This command enables the measurement trigger system. When a measurement trigger is initiated, an event on a selected trigger source causes the specified triggering action to occur. If the trigger system is not initiated, all triggers are ignored.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

It takes a few milliseconds for the instrument to be ready to receive a trigger signal after receiving the INITiate:ACQuire command, and it can take longer if the value of SENSe:SWEep:OFFSet is negative.

If a trigger occurs before the trigger system is ready for it, the trigger will be ignored. The user can test the WTG_meas bit in the operation status register to know when the instrument is ready to receive a trigger after initiating.

### Example

The following command initiates the measurement trigger system on channel 1.

```
INIT:ACQ (@1)
```

### See Also

INITiate[:IMMediate]:TRANsient

TRIGger:ACQuire:SOURce

ABORt:ACQuire

## INITiate[:IMMediate]:DLOG

### Syntax

```
INITiate[:IMMediate]:DLOG <"filename">
```

### Description

This command initiates the data logger. When the data logger is initiated, an event on a selected data log trigger source starts a data log. If the data logger is not initiated, all triggers are ignored.

The filename in which to save the data should be the full path and filename. All data log files must have the extension .dlog

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename"\> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |

### Example

The following command initiates the data log and creates a file named data1.dlog in the instrument's internal file system.

```
INIT:DLOG "internal:\data1.dlog"
```

### See Also

TRIGger:DLOG[:IMMediate]

TRIGger:DLOG:SOURce

ABORt:DLOG

## INITiate[:IMMediate]:ELOG

### Syntax

```
INITiate[:IMMediate]:ELOG (@<chanlist>)
```

### Description

This command initiates an external data log. When the external data log is initiated, an event on a selected external data log trigger source starts the data log. If the external data log is not initiated, all triggers are ignored.

The external data log function is independent of the built-in data logger and is not displayed on the instrument's data logger view. All external data log functions are controlled using SCPI commands.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command initiates an external data log on channels 1 and 2.

```
INIT:ELOG (@1,2)
```

### See Also

TRIGger:ELOG[:IMMediate]

TRIGger:ELOG:SOURce

ABORt:ELOG

## INITiate[:IMMediate]:HISTogram

### Syntax

```
INITiate[:IMMediate]:HISTogram (@<chanlist>)
```

### Description

This command initiates a histogram current measurement. A histogram measurement provides a statistical measurement for profiling the signal levels of a sense function. The acquisition generates an array of frequency of occurrence vs. amplitude data that can be analyzed using a CCDF function. All histogram functions are controlled using SCPI commands.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed..

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command starts a histogram measurement on channels 1 and 2.

```
INIT:HIST (@1,2)
```

### See Also

TRIGger:HIST[:IMMediate]

TRIGger:HIST:SOURce

ABORt:HIST

## INITiate[:IMMediate]:TRANsient

### Syntax

```
INITiate[:IMMediate]:TRANsient (@<chanlist>)
```

### Description

This command enables the output trigger system. When an output trigger is initiated, an event on a selected trigger source causes the specified triggering action to occur. If the trigger system is not initiated, all triggers are ignored.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command initiates the transient trigger system on channel 1.

```
INIT:TRAN (@1)
```

### See Also

INITiate[:IMMediate]:ACQuire

ABORt:TRANsient

## INITiate:CONTinuous:TRANsient

### Syntax

```
INITiate:CONTinuous:TRANsient <Bool>, (@<chanlist>)
INITiate:CONTinuous:TRANsient? (@<chanlist>)
```

### Description

This command continuously initiates the output trigger system. This allows multiple triggers to generate multiple output transients with no intermediate commands. The enabled state is ON (1); the disabled state is OFF (0).

> **NOTE** With continuous triggering disabled, the output trigger system must be initiated for each trigger using the INITiate:TRANsient command.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<Bool\> | Boolean | OFF \| 0 \| ON \| 1 | OFF |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Return Format

\<NR1\> The query command returns 0 if continuous transients are disabled (OFF), and 1 if continuous transients are enabled (ON).

### Example

The following command continually initiates the transient trigger system on channel 1.

```
INIT:CONT:TRAN ON,(@1)
```

The following query returns the continuous transient trigger state.

```
INIT:CONT:TRAN? (@1)
```

Typical Response:

```
0
```

### See Also

INITiate[:IMMediate]:TRANsient

ABORt:TRANsient
