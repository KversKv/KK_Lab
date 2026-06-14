import React, { useState, useEffect, useRef } from 'react';
import { LogPanel, LogItem, QuickProject, Script, ScriptStep, AutoBaudSettings, QuickCommand } from './types';
import { Sidebar } from './components/Sidebar';
import { Toolbar } from './components/Toolbar';
import { LogGrid } from './components/LogGrid';
import { QuickCommandsTab } from './components/QuickCommandsTab';
import { ScriptsTab } from './components/ScriptsTab';
import { SettingsModal } from './components/SettingsModal';
import { 
  isWebSerialSupported, 
  getDefaultQuickCommands, 
  getDefaultScripts, 
  generateMockDeviceBoot,
  getFormattedTimestamp,
  encodeText,
  hexToBytes,
  bytesToHex,
  countGoodAsciiRatio
} from './utils/serialHelper';
import { Terminal, Send, HelpCircle } from 'lucide-react';

const INITIAL_AUTOBAUD_SETTINGS: AutoBaudSettings = {
  enabled: true,
  runtimeRedetectEnabled: true,
  candidateBaudrates: [115200, 9600, 921600],
  lockThreshold: 85,
  badThreshold: 45,
  badWindowsToSuspect: 3,
  suspectWindowsToScan: 2,
  monitorWindowMaxTimeMs: 400,
  switchCooldownMs: 5000,
  switchScoreMargin: 15,
  confirmScanRounds: 2
};

