# 5 Programming Examples

This chapter contains several example programs to help you develop programs for your own application. The example programs are for illustration only, and are provided with the assumption that you are familiar with the programming language being demonstrated and the tools used to create and debug procedures. See chapter 3, “Commands by Subsyustem” for the SCPI command syntax.

You have a royalty-free right to use, modify, reproduce and distribute the example programs (and/or any modified version) in any way you find useful, provided you agree that Keysight Technologies has no warranty, obligations, or liability for any example programs.

The example programs are written in Microsoft Visual Basic 6.0 using the VISA COM IO library. The VISA COM library must be downloaded from the Automation-Ready CD-ROM to use these programs. For information about using VISA COM in another Visual Basic project, refer to “Programming Your Instruments” in the USB/LAN/GPIB Interfaces Connectivity Guide , also included on the Automation-Ready CD-ROM.

> **NOTE** Example programs for the following programming environments are also included on the Product-Reference CD-ROM located at the back of this guide: Microsoft Visual Basic 6.0 Microsoft Visual C++ 6.0 Microsoft Excel Keysight VEE Pro The CD also contains IVI-COM and VXIplug&play drivers for your instrument.

## Arb Programming Example

This program executes a voltage arbitrary waveform consisting of 10 steps. The steps are set to a dwell time of 1 second. When done, the program checks for instrument error and gives a message if there is an error. This is similar to the list programming example, but using SCPI Arb commands. Note that current values cannot be programmed as part of a voltage arbitrary waveform.

```
Sub arb_programming_example()
Dim IDN As String
Dim GPIBaddress As String
Dim ErrString As String
Dim channel As String
'These variable are necessary to initialize the VISA COM.
Dim ioMgr As KeysightRMLib.SRMCls
Dim Instrument As VisaComLib.FormattedIO488
' The following command line provides the program with the VISA name of the
' interface that it will communicate with. It is currently set to use GPIB.
GPIBaddress = "GPIB1::5::INSTR"
' Use the following line instead for LAN communication
' TCPIPaddress="TCPIP0::141.25.36.214"
' Use the following line instead for USB communication
' USBaddress = "USB0::2391::1799::US00000002"
' Initialize the VISA COM communication
Set ioMgr = New KeysightRMLib.SRMCls
Set Instrument = New VisaComLib.FormattedIO488
Set Instrument.IO = ioMgr.Open(TCPIPaddress)
' These next three strings are the points in the user defined voltage arb.
' The first one controls voltage, the second dwell, and the third trigger out
Const voltPoints = "1,2,3,4,5,6,7,8,9,10"
Const dwellPoints = "1"
Const triggerPoints = "0"
' This variable can be changed to program any channel in the mainframe
channel = "(@1)" ' channel 1
With Instrument
' Send a power reset to the instrument
.WriteString "*RST"
' Query the instrument for the IDN string
.WriteString "*IDN?"
IDN = .ReadString
' Set the arb type to user defined voltage
.WriteString "ARB:FUNC UDV," & channel
' Set the voltage mode to arb
.WriteString "VOLT:MODE ARB," & channel
' Send the voltage points
.WriteString "ARB:VOLT:UDEF:LEV " & voltPoints & "," & channel
' Send the dwell points
.WriteString "ARB:VOLT:UDEF:DWEL " & dwellPoints & "," & channel
'Send the trigger points
.WriteString "ARB:VOLT:UDEF:BOST " & triggerPoints & "," & channel
' Turn the output on
.WriteString "OUTP ON," & channel
' Wait for output to settle in the ON state.
.WriteString "*OPC?"
.ReadString
' Set the trigger source to bus
.WriteString "TRIG:TRAN:SOUR BUS," & channel
' Initiate the transient system
.WriteString "INIT:TRAN " & channel
' Trigger the unit
.WriteString "TRIG:TRAN " & channel
' Check instrument for any errors
.WriteString "Syst:err?"
ErrString = .ReadString
' give message if there is an error
If Val(ErrString) Then
MsgBox "Error in instrument!" & vbCrLf & ErrString
End If
End With
End Sub
```

## Output Programming Example

This is a simple program that sets a voltage, current, over-voltage, and the status of over-current protection. When done, the program checks for instrument error and gives a message if there is an error.

