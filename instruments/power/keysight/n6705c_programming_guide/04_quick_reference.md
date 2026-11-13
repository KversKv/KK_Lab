# 4 Command Quick Reference

## SCPI Command Summary

> **NOTE** Some [optional] commands have been included for clarity. All settings commands have a corresponding query. Not all commands apply to all models.

| SCPI Command | Description |
|---|---|
| ABORt |  |
| :ACQuire (@chanlist) | Resets the measurement trigger system to the Idle state |
| :DLOG | Stops the internal data logger |
| :ELOG (@chanlist) | Stops the external data logger |
| :HISTogram (@chanlist) | Stops the histogram current measurement |
| :TRANsient (@chanlist) | Resets the transient trigger system to the Idle state |
| CALibrate |  |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@channel) | Calibrates the output current programming |
| :LIMit |  |
| :NEGative \<NRf\>, (@channel) | Calibrates the negative current limit (only on N6783A) |
| :POSitive \<NRf\>, (@channel) | Calibrates the positive current limit (only on N678xA SMU) |
| :MEASure \<NRf\>, (@channel) | Calibrates the current measurement |
| :PEAK (@channel) | Calibrates the peak current limit (only on N675xA, N676xA) |
| :DATA \<NRf\> | Enters the calibration value |
| :DATE \<”date”\>, (@channel) | Sets the calibration date |
| :DPRog (@channel) | Calibrates the current downprogrammer |
| :LEVel P1 \| P2 \| P3 | Advances to the next calibration step |
| :PASSword \<NRf\> | Sets the numeric calibration password |
| :RESistance 20\| 6, (@channel) | Calibrates the output resistance (only on N6781/85A) |
| :SAVE | Saves the new cal constants in non-volatile memory |
| :STATE \<Bool\> [,\<NRf\>] | Enables/disables calibration mode |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@channel) | Calibrates the output voltage programming |
| :CMRR (@channel) | Calibrates common mode rejection ratio (only N675xA, N676xA) |
| :LIMit |  |
| :POSitive \<NRf\>, (@channel) | Calibrates the positive voltage limit (only on N678xA SMU) |
| :MEASure \<NRf\>, (@channel) | Calibrates the voltage measurement |
| :AUXiliary (@channel) | Calibrates the auxiliary voltage measurement (only N6781/85A) |
| DISPlay |  |
| [:WINDow] |  |
| :VIEW METER1 \| METER4 | Selects 1-channel or 4-channel meter view |
| FETCh |  |
| [:SCALar] |  |
| :CURRent |  |
| [:DC]? (@chanlist) | Returns the average current |
| :ACDC? (@chanlist) | Returns the total rms current (AC + DC) |
| :HIGH? (@chanlist) | Returns the high level of a current pulse |
| :LOW? (@chanlist) | Returns the low level of a current pulse |
| :MAXimum? (@chanlist) | Returns the maximum current |
| :MINimum? (@chanlist) | Returns the minimum current |
| :POWer |  |
| [:DC]? (@chanlist) | Returns the average output power |

