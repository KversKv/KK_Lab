# 6 SCPI Error Messages

This appendix gives the error numbers and descriptions that are returned by the Keysight N6705.

## Intoduction

The front-panel ERR annunciator turns on when one or more errors are currently stored in the error queue.

Errors are retrieved in first-in-first-out (FIFO) order. The first error returned is the first error that was stored.

Errors are cleared as you read them. When you have read all errors from the error queue, the ERR annunciator turns off and the errors are cleared.

If more errors have occurred than can fit in the buffer, the last error stored in the queue (the most recent error) is replaced with -350,"Error queue overflow". No additional errors are stored until you remove errors from the queue. If no errors have occurred when you read the error queue, the instrument responds with +0,"No error".

The error queue is cleared by the \*CLS (Clear Status) command and when power is cycled. The errors are also cleared when you read the error queue. The error queue is not cleared by a Factory Reset (\*RST command) or an Instrument Preset (SYSTem:PRESet command).

#### Front-Panel Operation:

If the ERR annunciator is on, press the Error key to view the errors. Use the navigation keys to scroll through the error list. All errors are cleared when you exit the menu.

#### Remote Interface Operation:

SYSTem:ERRor? Reads and clears one error from the queue Errors have the following format (the error string may contain up to 80 characters): -113,"Undefined header"

## Error List

