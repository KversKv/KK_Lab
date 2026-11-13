# HCOPy Commands Introduction

HCOPy commands provide screen shots of the front panel display.

| SCPI Command | Description |
|---|---|
| HCOPy:SDUMp:DATA? | Returns an image of the display in .gif format |

## HCOPy:SDUMp:DATA?

### Syntax

```
HCOPy:SDUMp:DATA?
```

### Description

This query returns the front panel LCD image formatted as a compressed GIF (graphical image file). The size of the compressed image is approximately 5k bytes.

### Return Format

\<Block\> The response is an indefinite length arbitrary binary block of the form: #0\<data-bytes\>NL^END #0 indicates the response is an indefinite length. The end of the block is a newline with EOI asserted.

### Example

The following query returns the LCD image.

```
HCOP:SDUM:DATA?
```
