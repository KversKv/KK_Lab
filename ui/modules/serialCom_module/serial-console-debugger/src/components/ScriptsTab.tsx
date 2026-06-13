import React, { useState } from 'react';
import { Script, ScriptStep, QuickCommand } from '../types';
import { Play, Square, Plus, Trash2, ArrowUp, ArrowDown, Edit, Upload, Download } from 'lucide-react';

interface ScriptsTabProps {
  scripts: Script[];
  setScripts: React.Dispatch<React.SetStateAction<Script[]>>;
  activeScriptId: string;
  setActiveScriptId: (id: string) => void;
  isRunning: boolean;
  onRunScript: (script: Script) => void;
  onStopScript: () => void;
  currentStepIndex: number;
  loopRemaining: number;
}

export function ScriptsTab({
  scripts,
  setScripts,
  activeScriptId,
  setActiveScriptId,
  isRunning,
  onRunScript,
  onStopScript,
  currentStepIndex,
  loopRemaining
}: ScriptsTabProps) {
  // Modal states
  const [showScriptModal, setShowScriptModal] = useState(false);
  const [showStepModal, setShowStepModal] = useState(false);

  // Edit fields
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [scriptName, setScriptName] = useState('');
  const [scriptLoop, setScriptLoop] = useState(false);
  const [scriptLoopCount, setScriptLoopCount] = useState(1);

  // Step field variables
  const [stepCmd, setStepCmd] = useState('');
  const [stepPriority, setStepPriority] = useState(1);
  const [stepWaitMs, setStepWaitMs] = useState(1000);
  const [stepKeyword, setStepKeyword] = useState('');
  const [stepTimeout, setStepTimeout] = useState(0);
  const [editingStepIndex, setEditingStepIndex] = useState<number | null>(null);

  const activeScript = scripts.find(s => s.id === activeScriptId) || scripts[0];

  const handleCreateScript = () => {
    setScriptName('');
    setScriptLoop(false);
    setScriptLoopCount(1);
    setModalType('create');
    setShowScriptModal(true);
  };

  const handleEditScriptSettings = () => {
    if (!activeScript) return;
    setScriptName(activeScript.name);
    setScriptLoop(activeScript.loop);
    setScriptLoopCount(activeScript.loop_count);
    setModalType('edit');
    setShowScriptModal(true);
  };

  const handleSaveScriptSettings = () => {
    if (!scriptName.trim()) return;
    if (modalType === 'create') {
      const newSid = `script_${Date.now()}`;
      const newScr: Script = {
        id: newSid,
        name: scriptName.trim(),
        loop: scriptLoop,
        loop_count: scriptLoopCount,
        steps: [
          { cmd: "AT", priority: 1, wait_ms: 1000, wait_keyword: "OK", wait_timeout_ms: 3000 }
        ]
      };
      setScripts([...scripts, newScr]);
      setActiveScriptId(newSid);
    } else {
      setScripts(scripts.map(s => s.id === activeScriptId ? { 
        ...s, 
        name: scriptName.trim(),
        loop: scriptLoop,
        loop_count: scriptLoopCount
      } : s));
    }
    setShowScriptModal(false);
  };

  const handleDeleteScript = () => {
    if (scripts.length <= 1) return;
    if (confirm(`Are you sure you want to delete script "${activeScript?.name}"?`)) {
      const filtered = scripts.filter(s => s.id !== activeScriptId);
      setScripts(filtered);
      setActiveScriptId(filtered[0].id);
    }
  };

  // Step Actions helper
  const handleOpenStepModal = (type: 'create' | 'edit', step?: ScriptStep, idx?: number) => {
    setModalType(type);
    if (type === 'edit' && step && idx !== undefined) {
      setStepCmd(step.cmd);
      setStepPriority(step.priority);
      setStepWaitMs(step.wait_ms);
      setStepKeyword(step.wait_keyword);
      setStepTimeout(step.wait_timeout_ms);
      setEditingStepIndex(idx);
    } else {
      setStepCmd('');
      setStepPriority((activeScript?.steps.length || 0) + 1);
      setStepWaitMs(1000);
      setStepKeyword('');
      setStepTimeout(0);
      setEditingStepIndex(null);
    }
    setShowStepModal(true);
  };

  const handleSaveStep = () => {
    if (!stepCmd.trim() || !activeScript) return;
    const finalStep: ScriptStep = {
      cmd: stepCmd.trim(),
      priority: Number(stepPriority),
      wait_ms: Number(stepWaitMs),
      wait_keyword: stepKeyword.trim(),
      wait_timeout_ms: Number(stepTimeout)
    };

    let updatedSteps = [...activeScript.steps];
    if (modalType === 'edit' && editingStepIndex !== null) {
      updatedSteps[editingStepIndex] = finalStep;
    } else {
      updatedSteps.push(finalStep);
    }

    // Sort by priority matching Python logic `_sc_script_ordered_steps`
    updatedSteps.sort((a, b) => a.priority - b.priority);

    setScripts(scripts.map(s => s.id === activeScriptId ? { ...s, steps: updatedSteps } : s));
    setShowStepModal(false);
  };

  const handleDeleteStep = (idx: number) => {
    if (!activeScript || activeScript.steps.length <= 1) return;
    if (confirm("Delete this script step?")) {
      const filteredSteps = activeScript.steps.filter((_, i) => i !== idx);
      setScripts(scripts.map(s => s.id === activeScriptId ? { ...s, steps: filteredSteps } : s));
    }
  };

  const handleMoveStep = (idx: number, delta: number) => {
    if (!activeScript) return;
    const targetIdx = idx + delta;
    if (targetIdx < 0 || targetIdx >= activeScript.steps.length) return;

    const reorderedSteps = [...activeScript.steps];
    const temp = reorderedSteps[idx];
    reorderedSteps[idx] = reorderedSteps[targetIdx];
    reorderedSteps[targetIdx] = temp;

    // Fix priority values sequentially automatically
    reorderedSteps.forEach((st, i) => {
      st.priority = i + 1;
    });

    setScripts(scripts.map(s => s.id === activeScriptId ? { ...s, steps: reorderedSteps } : s));
  };

  // Import text file scripts (format: cmd,priority,wait_ms,wait_keyword,wait_timeout)
  const handleImportText = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split('\n');
        const parsedSteps: ScriptStep[] = [];
        let priorityTracker = 1;

        lines.forEach(line => {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) return; // Ignore blank and comment lines
          const parts = trimmed.split(',');
          if (parts.length > 0 && parts[0]) {
            parsedSteps.push({
              cmd: parts[0].trim(),
              priority: Number(parts[1]) || priorityTracker++,
              wait_ms: Number(parts[2]) || 1000,
              wait_keyword: parts[3] ? parts[3].trim() : "",
              wait_timeout_ms: Number(parts[4]) || 0
            });
          }
        });

        if (parsedSteps.length === 0) {
          alert("Could not pull steps. Make sure file contains CSV line data.");
          return;
        }

        const importedScript: Script = {
          id: `script_${Date.now()}`,
          name: file.name.replace('.txt', '').replace('.csv', ''),
          loop: false,
          loop_count: 1,
          steps: parsedSteps
        };

        setScripts([...scripts, importedScript]);
        setActiveScriptId(importedScript.id);
        alert(`Successfully imported sequence of ${parsedSteps.length} steps!`);
      } catch (err) {
        alert("Failed to parse script sequence: " + err);
      }
    };
    reader.readAsText(file);
  };

  // Export TXT diagnostic layout script
  const handleExportText = () => {
    if (!activeScript) return;
    const header = `# Format: Command,Priority,Wait_ms,Wait_keyword,Wait_timeout\n# Script Name: ${activeScript.name}\n`;
    const lines = activeScript.steps.map(s => 
      `${s.cmd},${s.priority},${s.wait_ms},${s.wait_keyword},${s.wait_timeout_ms}`
    ).join('\n');
    
    const blob = new Blob([header + lines], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeScript.name.replace(/\s+/g, '_').toLowerCase()}_suite.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full bg-[#FAFBFD] dark:bg-zinc-950" id="automated-script-sequencer">
      
      {/* 1. SCRIPT TOOLBAR CONTROLS */}
      <div className="bg-[#FAFBFD] dark:bg-zinc-900 px-4 py-2 border-b border-gray-150 dark:border-zinc-800 flex items-center justify-between text-xs select-none" id="script-toolbar-controls">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-gray-500 dark:text-zinc-400">Run File:</span>
          {activeScript ? (
            <div className="flex items-center gap-2">
              <select
                value={activeScriptId}
                onChange={(e) => setActiveScriptId(e.target.value)}
                disabled={isRunning}
                className="bg-white dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100 text-xs border border-gray-250 p-1.5 rounded-lg focus:outline-none"
              >
                {scripts.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>

              <button 
                onClick={handleEditScriptSettings}
                disabled={isRunning}
                className="text-gray-400 hover:text-blue-500 disabled:opacity-40"
              >
                <Edit size={12} />
              </button>

              <button 
                onClick={handleDeleteScript}
                disabled={isRunning || scripts.length <= 1}
                className="text-gray-400 hover:text-red-500 disabled:opacity-40"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ) : (
            <span className="text-gray-400 italic">No script selected</span>
          )}

          <div className="h-4 w-px bg-gray-200 dark:bg-zinc-750" />

          {/* New / Import / Export buttons */}
          <div className="flex items-center gap-1.5" id="script-folder-triggers">
            <button 
              onClick={handleCreateScript}
              disabled={isRunning}
              className="px-2 py-1 px-3.5 bg-white hover:bg-gray-50 dark:bg-zinc-800 dark:hover:bg-zinc-750 dark:border-zinc-700 dark:text-zinc-200 border border-gray-150 rounded-lg text-gray-600 font-bold transition-all disabled:opacity-50 cursor-pointer"
            >
              + New Suite
            </button>
            
            <label className="flex items-center gap-1 border border-gray-150 dark:border-zinc-700 rounded-lg p-1 px-2.5 bg-white hover:bg-gray-50 dark:bg-zinc-800 dark:hover:bg-zinc-750 cursor-pointer text-gray-500 dark:text-zinc-300 disabled:opacity-50 text-[11px]">
              <Upload size={11} />
              <span>Import TXT</span>
              <input type="file" accept=".txt,.csv" onChange={handleImportText} disabled={isRunning} className="hidden" />
            </label>

            <button 
              onClick={handleExportText}
              className="flex items-center gap-1 border border-gray-150 dark:border-zinc-700 rounded-lg p-1 px-2.5 bg-white hover:bg-gray-50 dark:bg-zinc-800 dark:hover:bg-zinc-750 text-gray-500 dark:text-zinc-300 transition-all cursor-pointer"
            >
              <Download size={11} />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Dynamic Execution button group */}
        <div className="flex items-center gap-2" id="script-running-controllers">
          {isRunning ? (
            <button
              onClick={onStopScript}
              className="flex items-center gap-1 px-4 py-1.5 bg-[#FF3B30] hover:bg-red-600 text-white rounded-lg font-bold shadow-sm cursor-pointer"
            >
              <Square size={11} fill="currentColor" />
              <span>Stop Sequencer</span>
            </button>
          ) : (
            <button
              onClick={() => onRunScript(activeScript)}
              disabled={!activeScript || isRunning}
              className="flex items-center gap-1 px-4 py-1.5 bg-[#007AFF] hover:bg-blue-600 text-white rounded-lg font-bold shadow-sm disabled:opacity-50 cursor-pointer"
            >
              <Play size={11} fill="currentColor" />
              <span>Run Suite</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. PROGRESS META ROW */}
      <div className="bg-[#FAFBFD] dark:bg-zinc-900 px-4 py-1.5 border-b border-gray-150 dark:border-zinc-800 flex items-center justify-between text-[11px] text-gray-500 dark:text-zinc-400 font-semibold" id="script-status-progress">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${isRunning ? 'bg-[#34C759] animate-pulse' : 'bg-[#AEAEB2]'}`} />
            Status: <strong className={isRunning ? 'text-[#34C759]' : 'text-gray-500'}>
              {isRunning 
                ? `Running (Step ${currentStepIndex + 1}/${activeScript?.steps.length || 0})` 
                : '• Idle'
              }
            </strong>
          </span>
          {isRunning && activeScript?.loop && (
            <span>Loops remaining: <strong>{loopRemaining}</strong></span>
          )}
        </div>

        <div>
          <span>Steps count: <strong>{activeScript?.steps.length || 0}</strong></span>
        </div>
      </div>

      {/* 3. STEPS SCROLLABLE MATRIX (Displaying step sequence) */}
      <div className="flex-1 overflow-auto p-4" id="script-sequence-container">
        {!activeScript || activeScript.steps.length === 0 ? (
          <div className="text-center py-20 text-gray-400 select-none">
            <p className="text-xs font-bold leading-normal">No execution steps planned.</p>
            <p className="text-[10px] text-gray-300 mt-1">Add sequence steps using the dialog or CSV text import helpers.</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-150 text-[10px] text-gray-400 font-bold uppercase tracking-wider select-none">
                  <th className="p-3 text-center w-12">#</th>
                  <th className="p-3">Command / Instructions Directive</th>
                  <th className="p-3 text-center w-24">Priority</th>
                  <th className="p-3 text-center w-28">Wait (ms)</th>
                  <th className="p-3">Status Condition</th>
                  <th className="p-3 text-right w-24">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-medium">
                {activeScript.steps.map((step, idx) => {
                  const isScheduled = isRunning && currentStepIndex === idx;
                  const isDone = isRunning && currentStepIndex > idx;

                  return (
                    <tr 
                      key={idx} 
                      className={`hover:bg-gray-50/40 transition-colors ${
                        isScheduled 
                          ? 'bg-[#E8F2FF] text-[#007AFF]' 
                          : isDone 
                            ? 'text-gray-400 line-through decoration-gray-300' 
                            : 'text-slate-800'
                      }`}
                    >
                      <td className="p-3 text-center font-mono font-bold select-none">{idx + 1}</td>
                      <td className="p-3">
                        <div className="font-mono font-bold break-all flex flex-col">
                          <span>{step.cmd}</span>
                          {step.wait_keyword && (
                            <span className="text-[9px] text-indigo-500 font-bold mt-1">
                              ⟶ wait keyword: &quot;{step.wait_keyword}&quot; (timeout: {step.wait_timeout_ms || step.wait_ms}ms)
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-center font-bold">{step.priority}</td>
                      <td className="p-3 text-center font-bold pr-4">{step.wait_ms} ms</td>
                      <td className="p-3 select-none">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          isScheduled 
                            ? 'bg-blue-100 text-blue-700 animate-pulse' 
                            : isDone 
                              ? 'bg-gray-100 text-gray-500' 
                              : 'bg-slate-100 text-gray-500'
                        }`}>
                          {isScheduled ? '▶ Running' : isDone ? '✓ Done' : 'Pending'}
                        </span>
                      </td>
                      <td className="p-3 text-right select-none" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1.5 opacity-80 hover:opacity-100 transition-opacity">
                          {/* Arrange index button lists */}
                          <button 
                            disabled={idx === 0 || isRunning} 
                            onClick={() => handleMoveStep(idx, -1)} 
                            className="text-gray-400 hover:text-gray-800 disabled:opacity-30"
                          >
                            <ArrowUp size={11} className="stroke-[2.5px]" />
                          </button>
                          
                          <button 
                            disabled={idx === activeScript.steps.length - 1 || isRunning} 
                            onClick={() => handleMoveStep(idx, 1)} 
                            className="text-gray-400 hover:text-gray-800 disabled:opacity-30"
                          >
                            <ArrowDown size={11} className="stroke-[2.5px]" />
                          </button>

                          <button 
                            disabled={isRunning}
                            onClick={() => handleOpenStepModal('edit', step, idx)}
                            className="text-blue-500 hover:text-blue-600 disabled:opacity-30"
                          >
                            <Edit size={11} />
                          </button>

                          <button 
                            disabled={isRunning || activeScript.steps.length <= 1}
                            onClick={() => handleDeleteStep(idx)}
                            className="text-red-500 hover:text-red-600 disabled:opacity-40"
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Append new step option row */}
        {!isRunning && activeScript && (
          <button
            onClick={() => handleOpenStepModal('create')}
            className="mt-3.5 w-full flex items-center justify-center gap-1 text-xs font-bold text-gray-500 hover:text-[#007AFF] bg-gray-50 hover:bg-[#E8F2FF] border border-dashed border-gray-250 hover:border-[#007AFF] py-2.5 rounded-xl transition-all cursor-pointer"
          >
            <Plus size={13} className="stroke-[3px]" />
            <span>Add Sequence Step Directive</span>
          </button>
        )}
      </div>

      {/* MODAL 1: ADD/EDIT SCRIPT SUITE DETAILS */}
      {showScriptModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800">
            <h3 className="text-sm font-bold text-slate-800">{modalType === 'create' ? "New Script Suite" : "Edit Suite Settings"}</h3>
            
            <div className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-gray-400 tracking-wide uppercase">Suite Name</label>
                <input
                  type="text"
                  placeholder="e.g. ESP32 Stress Diagnostics"
                  value={scriptName}
                  onChange={(e) => setScriptName(e.target.value)}
                  className="w-full text-xs bg-gray-55 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-gray-50">
                <span className="font-bold text-gray-500">Loop Executions Match</span>
                <input
                  type="checkbox"
                  checked={scriptLoop}
                  onChange={(e) => setScriptLoop(e.target.checked)}
                  className="rounded text-[#007AFF] border-gray-200 h-4 w-4 cursor-pointer"
                />
              </div>

              {scriptLoop && (
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-gray-400 tracking-wide uppercase">Loops Count Repeat</label>
                  <input
                    type="number"
                    min={1}
                    max={9999}
                    value={scriptLoopCount}
                    onChange={(e) => setScriptLoopCount(Math.max(1, Number(e.target.value)))}
                    className="w-full text-xs bg-gray-55 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 text-xs font-bold pt-1 border-t border-gray-100">
              <button onClick={() => setShowScriptModal(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Cancel</button>
              <button onClick={handleSaveScriptSettings} className="px-4 py-2 bg-[#007AFF] text-white rounded-lg hover:bg-blue-600 cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD/EDIT STEP SPECIFICS */}
      {showStepModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800">
            <h3 className="text-sm font-bold text-slate-800">{modalType === 'create' ? "Add Execution Command" : "Edit Step Directive"}</h3>
            
            <div className="space-y-3.5 text-xs text-left">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-gray-400">Step Command (TEXT/HEX payload)</label>
                <input
                  type="text"
                  placeholder="e.g. AT+CWCAP"
                  value={stepCmd}
                  onChange={(e) => setStepCmd(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-gray-400">Priority Ordering</label>
                  <input
                    type="number"
                    min={1}
                    value={stepPriority}
                    onChange={(e) => setStepPriority(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-gray-400">Step Wait Delay (ms)</label>
                  <input
                    type="number"
                    min={0}
                    value={stepWaitMs}
                    onChange={(e) => setStepWaitMs(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 outline-none"
                  />
                </div>
              </div>

              <div className="h-px bg-gray-100" />

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-gray-400">Expected Wait Keyword (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. OK, READY, or SUCCESS"
                  value={stepKeyword}
                  onChange={(e) => setStepKeyword(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
                />
              </div>

              {stepKeyword && (
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-gray-400">Keyword Timeout (ms - default is Wait Delay)</label>
                  <input
                    type="number"
                    min={0}
                    placeholder="e.g. 5000"
                    value={stepTimeout}
                    onChange={(e) => setStepTimeout(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 outline-none"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 text-xs font-bold pt-2 border-t border-gray-100">
              <button onClick={() => setShowStepModal(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Cancel</button>
              <button onClick={handleSaveStep} className="px-4 py-2 bg-[#34C759] text-white rounded-lg hover:bg-[#30B650] cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