| SCPI Command | Description |
|---|---|
| FETCh[:SCALar] (continued) |  |
| :VOLTage |  |
| [:DC]? (@chanlist) | Returns the average voltage |
| :ACDC? (@chanlist) | Returns the total rms voltage (AC + DC) |
| :HIGH? (@chanlist) | Returns the high level of a voltage pulse |
| :LOW? (@chanlist) | Returns the low level of a voltage pulse |
| :MAXimum? (@chanlist) | Returns the maximum voltage |
| :MINimum? (@chanlist) | Returns the minimum voltage |
| :ARRay |  |
| :CURRent [:DC]? (@chanlist) | Returns the instantaneous output current |
| :POWer [:DC]? (@chanlist) | Returns the instantaneous output power |
| :VOLTage [:DC]? (@chanlist) | Returns the instantaneous output voltage |
| :DLOG |  |
| :AHOur? (@chanlist) | Returns the amp-hours between markers |
| :CURRent |  |
| [:DC]? (@chanlist) | Returns the average current between markers |
| :MAXimum? (@chanlist) | Returns the maximum current between markers |
| :MINimum? (@chanlist) | Returns the minimum current between markers |
| :PTPeak? (@chanlist) | Returns the peak-to-peak current between markers |
| :VOLTage |  |
| [:DC]? (@chanlist) | Returns the average voltage between markers |
| :MAXimum? (@chanlist) | Returns the maximum voltage between markers |
| :MINimum? (@chanlist) | Returns the minimum voltage between markers |
| :PTPeak? (@chanlist) | Returns the peak-to-peak voltage between markers |
| :WHOur? (@chanlist) | Returns the watt-hours between markers |
| :ELOG \<NR1\>, (@chanlist) | Returns the most recent external data log records |
| :HISTogram |  |
| :CURRent? 8 \| 0.0039, (@chanlist) | Returns the cumulative histogram current data (N6781/82/85/86A) |
| FORMat |  |
| [:DATA] ASCII \| REAL | Returns data as ASCII or binary |
| :BORDer NORMal \| SWAPped | Sets the byte order of the external data log data |
| HCOPy:SDUMp:DATA? | Returns an image of the display in .gif format |
| INITiate |  |
| [:IMMediate] |  |
| :ACQuire (@chanlist) | Enables measurement triggers |
| :DLOG \<“filename”\> | Enables the data logger function |
| :ELOG (@chanlist) | Enables external data logger measurements |
| :HISTogram (@chanlist) | Enables histogram measurements (only on N6781/82/85/86A) |
| :TRANsient (@chanlist) | Enables output triggers |
| :CONTinuous |  |
| :TRANsient \<Bool\>, (@chanlist) | Enables/disables continuous transient triggers |
| MEASure |  |
| [:SCALar] |  |
| :CURRent |  |
| [:DC]? (@chanlist) | Takes a measurement; returns the average current |
| :ACDC? (@chanlist) | Takes a measurement; returns the total rms current (AC + DC) |
| :HIGH? (@chanlist) | Takes a measurement; returns the high level of a current pulse |
| :LOW? (@chanlist) | Takes a measurement; returns the low level of a current pulse |
| :MAXimum? (@chanlist) | Takes a measurement; returns the maximum current |
| :MINimum? (@chanlist) | Takes a measurement; returns the minimum current |