Error Device-dependent Errors (these errors set Standard Event Status register bit #3)

0 No error This is the response to the ERR? query when there are no errors.

100 Too many channels You have specified more channels than are installed in the mainframe.

101 Calibration state is off Calibration is not enabled. The instrument will not accept calibration commands.

102 Calibration password is incorrect The calibration password is incorrect.

103 Calibration is inhibited by switch setting Calibration mode is locked out by the calibration switch.

104 Bad sequence of calibration commands Calibration commands have not been entered in the proper sequence.

105 Unexpected output current The measured output current is outside the acceptable range.

Device-dependent Errors (continued)

106 Zero measurement out of range error The “zero” measurement value is outside the acceptable range.

107 Programming cal constants out of range The programmed calibration constant is outside the acceptable range.

108 Measurement cal constants out of range The measurement calibration constant is outside the acceptable range.

109 Over voltage cal constants out of range The over voltage calibration constant is outside the acceptable range.

110 Wrong V+I The instrument was unable to set the correct voltage or current value.

111 Aux vloc cal constants out of range Calibration constants on the internal auxiliary local ADC are outside the acceptable range.

112 Aux vrem cal constants out of range Calibration constants on the internal auxiliary remote ADC are outside the acceptable range.

113 Aux imon cal constants out of range Calibration constants on the internal auxiliary imon ADC are outside the acceptable range.

114 Wrong status An incorrect status function has been reported.

115 Output track resistance out of range The output track resistance is out of range. Re-calibrate the output module.

116 Locked out by internal switch setting This function has been locked out by an internal switch in the mainframe.

117 Calibration error A calibration error has occurred. Do not save calibration constants. Try re-calibrating the unit.

200 Hardware error channel \<channel\> A hardware error has occurred on the specified channel.

201 Invalid configuration, empty slots There is an empty slot between modules. This configuration is not allowed.

202 Selftest Fail A selftest failure has occurred. See selftest failure list for details.

203 Compatibility function not implemented The requested compatibility function is not available.

204 NVRAM checksum error A checksum error has occurred in the instrument’s nonvolatile random access memory.

205 NVRAM full The nonvolatile random access memory of the instrument is full.

206 File not found The internal calibration file or the internal channel attribute file was not found in NVRAM.

207 Cal file version error The calibration file was written or read using old firmware. Firmware must be updated.

208 Running backup firmware The instrument is presently running the backup (previous) version of the firmware.

209 Modules do not match group NV config One or more modules that have their output coupled do not match the instrument state settings.

210 Frame NVRAM error A non-volatile RAM error has occurred in the mainframe

211 Output state couple modules do not match One or more modules in the group does not match the non-volatile configurations settings.

302 Option not installed The option that is programmed by this command is not installed.

Device-dependent Errors (continued) 303 There is not a valid acquisition to fetch from There is no valid data in the measurement buffer.

304 Volt and curr in incompatible transient modes Voltage and current cannot be in Step and List mode at the same time.

305 A triggered value is on a different range A triggered value is on a different range than the one that is presently set.

306 Too many list points Too many list points have been specified.

307 List lengths are not equivalent One or more lists are not the same length.

308 This setting cannot be changed while transient trigger is initiated Setting cannot be changed while the instrument is waiting for or executing a trigger sequence.

309 Cannot initiate, voltage and current in fixed mode Cannot initiate transient generator. Either the voltage or current function is set to Fixed mode.

310 The command is not supported by this model This power modules either does not have the hardware capability or the options required to support this command.

311 This group of channel has non-identical features One or more modules in this group does not match the ratings or options of the other modules.

312 The command is disabled when the channel is grouped This command is disabled when the output channel is grouped.

313 Datalog time interval is out of range The data log time interval is outside the programmable range.

314 Time of day clock has stopped The time of day clock has stopped. Replace the internal battery. See Service Guide.

315 Settings conflict error A data element could not be programmed because of the present instrument state.

316 Mass storage error The mass storage memory has been exceeded.

317 Invalid format An invalid data format was found in the command string.

318 Datalog error An error has occurred in the data returned by the datalogger.

319 Measurement is not allowed while datalogger is running You cannot make measurements in Meter View or Scope View while the datalogger is running.

320 Firmware update error This may be due to the instrument hardware not being able to support the firmware version.

321 Modules do not match data format One or more power modules does not match the data format of the file that is being loaded.

Command Errors (these errors set Standard Event Status register bit #5) − 100 Command error Generic syntax error.

− 101 Invalid character An invalid character was found in the command string.

− 102 Syntax error Invalid syntax was found in the command string. Check for blank spaces.

− 103 Invalid separator An invalid separator was found in the command string. Check for proper use of , ; :

− 104 Data type error A different data type than the one allowed was found in the command string.

Command Errors (continued)

− 105 GET not allowed A group execute trigger is not allowed in a command string.

− 108 Parameter not allowed More parameters were received than were expected.

− 109 Missing parameter Fewer parameters were received than were expected.

− 110 Command header error An error was detected in the header.

− 111 Header separator error A character that was not a valid header separator was found in the command string.

− 112 Program mnemonic too long The header contains more than 12 characters.

− 113 Undefined header A command was received that was not valid for this instrument.

− 114 Header suffix out of range The value of the numeric suffix is not valid.

− 120 Numeric data error Generic numeric data error.

− 121 Invalid character in number An invalid character for the data type was found in the command string.

− 123 Exponent too large The magnitude of the exponent was larger than 32000.

− 124 Too many digits The mantissa of a numeric parameter contained more than 255 digits, excluding leading zeros.

− 128 Numeric data not allowed A numeric parameter was received but a character string was expected.

− 130 Suffix error Generic suffix error

− 131 Invalid suffix A suffix was incorrectly specified for a numeric parameter.

− 134 Suffix too long The suffix contains more than 12 characters.

− 138 Suffix not allowed A suffix is not supported for this command.

− 140 Character data error Generic character data error

− 141 Invalid character data Either the character data element contains an invalid character, or the element is not valid.

− 144 Character data too long The character data element contains more than 12 characters.

− 148 Character data not allowed A discrete parameter was received, but a string or numeric parameter was expected.

− 150 String data error Generic string data error

− 151 Invalid string data An invalid character string was received. Check that the string is enclosed in quotation marks.

− 158 String data not allowed A character string was received, but is not allowed for this command.

− 160 Block data error Generic block data error Command Errors (continued)

− 161 Invalid block data The number of data bytes sent does not match the number of bytes specified in the header.

− 168 Block data not allowed Data was sent in arbitrary block format but is not allowed for this command.

− 170 Expression error Generic expression error

− 171 Invalid expression data The expression data element was invalid.

− 178 Expression data not allowed Expression data element was sent but is not allowed for this command.

Execution Errors (these errors set Standard Event Status register bit #4)

− 200 Execution error Generic syntax error

− 220 Parameter error A data element related error occurred.

− 221 Settings conflict A data element could not be executed because of the present instrument state.

− 222 Data out of range A data element could not be executed because the value was outside the valid range.

− 223 Too much data A data element was received that contains more data than the instrument can handle.

− 224 Illegal parameter value An exact value was expected but not received.

− 225 Out of memory The device has insufficient memory to perform the requested operation.

− 226 Lists not same length One or more lists are not the same length.

− 230 Data corrupt or stale Possible invalid data. A new reading was started but not completed.

− 231 Data questionable The measurement accuracy is suspect.

− 232 Invalid format The data format or structure is inappropriate.

− 233 Invalid version The version of the data format is incorrect to the instrument.

− 240 Hardware error The command could not be executed because of a hardware problem with the instrument.

− 241 Hardware missing The command could not be executed because of missing hardware, such as an option.

− 260 Expression error An expression program data element related error occurred.

− 261 Math error in expression An expression program data element could not be executed due to a math error.

Query Errors (these errors set Standard Event Status register bit #2)

− 400 Query Error Generic error query

− 410 Query INTERRUPTED A condition causing an interrupted query error occurred.

Query Errors (continued)

− 420 Query UNTERMINATED A condition causing an unterminated query error occurred.

− 430 Query DEADLOCKED A condition causing a deadlocked query error occurred.

− 440 Query UNTERMINATED after indefinite response A query was received in the same program message after a query indicating an indefinite response was executed.

Selftest Errors (these errors set Standard Event Status register bit #3)

202 Selftest Fail Aux Adc 0 expected \<n1\> to \<n2\>, measured \<n3\>, chan \<n4\> Auxiliary ADC failed. n1 and n2 are the expected limits. n3 is the measured value. n4 is the channel location of the failed module.

202 Selftest Fail DACs 0 expected \<n1\> to \<n2\>, measured \<n3\>, chan \<n4\> Both voltage and current DACs are at zero. n1 and n2 are the expected limits. n3 is the measured value. n4 is the channel location of the failed module.

202 Selftest Fail DACs 1 expected \<n1\> to \<n2\>, measured \<n3\>, chan \<n4\> Voltage DAC is at zero; current DAC is at full scale. n1 and n2 are the expected limits. n3 is the measured value. n4 is the channel location of the failed module.

202 Selftest Fail DACs 2 expected \<n1\> to \<n2\>, measured \<n3\>, chan \<n4\> Voltage DAC is at full scale; current DAC is at zero. n1 and n2 are the expected limits. n3 is the measured value. n4 is the channel location of the failed module.

202 Selftest Fail DACs 3 expected \<n1\> to \<n2\>, measured \<n3\>, chan \<n4\> Both voltage and current DACs are at full scale. n1 and n2 are the expected limits. n3 is the measured value. n4 is the channel location of the failed module.