```
Sub output_programming_example()
Dim IDN As String
Dim GPIBaddress As String
Dim ErrString As String
' This variable controls the channel number to be programmed
Dim channel As String
' This variable controls the voltage
Dim VoltSetting As Double
' This variable measures the voltage
Dim MeasureVoltString As String
' This variable controls the current
Dim CurrSetting As Double
' This variable controls the over voltage protection setting
Dim overVoltSetting As Double
'These variables are necessary to initialize the VISA COM.
Dim ioMgr As KeysightRMLib.SRMCls
Dim Instrument As VisaComLib.FormattedIO488
' The following command line provides the program with the VISA name of the
' interface that it will communicate with. It is currently set to use GPIB.
GPIBaddress = "GPIB0::5::INSTR"
' Use the following line instead for LAN communication
' TCPIPaddress="TCPIP0::141.25.36.214"
' Use the following line instead for USB communication
' USBaddress = "USB0::2391::1799::US00000002"
' Initialize the VISA COM communication
Set ioMgr = New KeysightRMLib.SRMCls
Set Instrument = New VisaComLib.FormattedIO488
Set Instrument.IO = ioMgr.Open(GPIBaddress)
' The next three command lines set the voltage, current, and over voltage
VoltSetting = 3
CurrSetting = 1.5 ' amps
overVoltSetting = 10
' This variable can be changed to program any channel in the mainframe
channel = "(@1)" ' channel 1
With Instrument
' Send a power reset to the instrument
.WriteString "*RST"
' Query the instrument for the IDN string
.WriteString "*IDN?"
IDN = .ReadString
' Set the voltage
.WriteString "VOLT" & Str$(VoltSetting) & "," & channel
' Set the over voltage level
.WriteString "VOLT:PROT:LEV " & Str$(overVoltSetting) & "," & channel
' Set current level
.WriteString "CURR " & Str$(CurrSetting) & "," & channel
' Turn on over current protection
.WriteString "CURR:PROT:STAT ON," & channel
' Turn the output on
.WriteString "OUTP ON," & channel
' Wait for previous commands to complete.
.WriteString "*OPC?"
.ReadString
' Measure the voltage
.WriteString "MEAS:VOLT? " & channel
MeasureVoltString = .ReadString
MsgBox "Measured Voltage is " & MeasureVoltString & "At channel" & channel
' Check instrument for any errors
.WriteString "Syst:err?"
ErrString = .ReadString
' give message if there is an error
If Val(ErrString) Then
MsgBox "Error in instrument!" & vbCrLf & ErrString
End If
End With
End Sub
```

## List Programming Example

This program executes a 10 point current and voltage list. It also specifies 10 different dwell times. When done, the program checks for instrument error and gives a message if there is an error.

```
Sub list_programming_example()
Dim IDN As String
Dim GPIBaddress As String
Dim ErrString As String
Dim channel As String
'These variable are necessary to initialize the VISA COM.
Dim ioMgr As KeysightRMLib.SRMCls
Dim Instrument As VisaComLib.FormattedIO488
' The following command line provides the program with the VISA name of the
' interface that it will communicate with. It is currently set to use GPIB.
GPIBaddress = "GPIB1::5::INSTR"
' Use the following line instead for LAN communication
' TCPIPaddress="TCPIP0::141.25.36.214"
' Use the following line instead for USB communication
' USBaddress = "USB0::2391::1799::US00000002"
' Initialize the VISA COM communication
Set ioMgr = New KeysightRMLib.SRMCls
Set Instrument = New VisaComLib.FormattedIO488
Set Instrument.IO = ioMgr.Open(GPIBaddress)
' These next three strings are the points in the list.
' All three strings are the same length.
' The first one controls voltage, the second current, and the third dwell time
Const voltPoints = "1,2,3,4,5,6,7,8,9,10"
Const currPoints = "0.5,1,1.5,2,2.5,3,3.5,4,4.5,5"
Const dwellPoints = "1,2,0.5,1,0.25,1.5,0.1,1,0.75,1.2"
' This variable can be changed to program any channel in the mainframe
channel = "(@1)" ' channel 1
With Instrument
' Send a power reset to the instrument
.WriteString "*RST"
' Query the instrument for the IDN string
.WriteString "*IDN?"
IDN = .ReadString
' Set the voltage mode to list
.WriteString "VOLT:MODE LIST," & channel
' Set the current mode to list
.WriteString "CURR:MODE LIST," & channel
' Send the voltage list points
.WriteString "LIST:VOLT " & voltPoints & "," & channel
' Send the Current list points
.WriteString "LIST:CURR " & currPoints & "," & channel
' Send the dwell points
.WriteString "LIST:DWEL " & dwellPoints & "," & channel
' Turn the output on
.WriteString "OUTP ON," & channel
' Wait for output to settle in the ON state.
.WriteString "*OPC?"
.ReadString
' Set the trigger source to bus
.WriteString "TRIG:TRAN:SOUR BUS," & channel
' Initiate the transient system
.WriteString "INIT:TRAN " & channel
' Trigger the unit
.WriteString "*TRG"
' Check instrument for any errors
.WriteString "Syst:err?"
ErrString = .ReadString
' give message if there is an error
If Val(ErrString) Then
MsgBox "Error in instrument!" & vbCrLf & ErrString
End If
End With
End Sub
```