| SCPI Command | Description |
|---|---|
| MEASure[:SCALar] (continued) |  |
| :POWer |  |
| [:DC]? (@chanlist) | Takes a measurement, returns the average output power |
| :VOLTage |  |
| [:DC]? (@chanlist) | Takes a measurement; returns the average voltage |
| :ACDC? (@chanlist) | Takes a measurement; returns the total rms voltage (AC + DC) |
| :HIGH? (@chanlist) | Takes a measurement; returns the high level of a voltage pulse |
| :LOW? (@chanlist) | Takes a measurement; returns the low level of a voltage pulse |
| :MAXimum? (@chanlist) | Takes a measurement; returns the maximum voltage |
| :MINimum? (@chanlist) | Takes a measurement; returns the minimum voltage |
| :ARRay |  |
| :CURRent [:DC]? (@chanlist) | Takes a measurement; returns the instantaneous output current |
| :POWer [:DC]? (@chanlist) | Takes a measurement; returns the instantaneous output power |
| :VOLTage [:DC]? (@chanlist) | Takes a measurement; returns the instantaneous output voltage |
| MMEMory |  |
| :ATTRibute? \<“object”\>, \<“attribute”\> | Gets the attributes of a file system object |
| :DATA [:DEFinite]? \<“filename”\> | Copies file contents; response is a definite length binary block |
| :DELete \<“filename”\> | Deletes a file |
| :EXPort |  |
| :DLOG \<“filename”\> | Exports a data log from the display to a file |
| :LOAD |  |
| :ARB:SEQuence \<“filename”\>, (@chanlist) | Loads an Arb sequence |
| :STORe |  |
| :ARB:SEQuence \<“filename”\>, (@chanlist) | Stores an Arb sequence |
| OUTPut |  |
| [:STATe] \<Bool\> [,NORelay], (@chanlist) | Enables/disables the specified output channel(s) |
| :COUPle |  |
| :CHANNel [\<NR1\> {,\<NR1\>}] | Selects which channels are coupled |
| :DOFFset \<NRf\> | Specifies a maximum delay offset to synchronize output changes |
| :MODE AUTO \| MANual | Specifies the output delay coupling mode |
| :MAX |  |
| :DOFFset? | Returns the maximum delay offset required for a mainframe |
| :DELay |  |
| :FALL \<NRf+\>, (@chanlist) | Sets the output turn-off sequence delay |
| :RISE \<NRf+\>, (@chanlist) | Sets the output turn-on sequence delay |
| :PMODe VOLTage \| CURRent, (@chanlist) | Sets the mode for turn on/off transitions (N6761A, N6762A) |
| :TMODe HIGHZ \| LOWZ, (@chanlist | Specifies the turn-off output impedance (only on N678xA SMU) |
| :INHibit |  |
| :MODE LATChing \| LIVE \| OFF | Sets the remote inhibit input |
| :PON |  |
| :STATe RST \| RCL0 | Programs the power-on state |
| :PROTection |  |
| :CLEar (@chanlist) | Resets latched protection |
| :COUPle \<Bool\> | Enables/disables channel coupling for protection faults |
| :DELay \<NRf+\>, (@chanlist) | Sets the over-current protection programming delay |
| :OSCillation[:STATe] \<Bool\>, (@chanlist) | Enables/disables output oscillation protection (N678xA SMU) |
| :WDOG |  |
| [:STATe] \<Bool\> | Enables/disables the I/O watchdog timer |
| :DELay \<NRf+\> | Sets watchdog timer delay |
| :RELay |  |
| :POLarity NORMal \| REVerse, (@chanlist) | Sets the output relay polarity (only on option 760) |

| SCPI Command | Description |
|---|---|
| SENSe |  |
| :CURRent |  |
| :CCOMpensate \<Bool\>, (@chanlist) | Enables/disables the capacitive current compensation |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Selects the current measurement range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :DLOG |  |
| :CURRent |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the internal data log current range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current data logging |
| :MINMax \<Bool\> | Enables/disables min/max data logging |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables voltage data logging |
| :MARKer\<1,2\> |  |
| :POINt \<NRf+\> | Positions the data log markers |
| :OFFSet \<NR1\> | Sets trigger offset as a percent from start of data log duration |
| :PERiod \<NRf+\> | Sets the interval between samples (replaces TINTerval) |
| :TIME \<NRf+\> | Sets the duration of the data log in seconds |
| :TINTerval \<NRf+\> | Sets the interval between samples (for backward compatibility) |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the internal data log voltage range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :ELOG |  |
| :CURRent |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the external data log current range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables external current data logging |
| :MINMax \<Bool\>, (@chanlist) | Enables/disables external min/max current data logging |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables external voltage data logging |
| :MINMax \<Bool\>, (@chanlist) | Enables/disables external min/max voltage data logging |
| :PERiod \<NR1\>, (@chanlist) | Sets the integration time of the external data logging |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the external data log voltage range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :FUNCtion “VOLTage”\|”CURRent” \| “NONE”, (@chanlist) | Enables the measurement function (for backward compatibility) |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current measurements (replaces FUNCtion) |
| :VOLTage \<Bool\>, (@chanlist) | Enables/disables voltage measurements (replaces FUNCtion) |
| :INPut MAIN \| AUXiliary, (@chanlist) | Selects the voltage measurement input (only on N6781/85A) |
| :HISTogram |  |
| :CURRent |  |
| [:DC]:BIN |  |
| :GAIN? 8 \| 0.0039, (@chanlist) | Queries the LSB weight of the histogram (N6781/82/85/86A) |
| :OFFSet? 8 \| 0.0039, (@chanlist) | Queries the weight of the histogram (N6781/82/85/86A) |
| :RANGes? (@chanlist) | Queries the values of the bin ranges (N6781/82/85/86A) |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Sets the measurement range of the histogram (N6781/82/85/86A) |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :FUNCtion |  |
| :CURRent \<Bool\>, (@chanlist) | Enables/disables current histogram (only on N6781/82/85/86A) |
| :SWEep |  |
| :OFFSet |  |
| :POINts \<NRf+\>, (@chanlist) | Defines the trigger offset in the measurement sweep |
| :POINts \<NRf+\>, (@chanlist) | Defines the number of data points in the measurement |
| :TINTerval \<NRf+\>, (@chanlist) | Sets the measurement sample interval |
| :RESolution RES20 \| RES40 | Sets the measurement resolution |

| SCPI Command | Description |
|---|---|
| SENSe:continued) |  |
| :VOLTage |  |
| [:DC]:RANGe |  |
| [:UPPer] \<NRf+\>, (@chanlist) | Selects the voltage measurement range |
| :AUTO \<Bool\>, (@chanlist) | Enables/disables measurement autoranging (N6781/82/85/86A) |
| :WINDow |  |
| [:TYPE] HANNing \| RECTangular, (@chanlist) | Selects the window type |
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
| :TERMinate:LAST \<Bool\>, (@chanlist) | Sets the Arb termination mode |
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

