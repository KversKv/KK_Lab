# FORMat Commands Introduction

The FORMat commands let you specify the format for transferring measurement data.

| SCPI Command | Description |
|---|---|
| FORMat |  |
| [:DATA] ASCII \| REAL | Returns data as ASCII or binary |
| :BORDer NORMal \| SWAPped | Sets the byte order of the external data log data |

## FORMat[:DATA]

### Syntax

```
FORMat[:DATA] <type>
FORMat[:DATA]?
```

### Description

This command specifies the format of the data returned by queries that can return a block of data.

ASCII Numeric data is transferred as ASCII bytes in \<NR1\>, \<NR2\>, or \<NR3\> format as appropriate. The numbers are separated by commas.

REAL Data is returned in binary IEEE single precision floating point. In this case the 4 bytes of each value can be returned in either big-endian or little-endian byte order, determined by the FORMat:BORDer setting.

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<type\> | CPD | ASCII \| REAL | ASCII |

### Remarks

The data format is used when fetching data from SCPI measurements.

These include: FETC:ARR:CURR?, FETC:ARR:VOLT?, FETC:ELOG?,

ARB:CURR:CDW?, and ARB:VOLT:CDW?.

### Return Format

\<CRD\> The query command returns the data format setting.

### Examples

The following command sets the data format to ASCII.

```
FORM ASCII
```

The following query returns the data format setting.

```
FORM?
```

Typical Response: ASCII

### See Also

FORMat:BORDer

## FORMat:BORDer

### Syntax

```
FORMat:BORDer <setting>
FORMat:BORDer?
```

### Description

This command specifies how binary data is transferred. This only applies when the FORMat:DATA is set to REAL.

NORMal Binary data is transferred in normal order. The most significant byte is returned first, and the least significant byte is returned last (big-endian).

SWAPped Binary data is transferred in swapped-byte order. The least significant byte is returned first, and the most significant byte is returned last (little-endian).

### Parameters

| Name | Type | Range of Values | Default Value |
|---|---|---|---|
| \<setting\> | CPD | NORMal \| SWAPped | NORMal |

### Remarks

The byte order is used when fetching data from SCPI measurements.

These include: FETC:ARR:CURR?, FETC:ARR:VOLT?, FETC:ELOG?,

ARB:CURR:CDW?, and ARB:VOLT:CDW?.

### Return Format

\<CRD\> The query command returns the binary byte order setting.

### Examples

The following command sets the byte order setting to SWAPped.

```
FORM:BORD SWAP
```

The following query returns the byte order setting.

```
FORM:BORD?
```

Typical Response: SWAP

### See Also

FORMat[:DATA]
