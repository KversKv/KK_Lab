# ABORt Commands Introduction

Abort commands cancel any triggered actions.

| SCPI Command | Description |
|---|---|
| ABORt |  |
| :ACQuire (@chanlist) | Resets the measurement trigger system to the Idle state |
| :DLOG | Stops the internal datalogger |
| :ELOG (@chanlist) | Stops the external datalogger |
| :HISTogram (@chanlist) | Stops the histogram current measurement (N6781A, N6782A, N6785A, N6786A) |
| :TRANsient (@chanlist) | Resets the transient trigger system to the Idle state |

## ABORt:ACQuire

### Syntax

```
ABORt:ACQuire (@<chanlist>)
```

### Description

This command cancels any triggered measurements and returns the trigger system back to the Idle state. It also resets the WTG-meas bit in the Condition Status register.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

ABORt:ACQuire is also executed at power-on and upon execution of the \*RST command.

### Example

The following command aborts the triggered action of channel 1.

```
ABOR:ACQ (@1)
```

### See Also

\*RST

ABORt:TRANsient

## ABORt:DLOG

### Syntax

```
ABORt:DLOG
```

### Description

This command stops the currently running data log and returns the trigger system back to the Idle state.

### Example

The following command stops the currently running data log.

```
ABOR:DLOG
```

## ABORt:ELOG

### Syntax

```
ABORt:ELOG (@<chanlist>)
```

### Description

This command stops the external data log and returns the trigger system back to the Idle state.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command stops the external data log on channel 1.

```
ABOR:ELOG (@1)
```

## ABORt:HISTogram

### Syntax

```
ABORt:HISTogram (@<chanlist>)
```

### Description

This command stops the histogram current measurement and returns the trigger system back to the Idle state.

> **NOTE** This command only applies to models N6781A, N6782A, N6785A, and N6786A that have the Data Logger function installed.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command stops the histogram measurement on channel 1.

```
ABOR:HIST (@1)
```

## ABORt:TRANsient

### Syntax

```
ABORt:TRANsient (@<chanlist>)
```

### Description

This command cancels any triggered actions and returns the trigger system back to the Idle state. ABORt:TRANsient also resets the WTG-tran bit in the Operation Condition Status register.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Remarks

If INITiate:CONTinuous:TRANsient ON has been programmed, ABORt does not turn off continuous triggers.

ABORt:TRANsient is also executed at power-on and upon execution of the \*RST command.

### Example

The following command aborts the triggered action of channel 1.

```
ABOR:TRAN (@1)
```

### See Also

\*RST

ABORt:ACQuire

INITiate:CONtinuous:TRANsient