| SCPI Command | Description |
|---|---|
| [SOURce:]CURRent (continued) |  |
| :SLEW |  |
| [:IMMediate] \<NRf+\> \| INFinity, (@chanlist) | Sets the output current slew rate (N678xA SMU) |
| MAXimum \<Bool\>, (@chanlist) | Enables/disables the maximum slew rate override (N678xA SMU) |
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
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the output resistance (only on N6781/85A) |
| :STATe \<Bool\>, (@chanlist) | Enables/disables output resistance programming (N6781/85A) |
| [SOURce:]STEP |  |
| :TOUTput \<Bool\>, (@chanlist) | Generate a trigger output on the voltage or current step |
| [SOURce:]VOLTage |  |
| [:LEVel] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the output voltage |
| :TRIGgered [:AMPLitude] \<NRf+\>, (@chanlist) | Sets the triggered output voltage |

| SCPI Command | Description |
|---|---|
| [SOURce:]VOLTage (continued) |  |
| :BWIDth LOW \| HIGH1 \| HIGH2 \| HIGH3, (@chanlist) | Sets the voltage bandwidth (only on N678xA SMU) |
| :LIMit |  |
| [:POSitive] |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the positive voltage limit (only on N678xA SMU) |
| :COUPle \<Bool\>, (@chanlist) | Sets the voltage limit tracking state (only on N6784A) |
| :NEGative |  |
| [:IMMediate][:AMPLitude] \<NRf+\>, (@chanlist) | Sets the negative voltage limit (only on N6784A) |
| :MODE FIXed \| STEP \| LIST \| ARB, (@chanlist) | Sets the voltage trigger mode |
| :PROTection |  |
| [:LEVel] \<NRf+\>, (@chanlist) | Sets the over-voltage protection level |
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
| STATus |  |
| :OPERation |  |
| [:EVENt]? (@chanlist) | Returns the value of the operation event register |
| :CONDition? (@chanlist) | Returns the value of the operation condition register |
| :ENABle \<NRf\>, (@chanlist) | Enables specific bits in the event register |
| :NTRansition \<NRf\>, (@chanlist) | Sets the negative transition filter |
| :PTRansition \<NRf\>, (@chanlist) | Sets the positive transition filter |
| :PRESet | Presets all enable and transition registers to power-on |
| :QUEStionable |  |
| [:EVENt]? (@chanlist) | Returns the value of the questionable event register |
| :CONDition? (@chanlist) | Returns the value of the questionable condition register |
| :ENABle \<NRf\>, (@chanlist) | Enables specific bits in the event register |
| :NTRansition \<NRf\>, (@chanlist) | Sets the negative transition filter |
| :PTRansition \<NRf\>, (@chanlist) | Sets the positive transition filter |
| SYSTem |  |
| :CHANnel |  |
| [:COUNt]? | Returns the number of output channels in a mainframe |
| :MODel? (@chanlist) | Returns the model number of the selected channel |
| :OPTion? (@chanlist) | Returns the option installed in the selected channel |
| :SERial? (@chanlist) | Returns the serial number of the selected channel |
| :COMMunicate |  |
| :RLSTate LOCal \| REMote \| RWLock | Specifies the Remote/Local state of the instrument |
| :TCPip:CONTrol? | Returns the control connection port number |
| :DATE \<yyyy\>,\<mm\>,\<dd\> | Sets the date of the system clock |
| :ERRor? | Returns the error number and error string |
| :GROup |  |
| :CATalog? | Returns the groups that have been defined (NOT for N678xA SMU) |
| :DEFine (@chanlist) | Group channels to create a single output (NOT for N678xA SMU) |
| :DELete \<channel\> | Deletes the specified channel from a group (NOT for N678xA SMU) |
| :ALL | Ungroups all channels (NOT for N678xA SMU) |
| :PASSword:FPANel:RESet | Resets the front panel lock password to zero |
| :REBoot | Returns the unit to its power-on state |
| :TIME \<hh\>,\<mm\>,\<ss\> | Sets the time of the system clock |
| :VERSion? | Returns the SCPI version number |

