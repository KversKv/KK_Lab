# MMEMory Subsystem Introduction

MMEMory commands provide mass storage capability for output measurement data. The mass storage may be either internal or external to the instrument. The mass storage device is selected using the full path embedded within the filename. The filename parameter is a string.

| SCPI Command | Description |
|---|---|
| MMEMory |  |
| :ATTRibute? \<“object”\>, \<“attribute”\> | Gets the attributes of a file system object |
| :DATA [:DEFinite]? \<“filename”\> | Copies file contents; response is a definite length binary block |
| :DELete \<“filename”\> | Deletes a file |
| :EXPort |  |
| :DLOG \<“filename”\> | Exports a data log from the display to a file |
| :LOAD |  |
| :ARB |  |
| :SEQuence \<“filename”\>, (@chanlist) | Loads an Arb sequence |
| :STORe |  |
| :ARB |  |
| :SEQuence \<“filename”\>, (@chanlist) | Stores an Arb sequence |

## MMEMory:ATTRibute?

### Syntax

```
MMEMory:ATTRibute? <"object">, <"attribute">
```

### Description

This query returns the objects and attributes of a file system drive or of an individual file.

Objects "INTernal:" This object specifies the instrument's internal drive.

"EXTernal:" This object specifies the instrument's USB drive.

"\<filename\>" The filename object should be the full path and filename.

Attributes "DriveCapacity" This attribute specifies the capacity of the internal or external drive in bytes. Only applies when the object is INTernal: or EXTernal: "DriveFreeSpace" This attribute specifies the number of free bytes on the internal or external drive. Only applies when the object is INTernal: or EXTernal: "FileSize" This attribute specifies the size of the file or folder.

Only applies when the object is \<filename\>.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"object " \> | SPD | "INTernal:"\|"EXTernal:"\|"\<filename\>" Parameters must be enclosed in single or double quotes. | Required parameter |
| \<"attribute"\> | SPD | "DriveCapacity"\|"DriveFreeSpace" \|"FileSize" Parameters must be enclosed in single or double quotes. | Required parameter |

### Return Format

\<SRD\> The query command returns an ASCII string enclosed in double quotes containing the value of the specified attribute, or a blank string if the name of the attribute is not valid or an error has occurred.

### Examples

The following queries the internal drive description (quotes are also returned).

```
MMEM:ATTR? "INT:","DriveFreeSpace"
```

Typical Response:

```
"63422464"
```

The following queries the attributes of a data log file (quotes are also returned).

```
MMEM:ATTR? "INT:\datalog\data1.dlog","FileSize"
```

Typical Response:

```
"112770"
```

## MMEMory:DATA[:DEFinite]

### Syntax

```
MMEMory:DATA[:DEFinite] <"filename">, <data>
MMEMory:DATA[:DEFinite]? <"filename">
```

### Description

This command copies a file to the file system of the instrument. The filename should be the full path and filename. The query returns the contents of the specified file.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename " \> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |
| \<data\> | Block | \<data\> is a definite length arbitrary binary block of the form: #\<D\>\<DD...D\>\<data-bytes\> #\<D\> indicates the response is definite length with \<D\> indicating the number of digits are in the length field. \<DD...D\> indicates the length of the binary block containing the actual file. \<data-bytes\> are the contents of the file. | Required parameter |

### Return Format

\<Block\> The response is a definite length arbitrary binary block of the form: #\<D\>\<DD...D\>\<data-bytes\>

### Examples

The following copies a file and its contents to the file system.

```
MMEM:DATA "internal:\example.bin", <insert definite
length binary block here>
```

The following query returns the contents of the specified file.

```
MMEM:DATA? "internal:\example.bin"
```

## MMEMory:DELete

### Syntax

```
MMEMory:DELete <"filename">
```

### Description

This command deletes the specified file. The filename should be the full path and filename.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename " \> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |

### Examples

The following command deletes the file named data1.dlog.

```
MMEM:DEL "internal:\datalog\data1.dlog"
```

## MMEMory:EXPort:DLOG

### Syntax

```
MMEMory:EXPort:DLOG <"filename">
```

### Description

This command exports the data that is currently loaded in the instrument's datalog viewer to a file. The export filename should be the full path and filename. The exported data is in .csv (comma separated values) format .

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename " \> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |

### Example

The following command exports the data log file named data1.csv to the external USB drive.

```
MMEM:EXP:DLOG "external:\data1.csv"
```

## MMEMory:LOAD:ARB:SEQuence

### Syntax

```
MMEMory:LOAD:ARB:SEQuence <"filename">, (@<chanlist>)
```

### Description

This command loads an ARB sequence from a file. The filename should be the full path and filename. All ARB sequence data is saved in a proprietary format (.seq) which is not editable.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename"\> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |
| \<chanlist\> | Numeric | One or more channels. (@2) - channel 2 (@1,4) - channels 1 and 4 (@1:3) - channels 1 through 3. | Required parameter |

### Example

The following command loads the sequence file named data1.seq from the external USB drive to channel 1.

```
MMEM:LOAD:ARB:SEQ "external:\data1.seq",(@1)
```

## MMEMory:STORe:ARB:SEQuence

### Syntax

```
MMEMory:STORe:ARB:SEQuence <"filename">, (@<channel>)
```

### Description

This command stores an ARB sequence to a file. The filename should be the full path and filename. All ARB sequence data is saved in a proprietary format (.seq) which is not editable.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<"filename " \> | SPD | Filename and path must be enclosed in single or double quotes. | Required parameter |
| \<channel\> | NR1 | An ARB sequence can only be saved from one channel at a time. | Required parameter |

### Example

The following command stores the sequence file named data1.seq from channel 1 to the external USB drive.

```
MMEM:STOR:ARB:SEQ "external:\data1.seq",(@1)
```