## Digitizer Programming Example

This program uses the voltage in step mode and also demonstrates how to set up and use the digitizer. When done, the program checks for instrument error and gives a message if there is an error.

```
Sub digitizer_programming_example()
Dim IDN As String
Dim GPIBaddress As String
Dim ErrString As String
Dim channel As String
Dim measPoints As Long
Dim measOffset As Long
Dim VoltSetting As Double
Dim finalVoltage As Double
Dim timeInterval As Double
Dim VoltPoints() As Variant
Dim i As Long
Const WTG_MEAS = 8
Const WTG_TRANS = 16
'These variables are necessary to initialize the VISA COM.
Dim ioMgr As KeysightRMLib.SRMCls
Dim Instrument As VisaComLib.FormattedIO488
' The following command line provides the program with the VISA name of the
' interface that it will communicate with. It is currently set to use GPIB.
GPIBaddress = "GPIB0::5::INSTR"
' Use the following line instead for LAN communication
' TCPIPaddress="TCPIP0::141.25.36.214"
' Use the following line instead for USB communication
' USBaddress = "USB0::2391::1799::US00000002"
' Initialize the VISA COM communication
Set ioMgr = New KeysightRMLib.SRMCls
Set Instrument = New VisaComLib.FormattedIO488
Set Instrument.IO = ioMgr.Open(GPIBaddress)
' This controls the number of points the measurement system measures
measPoints = 100
' This controls the number of points to offset the measurement (positive for
' forward, negative for reverse)
measOffset = 0
' This sets the time between points
timeInterval = 0.0025
' This controls the voltage
VoltSetting = 5
' This is the final voltage that will be triggered
finalVoltage = 10
' This variable can be changed to program any channel in the mainframe
channel = "(@1)" ' channel 1
With Instrument
' Send a power reset to the instrument
.WriteString "*RST"
' Query the instrument for the IDN string
.WriteString "*IDN?"
IDN = .ReadString
' Put the Voltage into step mode which causes it to transition from one
' voltage to another upon receiving a trigger
.WriteString "VOLT:MODE STEP," & channel
' Set the voltage
.WriteString "VOLT" & Str$(VoltSetting) & "," & channel
' Go to final value
.WriteString "VOLT:TRIG" & Str$(finalVoltage) & "," & channel
' Turn the output on
.WriteString "OUTP ON," & channel
' Wait for output to turn on.
.WriteString "*OPC?"
.ReadString
' Set the bus as the transient trigger source
.WriteString "TRIG:TRAN:SOUR BUS," & channel
' Set the number of points for the measurement system to use as an offset
.WriteString "SENS:SWE:OFFS:POIN" & Str$(measOffset) & "," & channel
' Set the number of points that the measurement system uses
.WriteString "SENS:SWE:POIN" & Str$(measPoints) & "," & channel
' Set the time interval between points
.WriteString "SENS:SWE:TINT" & Str$(timeInterval) & "," & channel
' Set the measurement trigger source
.WriteString "TRIG:ACQ:SOUR BUS," & channel
' Initiate the measurement trigger system
.WriteString "INIT:ACQ " & channel
' Initiate the transient trigger system
.WriteString "INIT:TRAN " & channel
' Wait for INITiate commands to complete
Do
.WriteString "STAT:OPER:COND? " & channel
Status = .ReadString
Loop Until (Status And (WTG_MEAS + WTG_TRANS)) = (WTG_MEAS + WTG_TRANS)
' Trigger the unit
.WriteString "*TRG"
' Read back the voltage points
.WriteString "FETC:ARR:VOLT? " & channel
VoltPoints = .ReadList
' Print the first 10 voltage points
For i = 0 To 9
Debug.Print i, VoltPoints(i)
Next i
' Check instrument for any errors
.WriteString "Syst:err?"
ErrString = .ReadString
' give message if there is an error
If Val(ErrString) Then
MsgBox "Error in instrument!" & vbCrLf & ErrString
End If
End With
End Sub
```