| SCPI Command | Description |
|---|---|
| TRIGger |  |
| :ACQuire |  |
| [:IMMediate] (@chanlist) | Triggers the measurement immediately |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the current trigger level |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the current trigger slope |
| :SOURce \<source\>, (@chanlist) | Sets the measurement trigger source \<source\> = BUS, CURRent\<n\>,EXTernal, PIN\<n\>, TRANsient\<n\>, VOLTage\<n\> |
| :TOUTput |  |
| [:ENABle] \<Bool\>, (@chanlist) | Enables measurement triggers to be sent to a digital port pin |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the voltage trigger level |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the voltage trigger slope |
| :ARB:SOURce BUS \| IMMediate \| EXTernal | Sets the arbitrary waveform trigger source |
| :DLOG |  |
| [:IMMediate] | Triggers the internal data logger immediately |
| :CURRent |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the current trigger level of the data logger |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the current trigger slope of the data logger |
| :SOURce \<source\> | Sets the internal data logger trigger source \<source\> = BUS, CURRent\<n\>, EXTernal, IMMediate, VOLTage\<n\>, ARSK, OOOK |
| :VOLTage |  |
| [:LEVel] \<NRf\>, (@chanlist) | Sets the voltage trigger level of the data logger |
| :SLOPe POSitive \| NEGative, (@chanlist) | Sets the voltage trigger slope of the data logger |
| :ELOG |  |
| [:IMMediate] (@chanlist) | Triggers the external data logger immediately |
| :SOURce \<source\>, (@chanlist) | Sets the external data logger trigger source \<source\> = BUS, EXTernal, IMMediate, PIN\<n\> |
| :HISTogram |  |
| [:IMMediate] (@chanlist) | Triggers the current histogram immediately (N6781/82/85/86A) |
| :SOURce \<source\>, (@chanlist) | Sets the current histogram trigger source (N6781/82/85/86A) \<source\> = BUS, EXTernal, IMMediate, PIN\<n\> |
| :TRANsient |  |
| [:IMMediate] (@chanlist) | Triggers the output immediately |
| :SOURce \<source\>, (@chanlist) | Sets the output trigger source \<source\> = BUS, EXTernal, IMMediate, PIN\<n\>, TRANsient\<n\> |
| Common Command Description |  |
| \*CLS Clear status |  |
| \*ESE \<NRf\> Standard event status | enable |
| \*ESR? Return event status | register |
| \*IDN? Return instrument identification |  |
| \*OPC Enable "operation complete" | bit in ESR |
| \*OPT? Return option number |  |
| \*RCL \<NRf\> Recalls a saved instrument | state |
| \*RDT? Return output channel | descriptions |
| \*RST Reset |  |
| \*SAV \<NRf\> Saves an instrument | state |
| \*SRE \<NRf\> Set service request | enable register |
| \*STB? Return status byte |  |
| \*TRG Trigger |  |
| \*TST? Performs self-test, then | returns result |
| \*WAI Pauses additional command | processing until all device commands are done |

