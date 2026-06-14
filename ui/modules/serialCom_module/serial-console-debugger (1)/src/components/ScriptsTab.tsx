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
    <div className="flex flex-col h-full bg-white dark:bg-[#020617]" id="automated-script-sequencer">
      
      {/* 1. SCRIPT TOOLBAR CONTROLS */}
      <div className="bg-slate-50/50 dark:bg-slate-900/50 px-4 py-2 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between text-xs select-none backdrop-blur-md" id="script-toolbar-controls">
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-500 dark:text-slate-500">Run File:</span>
          {activeScript ? (
            <div className="flex items-center gap-2">
              <select
                value={activeScriptId}
                onChange={(e) => setActiveScriptId(e.target.value)}
                disabled={isRunning}
                className="bg-white dark:bg-slate-900 dark:bg-slate-700 dark:bg-slate-100 font-bold text-xs border border-slate-200/80 px-2 py-1.5 rounded-lg focus:outline-none shadow-sm disabled:opacity-50"
              >
                {scripts.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>

              <button 
                onClick={handleEditScriptSettings}
                disabled={isRunning}
                className="text-slate-400 hover:text-blue-600 dark:hover:text-slate-500 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 p-1.5 rounded-lg border border-transparent hover:border-blue-200/50 dark:hover:border-blue-500/20 disabled:opacity-40 transition-colors"
              >
                <Edit size={14} />
              </button>

              <button 
                onClick={handleDeleteScript}
                disabled={isRunning || scripts.length <= 1}
                className="text-slate-400 hover:text-rose-600 dark:hover:text-slate-500 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 p-1.5 rounded-lg border border-transparent hover:border-rose-200/50 dark:hover:border-rose-500/20 disabled:opacity-40 transition-colors"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ) : (
            <span className="text-gray-400 italic">No script selected</span>
          )}

          <div className="h-4 w-px bg-slate-200 dark:bg-slate-750" />

          {/* New / Import / Export buttons */}
          <div className="flex items-center gap-2" id="script-folder-triggers">
            <button 
              onClick={handleCreateScript}
              disabled={isRunning}
              className="px-2.5 py-1.5 bg-white hover:bg-blue-50 dark:hover:bg-slate-900 dark:hover:bg-blue-500/10 hover:text-blue-600 dark:hover:text-blue-400 dark:text-slate-700 dark:bg-slate-200 border border-slate-200/80 rounded-lg text-slate-600 font-bold transition-all disabled:opacity-50 cursor-pointer shadow-sm"
            >
              + New Suite
            </button>
            
            <label className="flex items-center gap-1.5 border border-slate-200/80 dark:border-slate-800/80 rounded-lg py-1.5 px-2.5 bg-white hover:bg-slate-50 dark:hover:bg-slate-900 dark:bg-slate-800 cursor-pointer text-slate-500 dark:text-slate-300 disabled:opacity-50 text-[11px] font-bold shadow-sm transition-colors">
              <Upload size={12} />
              <span>Import TXT</span>
              <input type="file" accept=".txt,.csv" onChange={handleImportText} disabled={isRunning} className="hidden" />
            </label>

            <button 
              onClick={handleExportText}
              className="flex items-center gap-1.5 border border-slate-200/80 dark:border-slate-800/80 rounded-lg py-1.5 px-2.5 bg-white hover:bg-blue-50 text-slate-500 hover:text-blue-600 dark:hover:text-slate-900 dark:hover:bg-blue-500/10 dark:bg-slate-300 dark:hover:text-blue-400 transition-all cursor-pointer font-bold shadow-sm"
            >
              <Download size={12} />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Dynamic Execution button group */}
        <div className="flex items-center gap-2" id="script-running-controllers">
          {isRunning ? (
            <button
              onClick={onStopScript}
              className="flex items-center gap-1.5 px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white rounded-lg font-bold shadow-sm cursor-pointer active:scale-95 transition-all focus:ring-4 focus:ring-rose-500/20"
            >
              <Square size={13} fill="currentColor" />
              <span>Stop Sequencer</span>
            </button>
          ) : (
            <button
              onClick={() => onRunScript(activeScript)}
              disabled={!activeScript || isRunning}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold shadow-sm disabled:opacity-50 cursor-pointer active:scale-95 transition-all focus:ring-4 focus:ring-emerald-500/20"
            >
              <Play size={13} fill="currentColor" />
              <span>Run Suite</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. PROGRESS META ROW */}
      <div className="bg-slate-50 border-b border-slate-200/80 dark:border-slate-950 dark:border-slate-800/80 px-4 py-2 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-bold" id="script-status-progress">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full shadow-sm ${isRunning ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-300 dark:bg-slate-700'}`} />
            Status: <span className={isRunning ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-slate-500'}>
              {isRunning 
                ? `Running (Step ${currentStepIndex + 1}/${activeScript?.steps.length || 0})` 
                : 'Idle'
              }
            </span>
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
      <div className="flex-1 overflow-auto p-4 bg-slate-50/50 dark:bg-[#020617]/50" id="script-sequence-container">
        {!activeScript || activeScript.steps.length === 0 ? (
          <div className="text-center py-24 text-slate-400 select-none flex flex-col items-center">
            <div className="h-12 w-12 rounded-2xl bg-white dark:bg-slate-900 shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-center mb-4">
              <Square size={20} className="text-slate-300 dark:text-slate-600" />
            </div>
            <p className="text-xs font-bold leading-normal text-slate-500 dark:text-slate-400">No execution steps planned.</p>
            <p className="text-[11px] font-medium text-slate-400 dark:text-slate-500 mt-1">Add sequence steps using the dialog or CSV text import helpers.</p>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200/80 dark:border-slate-800/80 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/80 dark:bg-slate-950/80 border-b border-slate-200/80 dark:border-slate-800/80 text-[10px] text-slate-400 dark:text-slate-500 font-bold tracking-wider select-none backdrop-blur-sm">
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
                      className={`hover:bg-slate-50 dark:bg-slate-800/50 transition-colors border-b last:border-b-0 border-slate-100 dark:border-slate-800/50 ${
                        isScheduled 
                          ? 'bg-blue-50/50 dark:bg-blue-900/10' 
                          : isDone 
                            ? 'text-slate-400 opacity-60' 
                            : 'text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <td className={`p-3 text-center font-mono font-bold select-none ${isScheduled ? 'text-blue-600 dark:text-blue-400' : ''}`}>{idx + 1}</td>
                      <td className="p-3">
                        <div className={`font-mono font-bold break-all flex flex-col ${isScheduled ? 'text-blue-600 dark:text-blue-400' : ''}`}>
                          <span>{step.cmd}</span>
                          {step.wait_keyword && (
                            <span className="text-[10px] text-indigo-500 dark:text-indigo-400 mt-1 opacity-90">
                              ⟶ wait keyword: &quot;{step.wait_keyword}&quot; (timeout: {step.wait_timeout_ms || step.wait_ms}ms)
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-center font-bold">{step.priority}</td>
                      <td className="p-3 text-center font-bold pr-4 font-mono text-[11px]">{step.wait_ms} ms</td>
                      <td className="p-3 select-none">
                        <span className={`text-[10px] font-bold px-2 py-1 rounded inline-flex items-center gap-1 ${
                          isScheduled 
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400 ring-1 ring-blue-500/30' 
                            : isDone 
                              ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400' 
                              : 'bg-slate-100 text-slate-500 dark:text-slate-800 dark:text-slate-400'
                        }`}>
                          {isScheduled && <span className="h-1.5 w-1.5 rounded-full bg-blue-600 dark:bg-blue-400 animate-pulse" />}
                          {isScheduled ? 'Running' : isDone ? 'Done' : 'Pending'}
                        </span>
                      </td>
                      <td className="p-3 text-right select-none" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          {/* Arrange index button lists */}
                          <button 
                            disabled={idx === 0 || isRunning} 
                            onClick={() => handleMoveStep(idx, -1)} 
                            className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 p-1 rounded transition-colors"
                          >
                            <ArrowUp size={13} className="stroke-[2.5px]" />
                          </button>
                          
                          <button 
                            disabled={idx === activeScript.steps.length - 1 || isRunning} 
                            onClick={() => handleMoveStep(idx, 1)} 
                            className="text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 p-1 rounded transition-colors"
                          >
                            <ArrowDown size={13} className="stroke-[2.5px]" />
                          </button>

                          <button 
                            disabled={isRunning}
                            onClick={() => handleOpenStepModal('edit', step, idx)}
                            className="text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 disabled:opacity-30 p-1 rounded transition-colors"
                          >
                            <Edit size={13} />
                          </button>

                          <button 
                            disabled={isRunning || activeScript.steps.length <= 1}
                            onClick={() => handleDeleteStep(idx)}
                            className="text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 disabled:opacity-40 p-1 rounded transition-colors"
                          >
                            <Trash2 size={13} />
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
            className="mt-4 w-full flex items-center justify-center gap-2 text-xs font-bold text-slate-500 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 bg-white/50 dark:bg-slate-900/50 hover:bg-blue-50 dark:hover:bg-blue-900/10 border border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-400 dark:hover:border-blue-500 py-3 rounded-xl transition-all cursor-pointer group"
          >
            <div className="bg-slate-200 dark:bg-slate-800 group-hover:bg-blue-200 dark:group-hover:bg-blue-900 rounded-full p-1 transition-colors">
              <Plus size={14} className="stroke-[3px]" />
            </div>
            <span>Add Sequence Step Directive</span>
          </button>
        )}
      </div>

      {/* MODAL 1: ADD/EDIT SCRIPT SUITE DETAILS */}
      {showScriptModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-900 rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800 dark:text-slate-100 border border-transparent dark:border-slate-800">
            <h3 className="text-sm font-bold">{modalType === 'create' ? "New Script Suite" : "Edit Suite Settings"}</h3>
            
            <div className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400 tracking-wide uppercase">Suite Name</label>
                <input
                  type="text"
                  placeholder="e.g. ESP32 Stress Diagnostics"
                  value={scriptName}
                  onChange={(e) => setScriptName(e.target.value)}
                  className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-slate-100 dark:border-slate-800">
                <span className="font-bold text-slate-500 dark:text-slate-400">Loop Executions Match</span>
                <input
                  type="checkbox"
                  checked={scriptLoop}
                  onChange={(e) => setScriptLoop(e.target.checked)}
                  className="rounded text-blue-600 border-slate-200 dark:border-slate-700 dark:border-slate-800 h-4 w-4 cursor-pointer focus:ring-blue-500"
                />
              </div>

              {scriptLoop && (
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400 tracking-wide uppercase">Loops Count Repeat</label>
                  <input
                    type="number"
                    min={1}
                    max={9999}
                    value={scriptLoopCount}
                    onChange={(e) => setScriptLoopCount(Math.max(1, Number(e.target.value)))}
                    className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 outline-none"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 text-xs font-bold pt-1 border-t border-slate-100 dark:border-slate-800">
              <button onClick={() => setShowScriptModal(false)} className="px-4 py-2 border border-slate-200 dark:border-slate-700 dark:border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">Cancel</button>
              <button onClick={handleSaveScriptSettings} className="px-4 py-2 bg-blue-600 dark:bg-blue-600 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-500 cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD/EDIT STEP SPECIFICS */}
      {showStepModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-slate-900 rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800 dark:text-slate-100 border border-transparent dark:border-slate-800">
            <h3 className="text-sm font-bold">{modalType === 'create' ? "Add Execution Command" : "Edit Step Directive"}</h3>
            
            <div className="space-y-3.5 text-xs text-left">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400">Step Command (TEXT/HEX payload)</label>
                <input
                  type="text"
                  placeholder="e.g. AT+CWCAP"
                  value={stepCmd}
                  onChange={(e) => setStepCmd(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400">Priority Ordering</label>
                  <input
                    type="number"
                    min={1}
                    value={stepPriority}
                    onChange={(e) => setStepPriority(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400">Step Wait Delay (ms)</label>
                  <input
                    type="number"
                    min={0}
                    value={stepWaitMs}
                    onChange={(e) => setStepWaitMs(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="h-px bg-slate-100 dark:bg-slate-800" />

              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400">Expected Wait Keyword (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. OK, READY, or SUCCESS"
                  value={stepKeyword}
                  onChange={(e) => setStepKeyword(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 focus:ring-1 focus:ring-blue-500 outline-none"
                />
              </div>

              {stepKeyword && (
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-slate-400 dark:text-slate-400">Keyword Timeout (ms - default is Wait Delay)</label>
                  <input
                    type="number"
                    min={0}
                    placeholder="e.g. 5000"
                    value={stepTimeout}
                    onChange={(e) => setStepTimeout(Number(e.target.value))}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 text-xs font-bold pt-2 border-t border-slate-100 dark:border-slate-800">
              <button onClick={() => setShowStepModal(false)} className="px-4 py-2 border border-slate-200 dark:border-slate-700 dark:border-slate-300 rounded-lg text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">Cancel</button>
              <button onClick={handleSaveStep} className="px-4 py-2 bg-green-500 dark:bg-green-600 text-white rounded-lg hover:bg-green-600 dark:hover:bg-green-500 cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