export default function App() {
  const [isDark, setIsDark] = useState<boolean>(() => {
    const saved = localStorage.getItem('kk_is_dark');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('kk_is_dark', JSON.stringify(isDark));
  }, [isDark]);

  const [panels, setPanels] = useState<LogPanel[]>([createDefaultPanel('1', 'Primary Log')]);
  const [activePanelIndex, setActivePanelIndex] = useState<number>(0);
  const [availablePorts, setAvailablePorts] = useState<string[]>([]);
  const [autoBaud, setAutoBaud] = useState<AutoBaudSettings>(INITIAL_AUTOBAUD_SETTINGS);
  
  // Modals
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Tabs Bottom console
  const [activeTab, setActiveTab] = useState<'quick' | 'scripts'>('quick');

  // Quick command states
  const [projects, setProjects] = useState<QuickProject[]>(() => {
    const saved = localStorage.getItem('kk_projects');
    return saved ? JSON.parse(saved) : getDefaultQuickCommands();
  });
  const [activeProjectId, setActiveProjectId] = useState<string>('');
  const [activeGroupId, setActiveGroupId] = useState<string>('');

  // Script Automated states
  const [scripts, setScripts] = useState<Script[]>(() => {
    const saved = localStorage.getItem('kk_scripts');
    return saved ? JSON.parse(saved) : getDefaultScripts();
  });
  const [activeScriptId, setActiveScriptId] = useState<string>('');
  const [isScriptRunning, setIsScriptRunning] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [scriptLoopRemaining, setScriptLoopRemaining] = useState(1);
  
  // References to active physical Serial Ports & stream readers/writers
  const openedPortsRef = useRef<Map<string, {
    port: any;
    reader?: any;
    writer?: any;
    readableStreamStop?: () => void;
  }>>(new Map());

  // Input textbox
  const [sendText, setSendText] = useState('');
  const [sendHistory, setSendHistory] = useState<string[]>([]);
  const [historyIndex, setSendHistoryIndex] = useState(-1);

  // Interval timer references for mock devices streaming
  const mockTimersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Script timer or keyword wait timeout
  const scriptTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const currentScriptRef = useRef<Script | null>(null);

  const activePanel = panels[activePanelIndex] || panels[0];
  const activeScript = scripts.find(s => s.id === activeScriptId) || scripts[0];

  // Create standard template panel helper
  function createDefaultPanel(id: string, title: string): LogPanel {
    return {
      id,
      title,
      port: '',
      baudrate: 115200,
      databits: 8,
      stopbits: '1',
      parity: 'None',
      flowControl: 'None',
      rxBytes: 0,
      txBytes: 0,
      isConnected: false,
      isMock: true,
      allLogs: [],
      filterKeyword: '',
      filterRegex: false,
      filterCase: false,
      filterInvert: false,
      filterBefore: 0,
      filterAfter: 0,
      autoScroll: true,
      showTime: true,
      useNtp: false,
      showSent: true,
      lineByLine: false,
      maxLines: 5000,
      rxFormat: 'ASCII',
      txFormat: 'ASCII',
      lineEnding: '\\r\\n',
      autoFlush: true,
      autoFlushMs: 50
    };
  }

  // Save changes locally
  useEffect(() => {
    localStorage.setItem('kk_projects', JSON.stringify(projects));
  }, [projects]);

  useEffect(() => {
    localStorage.setItem('kk_scripts', JSON.stringify(scripts));
  }, [scripts]);

  // Set initial project and group ids
  useEffect(() => {
    if (projects.length > 0) {
      setActiveProjectId(projects[0].id);
      if (projects[0].groups.length > 0) {
        setActiveGroupId(projects[0].groups[0].id);
      }
    }
    if (scripts.length > 0) {
      setActiveScriptId(scripts[0].id);
    }
  }, []);

  // Poll Web Serial ports
  const handleQueryPorts = async () => {
    if (!isWebSerialSupported()) {
      console.log("Web Serial API is not supported in this browser.");
      return;
    }
    try {
      const ports = await (navigator as any).serial.getPorts();
      const portNames = ports.map((port: any, idx: number) => `Port #${idx + 1} (USB Adapter)`);
      setAvailablePorts(portNames);
    } catch (err) {
      console.error("Failed to query ports", err);
    }
  };

  useEffect(() => {
    handleQueryPorts();
    // Watch connection plug events
    if (isWebSerialSupported()) {
      const onConnect = () => handleQueryPorts();
      const onDisconnect = () => handleQueryPorts();
      (navigator as any).serial.addEventListener('connect', onConnect);
      (navigator as any).serial.addEventListener('disconnect', onDisconnect);
      return () => {
        (navigator as any).serial.removeEventListener('connect', onConnect);
        (navigator as any).serial.removeEventListener('disconnect', onDisconnect);
      };
    }
  }, []);

  // Update Settings inside specific panel index
  const handleUpdatePanelSettings = (idx: number, settings: Partial<LogPanel>) => {
    setPanels(prev => prev.map((p, i) => i === idx ? { ...p, ...settings } : p));
  };

  // Reset defaults matching `_sc_reset_user_config_keep_quick_commands`
  const handleResetDefaults = () => {
    setPanels([createDefaultPanel('1', 'Primary Log')]);
    setActivePanelIndex(0);
    setAutoBaud(INITIAL_AUTOBAUD_SETTINGS);
    appendSystemLog(0, "System specifications restored to defaults. Cleaned active cache slots.", 'sys');
  };

  // Append customized formatted log item helper
  const appendLog = (idx: number, text: string, type: 'rx' | 'tx' | 'info' | 'warn' | 'error' | 'sys') => {
    setPanels(prev => {
      return prev.map((panel, i) => {
        if (i !== idx) return panel;
        const newLog: LogItem = {
          id: `log_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          timestamp: getFormattedTimestamp(false),
          type,
          text,
          ntpTimestamp: panel.useNtp ? getFormattedTimestamp(true) : undefined
        };
        const updatedLogs = [...panel.allLogs, newLog].slice(-panel.maxLines);
        return {
          ...panel,
          allLogs: updatedLogs
        };
      });
    });
  };

  const appendSystemLog = (idx: number, text: string, type: 'sys' | 'info' | 'warn' | 'error') => {
    appendLog(idx, `[SYSTEM] ${text}`, type);
  };

  // Connect / Disconnect triggers
  const handleToggleConnectActivePort = async () => {
    const idx = activePanelIndex;
    const panel = panels[idx];

    if (panel.isConnected) {
      // Disconnect
      await doDisconnectPanel(idx);
    } else {
      // Connect
      if (!panel.port) {
        alert("Please specify or select a Serial Port first inside the sidebar panel config.");
        return;
      }
      await doConnectPanel(idx);
    }
  };

  const doConnectPanel = async (idx: number) => {
    const panel = panels[idx];
    const isMock = panel.port.includes('(Simulation)');

    if (isMock) {
      // Simulation mode
      handleUpdatePanelSettings(idx, { isMock: true, isConnected: true });
      appendSystemLog(idx, `Simulating connection established safely: ${panel.port} @ ${panel.baudrate}bps`, 'info');
      
      // Simulate Boot loader stream
      const bootMessages = generateMockDeviceBoot(panel.port, panel.baudrate);
      bootMessages.forEach((msg, offset) => {
        setTimeout(() => {
          appendLog(idx, msg, 'rx');
          handleUpdatePanelSettings(idx, { rxBytes: panel.rxBytes + msg.length });
        }, offset * 250);
      });

      // Stream periodic standard sensor readings
      let streamCounter = 0;
      const timer = setInterval(() => {
        streamCounter++;
        let reading = '';
        if (panel.port.includes('COM9') || panel.port.includes('Sensor')) {
          const temp = (23.5 + Math.sin(streamCounter / 10) * 1.5).toFixed(1);
          const hum = (67.2 + Math.cos(streamCounter / 10) * 3).toFixed(1);
          reading = `01 03 04 01 E2 02 A8 B9 FA  (Temp: ${temp}°C, Humidity: ${hum}%)`;
        } else {
          reading = `SENSOR_A: ${Math.round(510 + Math.sin(streamCounter / 10) * 15)}, SENSOR_B: ${Math.round(90 + Math.cos(streamCounter / 5) * 5)}, STATUS: SECURE`;
        }
        appendLog(idx, reading, 'rx');
      }, 2000);

      mockTimersRef.current.set(panel.id, timer);

    } else {
      // Real Web Serial adapter mode
      if (!isWebSerialSupported()) {
        alert("Web Serial API is not supported in this browser. Try opening on Google Chrome, Edge or Brave, or toggle to a Simulation Port!");
        return;
      }

      try {
        appendSystemLog(idx, "Requesting native browser serial permissions...", 'info');
        const serialPortObj = await (navigator as any).serial.requestPort();
        
        const openOptions: any = {
          baudRate: panel.baudrate,
          dataBits: panel.databits,
          stopBits: Number(panel.stopbits),
        };
        // Normalize flow control
        if (panel.flowControl === 'RTS/CTS') openOptions.flowControl = 'hardware';

        appendSystemLog(idx, `Opening hardware serial transport: ${panel.port} @ ${panel.baudrate}bps`, 'info');
        await serialPortObj.open(openOptions);

        handleUpdatePanelSettings(idx, { isMock: false, isConnected: true });
        appendSystemLog(idx, "Connection established successfully!", 'info');

        // Readers loops
        const reader = serialPortObj.readable.getReader();
        const writer = serialPortObj.writable.getWriter();
        
        openedPortsRef.current.set(panel.id, {
          port: serialPortObj,
          reader,
          writer
        });

        // Background reader loop
        let keepReading = true;
        openedPortsRef.current.get(panel.id)!.readableStreamStop = () => {
          keepReading = false;
        };

        (async () => {
          try {
            while (serialPortObj.readable && keepReading) {
              const { value, done } = await reader.read();
              if (done) break;
              if (value) {
                const text = new TextDecoder().decode(value);
                appendLog(idx, text.trim(), 'rx');
                handleUpdatePanelSettings(idx, { rxBytes: panel.rxBytes + value.length });
                
                // If script is waiting for a keyword feedback
                if (isScriptRunning && currentScriptRef.current) {
                  const activeStep = activeScript?.steps[currentStepIndex];
                  if (activeStep && activeStep.wait_keyword && text.includes(activeStep.wait_keyword)) {
                    // Trigger immediate advance
                    if (scriptTimeoutRef.current) clearTimeout(scriptTimeoutRef.current);
                    advanceScriptSequence();
                  }
                }
              }
            }
          } catch (rErr) {
            console.error(rErr);
          } finally {
            reader.releaseLock();
          }
        })();

      } catch (err: any) {
        appendSystemLog(idx, `Connection Error: ${err.message || err.toString()}`, 'error');
        alert("Failed to establish serial interface: " + err);
      }
    }
  };

  const doDisconnectPanel = async (idx: number) => {
    const panel = panels[idx];
    
    if (panel.isMock) {
      const timer = mockTimersRef.current.get(panel.id);
      if (timer) {
        clearInterval(timer);
        mockTimersRef.current.delete(panel.id);
      }
    } else {
      const session = openedPortsRef.current.get(panel.id);
      if (session) {
        if (session.readableStreamStop) session.readableStreamStop();
        try {
          if (session.reader) await session.reader.cancel();
          if (session.writer) await session.writer.releaseLock();
          await session.port.close();
        } catch (cErr) {
          console.error(cErr);
        }
        openedPortsRef.current.delete(panel.id);
      }
    }

    handleUpdatePanelSettings(idx, { isConnected: false });
    appendSystemLog(idx, "Interface disconnected.", 'warn');
  };

  // Terminate connections upon component unload
  useEffect(() => {
    return () => {
      panels.forEach((_, idx) => {
        doDisconnectPanel(idx);
      });
    };
  }, []);

  // Global pause/resume toggle for active panel
  const handlePauseToggle = () => {
    handleUpdatePanelSettings(activePanelIndex, { autoScroll: !activePanel.autoScroll });
  };

  // Add / Remove Log Grid card wrappers
  const handleAddLogPanel = () => {
    if (panels.length >= 4) return;
    const nextIdx = panels.length + 1;
    const newPanel = createDefaultPanel(String(nextIdx), `Split Console Log ${nextIdx}`);
    setPanels([...panels, newPanel]);
    setActivePanelIndex(panels.length); // auto select new panel
  };

  const handleRemoveLogPanel = () => {
    if (panels.length <= 1) return;
    const targetIdx = panels.length - 1;
    doDisconnectPanel(targetIdx);
    setPanels(panels.filter((_, idx) => idx !== targetIdx));
    if (activePanelIndex >= targetIdx) {
      setActivePanelIndex(targetIdx - 1);
    }
  };

  // Flush panel logs
  const handleClearPanelLogs = (idx: number) => {
    onClearLogs(idx);
  };

  const onClearLogs = (idx: number) => {
    setPanels(prev => prev.map((p, i) => i === idx ? {
      ...p,
      allLogs: [],
      rxBytes: 0,
      txBytes: 0
    } : p));
  };

  // AT Command Handshake Responder Simulation Engine (high-fidelity playground)
  const processSimulatedTxResponse = (idx: number, content: string) => {
    const clean = content.trim().toUpperCase();
    setTimeout(() => {
      if (clean === 'AT') {
        appendLog(idx, "OK", 'rx');
      } else if (clean === 'AT+GMR') {
        appendLog(idx, "esp32-v2.4.0-handshake\nSDK version: v4.4.2-kk-labs\nOK", 'rx');
      } else if (clean === 'AT+RST') {
        appendLog(idx, "Rebooting system target ESP32...", 'sys');
        setTimeout(() => {
          const resetLog = generateMockDeviceBoot("COM3", panels[idx].baudrate);
          resetLog.forEach((msg, offset) => {
            setTimeout(() => appendLog(idx, msg, 'rx'), offset * 100);
          });
        }, 500);
      } else if (clean === 'AT+CWLAP') {
        appendLog(idx, "+CWLAP:(4,\"KK_Office_Secure\",-48,\"22:83:cf:8a\")\n+CWLAP:(3,\"Developer_IoT_Zone\",-62,\"44:a0:88:bd\")\nOK", 'rx');
      } else if (clean.includes('01 03') || clean.includes('0103')) {
        // Simulated Modbus RTU Response Frame
        appendLog(idx, "01 03 04 01 FF 02 8F BA 1C", 'rx');
      } else {
        // echo command
        appendLog(idx, `ECHO Back: ${content}`, 'rx');
      }
    }, 120);
  };

  // General write data send logic (used by inputs, quick macro buttons, and script engines)
  const handleSendData = async (text: string, sendType: 'text' | 'hex' = 'text', lineEnding: string = '\\r\\n', encoding: string = 'utf-8') => {
    if (!activePanel.isConnected) {
      appendSystemLog(activePanelIndex, "Cannot write data: terminal interface disconnected.", 'error');
      return false;
    }

    let rawData: Uint8Array;
    try {
      if (sendType === 'hex') {
        rawData = hexToBytes(text);
      } else {
        const endingText = lineEnding
          .replace('\\r', '\r')
          .replace('\\n', '\n');
        rawData = encodeText(text + endingText, encoding);
      }
    } catch {
      appendSystemLog(activePanelIndex, `Formatting Error: HEX string parse crashed. Check for valid hex values.`, 'error');
      return false;
    }

    if (activePanel.isMock) {
      // Simulation mode
      handleUpdatePanelSettings(activePanelIndex, { txBytes: activePanel.txBytes + rawData.length });
      if (activePanel.showSent) {
        const display = sendType === 'hex' ? bytesToHex(rawData) : text;
        appendLog(activePanelIndex, `[TX] ${display}`, 'tx');
      }
      processSimulatedTxResponse(activePanelIndex, text);
      return true;
    } else {
      // Physical Serial adapter mode
      const session = openedPortsRef.current.get(activePanel.id);
      if (session && session.writer) {
        try {
          await session.writer.write(rawData);
          handleUpdatePanelSettings(activePanelIndex, { txBytes: activePanel.txBytes + rawData.length });
          
          if (activePanel.showSent) {
            const display = sendType === 'hex' ? bytesToHex(rawData) : text;
            appendLog(activePanelIndex, `[TX] ${display}`, 'tx');
          }
          return true;
        } catch (err: any) {
          appendSystemLog(activePanelIndex, `TX Fail: ${err.message}`, 'error');
          return false;
        }
      }
    }
    return false;
  };

  // Send input textbox callback
  const handleInputSubmit = async () => {
    if (!sendText.trim()) return;
    const ok = await handleSendData(sendText, activePanel.txFormat.toLowerCase() as any, activePanel.lineEnding);
    if (ok) {
      setSendHistory(p => [sendText, ...p.filter(x => x !== sendText)].slice(0, 50));
      setSendText('');
      setSendHistoryIndex(-1);
    }
  };

  // Keyboard navigation inside send inputs for history
  const handleKeyDownHistory = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const nextIdx = historyIndex + 1;
      if (nextIdx < sendHistory.length) {
        setSendHistoryIndex(nextIdx);
        setSendText(sendHistory[nextIdx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const nextIdx = historyIndex - 1;
      if (nextIdx >= 0) {
        setSendHistoryIndex(nextIdx);
        setSendText(sendHistory[nextIdx]);
      } else {
        setSendHistoryIndex(-1);
        setSendText('');
      }
    }
  };

  // Quick command button trig
  const handleQuickCommandClicked = (cmd: QuickCommand) => {
    handleSendData(cmd.content, cmd.send_type, cmd.line_ending, cmd.encoding);
  };

  // Script Sequencer execution scheduler loop
  const handleRunScriptSuite = (script: Script) => {
    if (isScriptRunning) return;
    if (!activePanel.isConnected) {
      alert("Please connect the interface diagnostic port before scheduling code sequences.");
      return;
    }
    
    currentScriptRef.current = script;
    setIsScriptRunning(true);
    setCurrentStepIndex(0);
    setScriptLoopRemaining(script.loop ? script.loop_count : 1);
    appendSystemLog(activePanelIndex, `[SCRIPT] Triggering script suite "${script.name}"`, 'sys');
  };

  const handleStopScript = () => {
    if (scriptTimeoutRef.current) clearTimeout(scriptTimeoutRef.current);
    setIsScriptRunning(false);
    setCurrentStepIndex(-1);
    currentScriptRef.current = null;
    appendSystemLog(activePanelIndex, `[SCRIPT] Automation sequence stopped.`, 'sys');
  };

  // Advancing loop steps
  useEffect(() => {
    if (!isScriptRunning || !currentScriptRef.current) return;
    const steps = currentScriptRef.current.steps;
    
    if (currentStepIndex >= steps.length) {
      // Loop cycle completed
      const remaining = scriptLoopRemaining - 1;
      if (currentScriptRef.current.loop && remaining > 0) {
        setScriptLoopRemaining(remaining);
        setCurrentStepIndex(0);
        appendSystemLog(activePanelIndex, `[SCRIPT] Entering next repetitive cycle. Loops left: ${remaining}`, 'sys');
      } else {
        // Complete execution successful
        setIsScriptRunning(false);
        setCurrentStepIndex(-1);
        currentScriptRef.current = null;
        appendSystemLog(activePanelIndex, `[SCRIPT] Run sequence finished successfully.`, 'sys');
      }
      return;
    }

    const step = steps[currentStepIndex];
    appendSystemLog(activePanelIndex, `[SCRIPT] Executing Step ${currentStepIndex + 1}/${steps.length} [${step.cmd}]`, 'sys');
    
    // Write step TX
    handleSendData(step.cmd, 'text', activePanel.lineEnding);

    // Set delay timeout OR wait on keyword feedback trigger
    const timeoutVal = step.wait_keyword ? (step.wait_timeout_ms || step.wait_ms || 4000) : step.wait_ms;
    
    scriptTimeoutRef.current = setTimeout(() => {
      if (step.wait_keyword) {
        appendSystemLog(activePanelIndex, `[SCRIPT] Keyword timeout: "${step.wait_keyword}" was not encountered. Skipping...`, 'warn');
      }
      advanceScriptSequence();
    }, timeoutVal);

    return () => {
      if (scriptTimeoutRef.current) clearTimeout(scriptTimeoutRef.current);
    };

  }, [isScriptRunning, currentStepIndex, scriptLoopRemaining]);

  const advanceScriptSequence = () => {
    setCurrentStepIndex(prev => prev + 1);
  };

  return (
    <div className={`flex flex-col h-screen font-sans ${isDark ? 'dark bg-[#020617] text-slate-300' : 'bg-slate-50 text-slate-800'}`} id="kk-uart-suite-window">
      
      {/* GLOBAL TOP HEADER BAR */}
      <Toolbar 
        panel={activePanel}
        onToggleConnect={handleToggleConnectActivePort}
        onPauseToggle={handlePauseToggle}
        onStop={() => doDisconnectPanel(activePanelIndex)}
        sidebarVisible={true}
        onToggleSidebar={() => {}}
        onAddLogPanel={handleAddLogPanel}
        onRemoveLogPanel={handleRemoveLogPanel}
        totalPanels={panels.length}
        onOpenSettingsModal={() => setIsSettingsOpen(true)}
        isDark={isDark}
        onToggleTheme={() => setIsDark(!isDark)}
      />

      <div className="flex-1 flex overflow-hidden" id="workspace-layout-split">
        {/* SIDEBAR PANEL */}
        <Sidebar 
          panel={activePanel}
          updatePanelSettings={(settings) => handleUpdatePanelSettings(activePanelIndex, settings)}
          autoBaud={autoBaud}
          updateAutoBaud={(settings) => setAutoBaud(prev => ({ ...prev, ...settings }))}
          onRefreshPorts={handleQueryPorts}
          availablePorts={availablePorts}
        />

        {/* Diagnostic workspace splits containing boards & tabs console */}
        <main className="flex-1 flex flex-col h-full bg-slate-100/50 dark:bg-[#020617] overflow-hidden" id="diagnostics-sandbox">
          
          {/* Top segment: Log screen grid columns splits */}
          <div className="flex-1 min-h-[40%] overflow-hidden bg-slate-50/50 dark:bg-[#070709]" id="diagnostics-log-boards">
            <LogGrid 
              panels={panels}
              activePanelIndex={activePanelIndex}
              setActivePanelIndex={setActivePanelIndex}
              updatePanelSettings={handleUpdatePanelSettings}
              onClearLogs={handleClearPanelLogs}
            />
          </div>

          {/* Quick interactive command sender row bar */}
          <div className="bg-white/80 dark:bg-[#020617]/80 border-y border-slate-200/80 dark:border-slate-800/80 p-3.5 px-6 flex items-center gap-3 select-none backdrop-blur-xl z-10" id="tx-quick-command-bar">
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-500 font-bold select-none" id="tx-console-icon">
              <Terminal size={14} className="text-blue-600 dark:text-blue-500" />
              <span>Diagnostic CLI</span>
            </div>
            
            <input
              type="text"
              placeholder="Inject command... (Use up/down arrow keys for command history)"
              value={sendText}
              onChange={(e) => setSendText(e.target.value)}
              onKeyDown={handleKeyDownHistory}
              onKeyPress={(e) => e.key === 'Enter' && handleInputSubmit()}
              className="flex-1 text-xs bg-slate-50 dark:bg-slate-900/50 dark:text-slate-100 text-slate-900 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800/80 focus:border-blue-500 dark:focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/10 dark:focus:ring-blue-500/10 outline-none font-mono transition-all shadow-inner dark:shadow-none placeholder:text-slate-400 dark:placeholder:text-slate-600"
              id="input-diagnostic-console-feed"
            />

            <button
              onClick={handleInputSubmit}
              title="Push directive payload"
              className="flex items-center gap-1.5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold text-xs rounded-lg transition-all focus:outline-none focus:ring-4 focus:ring-blue-500/20 shadow-sm"
              id="btn-send-payoad"
            >
              <Send size={11} fill="currentColor" />
              <span>Send CLI</span>
            </button>
          </div>

          {/* Bottom segment: Custom interactive selector tabs console */}
          <div className="h-64 bg-slate-50/80 dark:bg-[#09090b] flex flex-col overflow-hidden" id="auxiliary-diagnostic-console">
            {/* Console switcher header rows */}
            <div className="bg-white/50 dark:bg-[#020617]/50 px-4 flex items-center justify-between text-xs font-semibold select-none border-b border-slate-200/80 dark:border-slate-800 backdrop-blur-md" id="console-sub-navigation">
              <div className="flex items-center gap-6 pt-2">
                <button
                  onClick={() => setActiveTab('quick')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'quick' ? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-400 font-bold' : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-500 dark:hover:text-slate-300 font-medium'
                  }`}
                >
                  Quick Commands
                </button>

                <button
                  onClick={() => setActiveTab('scripts')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'scripts' ? 'border-blue-600 text-blue-600 dark:border-blue-500 dark:text-blue-400 font-bold' : 'border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-500 dark:hover:text-slate-300 font-medium'
                  }`}
                >
                  Automated Sequences
                </button>
              </div>

              <div className="flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-slate-500 font-bold select-none bg-slate-100/80 dark:bg-slate-900 px-3 py-1.5 rounded-full mb-1">
                <HelpCircle size={12} />
                <span>Double click buttons to edit macros</span>
              </div>
            </div>

            {/* Bottom active Tab component display */}
            <div className="flex-1 overflow-hidden" id="workspace-tab-contents">
              {activeTab === 'quick' ? (
                <QuickCommandsTab 
                  projects={projects}
                  setProjects={setProjects}
                  activeProjectId={activeProjectId}
                  setActiveProjectId={setActiveProjectId}
                  activeGroupId={activeGroupId}
                  setActiveGroupId={setActiveGroupId}
                  onSendCommand={handleQuickCommandClicked}
                />
              ) : (
                <ScriptsTab 
                  scripts={scripts}
                  setScripts={setScripts}
                  activeScriptId={activeScriptId}
                  setActiveScriptId={setActiveScriptId}
                  isRunning={isScriptRunning}
                  onRunScript={handleRunScriptSuite}
                  onStopScript={handleStopScript}
                  currentStepIndex={currentStepIndex}
                  loopRemaining={scriptLoopRemaining}
                />
              )}
            </div>
          </div>

        </main>
      </div>

      {/* SYSTEMS SETTINGS DIALOG */}
      <SettingsModal 
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        panel={activePanel}
        updatePanelSettings={(settings) => handleUpdatePanelSettings(activePanelIndex, settings)}
        autoBaud={autoBaud}
        updateAutoBaud={(settings) => setAutoBaud(prev => ({ ...prev, ...settings }))}
        onResetDefaults={handleResetDefaults}
      />

    </div>
  );
}