## Non-Volatile Settings

The following tables show the factory-shipped non-volatile settings of the instrument. Information in non-volatile memory is NOT lost when power is turned off. These settings are all customer-configurable.

The factory-shipped LAN settings can be restored by selecting the front panel Reset control located in the System\\I/O\\LAN\\Config\\Reset menu.

All non-volatile settings including LAN, can be restored by selecting the front panel Reset control located in the System\\Admin\\Nvram menu

Factory-shipped non-volatile LAN settings Get IP Address Automatic Dynamic DNS naming service Enabled IP Address 169.254.67.5 NetBIOS naming service Enabled Subnet Mask 255.255.0.0 Domain name Blank Default Gateway 0.0.0.0 TCP keepalive Enabled Obtain DNS server from DHCP Enabled TCP keepalive seconds 1800 DNS server Blank Ethernet Auto-negotiation Enabled Host name A-N6705B-xxxxx Ping server Enabled Web password Blank

Other factory-shipped non-volatile settings Admin/Calibration password 0 (zero) LAN interface Enabled Calibration date March 5, 2007 Output Inhibit mode Off Channel grouping No groups Saved states \*RST command Digital port function (all pins) Digital In Voltage and Current knobs Unlocked Digital port polarity (all pins) Positive Screen saver Enabled Front panel lockout Disabled Screen saver delay 60 minutes Front panel meter view 1-channel USB interface Enabled GPIB Address 5 Wake on I/O Enabled Key clicks Enabled Web server Enabled

## Reset Settings (\*RST)

These settings are set by the Reset (\*RST) command ARB:COUNt 1 ARB:FUNCtion:SHAPe NONE

ARB:CURRent|VOLTage:CDWell:DWELl 0.001 ARB:FUNCtion:TYPE VOLT

ARB:CURRent|VOLTage:CDWell:LEVel MIN ARB:SEQuence:COUNt 1

ARB:CURRent|VOLTage:EXPonential:END MIN ARB:SEQuence:STEP:COUNt 1

ARB:CURRent|VOLTage:EXPonential:STARt MIN ARB:SEQuence:STEP:FUNCtion:SHAPe PULS

ARB:CURRent|VOLTage:EXPonential:STARt:TIMe 0 ARB:SEQuence:STEP:PACing DWEL

ARB:CURRent|VOLTage:EXPonential:TCONstant 1 ARB:SEQuence:TERMinate:LAST ON

ARB:CURRent|VOLTage:EXPonential:TIMe 1 ARB:TERMinate:LAST OFF

ARB:CURRent|VOLTage:PULSe:END 0 CALibrate:STATe OFF

ARB:CURRent|VOLTage:PULSe:STARt MIN CURRent 0.08 or MIN

ARB:CURRent|VOLTage:PULSe:STARt:TIMe 0 CURRent:LIMit MAX

ARB:CURRent|VOLTage:PULSe:TOP MIN CURRent:LIMit:COUPle ON

ARB:CURRent|VOLTage:PULSe:TOP:TIMe 1 CURRent:LIMit:NEGative MIN

ARB:CURRent|VOLTage:RAMP:END MIN CURRent:MODE FIX

ARB:CURRent|VOLTage:RAMP:END:TIMe 0 CURRent:PROTection:DELay 0.02

ARB:CURRent|VOLTage:RAMP:RTIMe 1 CURRent:PROTection:DELaySTARt SCH

ARB:CURRent|VOLTage:RAMP:STARt MIN CURRent:PROTection:STATe OFF

ARB:CURRent|VOLTage:RAMP:STARt:TIMe 0 CURRent:RANGe MAX

ARB:CURRent|VOLTage:SINusoid:AMPLitude MIN CURRent:TRIGger MIN

ARB:CURRent|VOLTage:SINusoid:FREQuency 1 CURRent:SLEW 9.9E+37

ARB:CURRent|VOLTage:SINusoid:OFFSet 0 CURRent:SLEW:MAX ON

ARB:CURRent|VOLTage:STAircase:END 0 DIGital:OUTPut:DATA 0

ARB:CURRent|VOLTage:STAircase:END:TIMe MIN DISPlay:VIEW METER1

ARB:CURRent|VOLTage:STAircase:NSTeps 10 EMULation PS4Q (N6784A); PS2Q (N6781A, N6782A)

ARB:CURRent|VOLTage:STAircase:STARt MIN FUNCtion VOLT

ARB:CURRent|VOLTage:STAircase:STAR:TIMe 0 FORMat:DATA ASCII

ARB:CURRent|VOLTage:STAircase:TIMe 1 FORMat:BORDer NORM

ARB:CURRent|VOLTage:STEP:END MIN INITiate:CONTinuous:TRANsient OFF

ARB:CURRent|VOLTage:STEP:STARt MIN LIST:COUNt 1

ARB:CURRent|VOLTage:STEP:STARt:TIMe 0 LIST:CURRent MIN

ARB:CURRent|VOLTage:TRAPezoid:END:TIMe 0 LIST:DWELl 0.001

ARB:CURRent|VOLTage:TRAPezoid:FTIMe 1 LIST:STEP AUTO

ARB:CURRent|VOLTage:TRAPezoid:RTIMe 1 LIST:TERMinate:LAST OFF

ARB:CURRent|VOLTage:TRAPezoid:STARt MIN LIST:TOUTput:BOST OFF

ARB:CURRent|VOLTage:TRAPezoid:STARt:TIMe 0 LIST:TOUTput:EOST OFF

ARB:CURRent|VOLTage:TRAPezoid:TOP MIN LIST:VOLTage MIN

ARB:CURRent|VOLTage:TRAPezoid:TOP:TIMe 1 OUTPut OFF

ARB:CURRent|VOLTage:UDEFined:BOSTep OFF OUTPut:DELay:FALL 0

ARB:CURRent|VOLTage:UDEFined:DWELl 0.001 OUTPut:DELay:RISE 0

ARB:CURRent|VOLTage:UDEFined:LEVel MIN OUTPut:PMODe VOLT These settings are set by the Reset (\*RST) command OUTPut:PROTection:COUPle OFF SENSe:SWEep:OFFSet:POINts 0

OUTPut:PROTection:DELay 0.02 SENSe:SWEep:TINTerval 20.48E  6

OUTPut:PROTection:OSCillation ON SENSe:SWEep:TINTerval:RESolution RES20

OUTPut:PROTection:WDOG OFF SENSe:VOLTage:RANGe MAX

OUTPut:RELay:POLarity NORM SENSe:VOLTage:RANGe;AUTO OFF

OUTPut:TMODe LOWZ SENSe:WINDow RECT

POWer:LIMit MAX STEP:TOUTput FALSE RESistance 0 TRIGger:ACQuire:CURRent MIN

RESistance:STATe OFF TRIGger:ACQuire:CURRent:SLOPe POS

SENSe:CURRent:CCOMpensate ON TRIGger:ACQuire:SOURce BUS

SENSe:CURRent:RANGe MAX TRIGger:ACQuire:TOUTput OFF

SENSe:CURRent:RANGe:AUTO OFF TRIGger:ACQuire:VOLTage MIN

SENSe:DLOG:CURRent:RANGe:AUTO OFF TRIGger:ACQuire:VOLTage:SLOPe POS

SENSe:DLOG:FUNCtion:CURRent OFF TRIGger:ARB:SOURce IMM

SENSe:DLOG:FUNCtion:MINMax OFF TRIGger:DLOG:CURRent MIN

SENSe:DLOG:FUNCtion:VOLTage ON TRIGger:DLOG:CURRent:SLOPe POS

SENSe:DLOG:OFFset 0 TRIGger:DLOG:SOURce IMM

SENSe:DLOG:TINTerval 0.1 TRIGger:DLOG:VOLTage MIN

SENSe:DLOG:TIME 30 TRIGger:DLOG:VOLTage:SLOPe POS

SENSe:DLOG:VOLTage:RANGe:AUTO OFF TRIGger:ELOG:SOURce BUS

SENSe:ELOG:CURRent:RANGe:AUTO OFF TRIGger:HISTogram:SOURce BUS

SENSe:ELOG:FUNCtion:CURRent ON TRIGger:TRANsient:SOURce BUS

SENSe:ELOG:FUNCtion:CURRent:MINMax OFF VOLTage MIN

SENSe:ELOG:FUNCtion:VOLTage OFF VOLTage:BWIDth LOW

SENSe:ELOG:FUNCtion:VOLTage: MINMax OFF VOLTage:LIMit MAX

SENSe:ELOG:PERiod 0.1 VOLTage:LIMit:COUPle ON

SENSe:ELOG:VOLTage:RANGe:AUTO OFF VOLTage:LIMit:NEGative MIN

SENSe:FUNCtion “VOLT” VOLTage:MODE FIX

SENSe:FUNCtion:CURRent OFF VOLTage:PROTection:DELay 0

SENSe:FUNCtion:VOLTage ON VOLTage:PROTection:REMote MAX

SENSe:FUNCtion:VOLTage:INPut MAIN VOLTage:PROTection:REMote:NEGative MIN

SENSe:HISTogram:CURRent:RANGe MAX VOLTage:RANGe MAX

SENSe:HISTogram:CURRent:RANGe:AUTO OFF VOLTage:SLEW 9.9E+37

SENSe:HISTogram:FUNCtion:CURRent ON VOLTage:SLEW:MAX ON

SENSe:SWEep:POINts 1024 or 4883 VOLTage:TRIGger MIN

## Keysight N6784A SMU Initial Emulation Mode Settings

The following tables document the emulation mode settings that are applied when the emulation mode is selected. Emulation mode settings are not saved.

4 Quadrant Power 2 Quadrant Power 1 Quadrant Power Supply 1 Supply Supply

Priority mode voltage current voltage current voltage current Quadrants 4 4 2 2 1 1 Voltage range 6.12 V n/a 6.12 V n/a 6.12 V n/a Voltage 0 V n/a 0 V n/a 0 V n/a I limit range 3.06 A n/a 3.06 A 3 n/a 3.06 A 3 n/a +I limit 3.06 A n/a 3.06 A 3 n/a min n/a − I limit − 3.06 A n/a − 3.06 A 3 n/a − 0.612 A n/a Current range n/a 3.06 A n/a 3.06 A 3 n/a 3.06 A 3 Current n/a 0 A n/a 0 A n/a 0 A V limit range n/a 6.12 V n/a 6.12 V n/a 6.12 V +V limit n/a 6.12 V n/a 6.12 V n/a 6.12 V − V limit 1 n/a − 6.12 V n/a min n/a min Output resistance 2 0 Ω /off n/a 0 Ω /off n/a 0 Ω /off n/a Output state off off off off off off I limit tracking on on on off off off V limit tracking 1 on on off off off off

Battery Battery CC Load CV Load Voltmeter Ammeter Emulator 2 Charger 2

Priority mode voltage Voltage current voltage current voltage Quadrants 2 1 1 1 4 4 Voltage range 6.12 V 6.12 V n/a 6.12 V n/a lowest Voltage 0 V 0 V n/a 5 mV 0 V 0 V I limit range 3.06 A 3 3.06 A 3 n/a 3.06 A 3 n/a 3.06 A 3 +I limit 3.06 A 3 min n/a min n/a 3.06 A 3 − I limit − 3.06 A 3 min n/a max n/a − 3.06 A 3 Current range n/a n/a 3.06 A 3 n/a lowest n/a Current n/a n/a -0.5 mA n/a 0 A n/a V limit range n/a n/a 6.12 V n/a 20.4 V n/a +V limit n/a n/a 6.12 V n/a 20.4 V n/a − V limit 1 n/a n/a min n/a − 20.4 V n/a Output resistance 2 0 Ω /off 0 Ω /off n/a 0 Ω /off n/a 0 Ω /off Output state off off off off on on I limit tracking off off off off off off V limit tracking 1 off off off off off off Note 1: N6784A only Note 2: N6781A only Note 3: 8.16 A for Models N6785A and N6786A
