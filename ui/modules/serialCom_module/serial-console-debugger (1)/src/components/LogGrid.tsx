import React, { useRef, useEffect, useState } from 'react';
import { LogPanel, LogItem, LogType } from '../types';
import { formatByteCount } from '../utils/serialHelper';
import { 
  Filter, Copy, Download, Save, Trash2, ArrowDown, ChevronDown, Cpu 
} from 'lucide-react';

// Custom highlight parsing helper matching Python utility `_sc_html_with_filter_highlight`
const highlightMatch = (text: string, keyword: string, isRegex: boolean, isCase: boolean): React.ReactNode => {
  if (!keyword) return text;
  try {
    const flags = isCase ? 'g' : 'gi';
    const escapedKeyword = isRegex ? keyword : keyword.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`(${escapedKeyword})`, flags);
    const parts = text.split(regex);
    return (
      <>
        {parts.map((part, i) => 
          regex.test(part) ? (
            <mark key={i} className="bg-blue-100 text-blue-700 border border-blue-400 px-0.5 rounded-sm font-semibold">
              {part}
            </mark>
          ) : part
        )}
      </>
    );
  } catch {
    return text;
  }
};

// Perform before/after context logging filters
const getFilteredLogs = (panel: LogPanel): { logs: LogItem[]; indices: Set<number> } => {
  const { allLogs, filterKeyword, filterRegex, filterCase, filterInvert, filterBefore, filterAfter } = panel;
  if (!filterKeyword) {
    return { logs: allLogs, indices: new Set(allLogs.map((_, i) => i)) };
  }

  const matchedIndices: number[] = [];
  const keywordLower = filterKeyword.toLowerCase();

  // Find direct matches
  allLogs.forEach((log, index) => {
    let isMatch = false;
    if (filterRegex) {
      try {
        const regex = new RegExp(filterKeyword, filterCase ? 'i' : 'gi');
        isMatch = regex.test(log.text);
      } catch {
        isMatch = false;
      }
    } else {
      const textTarget = filterCase ? log.text : log.text.toLowerCase();
      const searchTarget = filterCase ? filterKeyword : keywordLower;
      isMatch = textTarget.includes(searchTarget);
    }

    if (filterInvert) {
      isMatch = !isMatch;
    }

    if (isMatch) {
      matchedIndices.push(index);
    }
  });

  // Expand to include Before and After context blocks
  const finalSet = new Set<number>();
  matchedIndices.forEach(idx => {
    const start = Math.max(0, idx - filterBefore);
    const end = Math.min(allLogs.length - 1, idx + filterAfter);
    for (let i = start; i <= end; i++) {
      finalSet.add(i);
    }
  });

  const logs: LogItem[] = [];
  allLogs.forEach((log, i) => {
    if (finalSet.has(i)) {
      logs.push(log);
    }
  });

  return { logs, indices: new Set(matchedIndices) };
};

// Copy logs logic
const handleCopyLogs = (panel: LogPanel) => {
  const text = panel.allLogs.map(l => `${l.timestamp} ${l.text}`).join('\n');
  navigator.clipboard.writeText(text);
};

// Export diagnostic files download
const handleExportLogs = (panel: LogPanel) => {
  const blob = new Blob([panel.allLogs.map(l => `${l.timestamp} ${l.text}`).join('\n')], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${panel.title.replace(/\s+/g, '_').toLowerCase()}_port_output.log`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

interface LogPanelCardProps {
  key?: string | number;
  panel: LogPanel;
  idx: number;
  isActive: boolean;
  setActivePanelIndex: (idx: number) => void;
  updatePanelSettings: (idx: number, settings: Partial<LogPanel>) => void;
  onClearLogs: (idx: number) => void;
}

function LogPanelCard({
  panel,
  idx,
  isActive,
  setActivePanelIndex,
  updatePanelSettings,
  onClearLogs
}: LogPanelCardProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { logs: displayLogs, indices: directMatchSet } = getFilteredLogs(panel);
  const [isFilterOpen, setIsFilterOpen] = useState(() => !!panel.filterKeyword);

  // Track auto-scroll behaviour perfectly on streaming additions
  useEffect(() => {
    if (panel.autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [panel.allLogs.length, panel.autoScroll]);

  // Scroll listener to toggle autoScroll when user scrolls up
  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 15;
    if (isAtBottom && !panel.autoScroll) {
      updatePanelSettings(idx, { autoScroll: true });
    } else if (!isAtBottom && panel.autoScroll) {
      updatePanelSettings(idx, { autoScroll: false });
    }
  };

  const getLogColorClass = (type: LogType): string => {
    switch (type) {
      case 'rx': return 'text-slate-800 dark:text-slate-300'; // Charcoal for RX
      case 'tx': return 'text-blue-600 dark:text-blue-400 font-medium'; // Deep Apple Blue for TX
      case 'info': return 'text-cyan-600 dark:text-cyan-500 font-semibold'; // Info cyan-blue
      case 'warn': return 'text-amber-500 dark:text-amber-400 font-semibold'; // Amber warning
      case 'error': return 'text-red-500 dark:text-red-400 font-semibold'; // Red warning
      case 'sys': return 'text-violet-500 dark:text-violet-400 italic'; // Violet system notes
      default: return 'text-slate-700 dark:text-slate-400';
    }
  };

  return (
    <div
      onClick={() => setActivePanelIndex(idx)}
      className={`bg-white/80 dark:bg-slate-950/80 backdrop-blur-md rounded-2xl flex flex-col h-full shadow-sm overflow-hidden transition-all duration-300 border-[1px] ${
        isActive 
          ? 'border-blue-500 shadow-[0_4px_24px_-4px_rgba(59,130,246,0.15)] ring-4 ring-blue-500/10' 
          : 'border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700/80'
      }`}
      id={`log-card-panel-${idx}`}
    >
      {/* CARD HEADER bar */}
      <div className="bg-slate-50/50 dark:bg-slate-900/50 border-b border-slate-200/80 dark:border-slate-800/80 px-4 py-2.5 flex items-center justify-between text-xs select-none backdrop-blur-sm" id="log-card-meta-toolbar">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full shadow-sm ${panel.isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-300/80 dark:bg-slate-700/80'}`} />
          <span className="font-bold text-slate-800 dark:text-slate-100 tracking-tight">{panel.title}</span>
          <span className="text-[10px] text-slate-500 dark:text-slate-400 font-bold bg-slate-200/50 dark:bg-slate-800/50 px-2 py-0.5 rounded-md">
            {panel.port ? panel.port.split(' ')[0] : 'Idle'}
          </span>
        </div>

        {/* Header Action Tools */}
        <div className="flex items-center gap-1.5" id="header-card-tool-icons">
          {/* Search Filter toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              const nextState = !isFilterOpen;
              setIsFilterOpen(nextState);
              if (!nextState && panel.filterKeyword) {
                updatePanelSettings(idx, { filterKeyword: '' });
              }
            }}
            title="Toggle Filter Panel"
            className={`p-1.5 rounded-md transition-colors cursor-pointer ${
              isFilterOpen 
                ? 'text-blue-600 bg-blue-50 dark:bg-blue-900/40 dark:text-blue-400 font-bold' 
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <Filter size={13} />
          </button>

          {/* Copy logs */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopyLogs(panel);
            }}
            title="Copy terminal buffer"
            className="p-1.5 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <Copy size={13} />
          </button>

          {/* Export Log */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleExportLogs(panel);
            }}
            title="Download device log"
            className="p-1.5 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <Download size={13} />
          </button>

          {/* Clear Board Screen */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClearLogs(idx);
            }}
            title="Flush screen logs"
            className="p-1.5 rounded-md text-slate-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
          >
            <Trash2 size={13} />
          </button>

          {/* Auto Scroll Lock toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              updatePanelSettings(idx, { autoScroll: !panel.autoScroll });
            }}
            title={panel.autoScroll ? "Lock Scroll down" : "Release Lock"}
            className={`p-1.5 rounded-md transition-colors cursor-pointer ${
              panel.autoScroll 
                ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 dark:text-emerald-400 font-bold' 
                : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <ArrowDown size={13} className={panel.autoScroll ? "animate-bounce" : ""} />
          </button>
        </div>
      </div>

      {/* FILTER PANEL ROW */}
      {isFilterOpen && (
        <div className="bg-white dark:bg-slate-950 border-b border-slate-100 dark:border-slate-800 p-2.5 text-xs space-y-2 animate-fade-in" id="filter-input-toolbar" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Enter keyword or search query..."
              value={panel.filterKeyword}
              onChange={(e) => updatePanelSettings(idx, { filterKeyword: e.target.value })}
              className="flex-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 focus:border-blue-500 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none rounded-md px-2 py-1 outline-none text-[11px] text-slate-800 dark:text-slate-100"
            />
            
            {panel.filterKeyword && (
              <span className="text-[10px] text-indigo-600 dark:text-indigo-400 font-bold bg-indigo-50 dark:bg-indigo-950/40 px-1.5 py-0.5 rounded">
                Matches: {directMatchSet.size}
              </span>
            )}
          </div>

          {/* Filter Modifiers checkboxes and After/Before Lines spins */}
          <div className="flex items-center flex-wrap gap-x-4 gap-y-1.5 text-[10px] text-slate-500 dark:text-slate-400 font-semibold select-none">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={panel.filterRegex}
                onChange={(e) => updatePanelSettings(idx, { filterRegex: e.target.checked })}
                className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-800 h-3 w-3 focus:ring-blue-500"
              />
              <span>Regex</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={panel.filterCase}
                onChange={(e) => updatePanelSettings(idx, { filterCase: e.target.checked })}
                className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-800 h-3 w-3 focus:ring-blue-500"
              />
              <span>Match Case</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={panel.filterInvert}
                onChange={(e) => updatePanelSettings(idx, { filterInvert: e.target.checked })}
                className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-800 h-3 w-3 focus:ring-blue-500"
              />
              <span>Invert</span>
            </label>

            <div className="h-3 w-px bg-slate-200 dark:bg-slate-700" />

            {/* Context Blocks Before spin */}
            <div className="flex items-center gap-1">
              <span>Before</span>
              <input
                type="number"
                min={0}
                max={50}
                value={panel.filterBefore}
                onChange={(e) => updatePanelSettings(idx, { filterBefore: Math.max(0, Number(e.target.value)) })}
                className="w-10 text-center bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded p-0.5 text-[10px] focus:outline-none focus:border-blue-500"
              />
              <span className="text-[9px] text-slate-400 dark:text-slate-500">lines</span>
            </div>

            {/* Context Blocks After spin */}
            <div className="flex items-center gap-1">
              <span>After</span>
              <input
                type="number"
                min={0}
                max={50}
                value={panel.filterAfter}
                onChange={(e) => updatePanelSettings(idx, { filterAfter: Math.max(0, Number(e.target.value)) })}
                className="w-10 text-center bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 rounded p-0.5 text-[10px] focus:outline-none focus:border-blue-500"
              />
              <span className="text-[9px] text-slate-400 dark:text-slate-500">lines</span>
            </div>
          </div>
        </div>
      )}

      {/* TERMINAL PRINT WINDOW */}
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed bg-transparent outline-none select-text selection:bg-blue-100 dark:selection:bg-blue-900/40 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800"
        id={`terminal-view-${idx}`}
      >
        {displayLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center h-full text-slate-300 py-12 select-none">
            <Cpu size={28} className="stroke-[1.5] mb-2 opacity-50 text-slate-400" />
            <p className="text-xs font-semibold text-slate-400">No data received</p>
            <p className="text-[10px] text-slate-400 mt-1">Configure serial ports on the sidebar to get started.</p>
          </div>
        ) : (
          <div className="space-y-1 block max-w-full overflow-hidden select-text text-left">
            {displayLogs.map((log) => {
              return (
                <div key={log.id} className="hover:bg-slate-50 dark:bg-slate-900/50 py-0.5 rounded px-1 transition-colors flex items-start gap-2 break-all text-left">
                  {/* Timestamps */}
                  {panel.showTime && (
                    <span className="text-slate-400 dark:text-slate-500 select-none text-[10px] pr-1.5 border-r border-slate-100 dark:border-slate-800 flex-shrink-0 font-medium">
                      {log.timestamp}
                    </span>
                  )}
                  {/* Custom NTP calibration index prefix */}
                  {panel.useNtp && log.ntpTimestamp && (
                    <span className="text-amber-500 font-bold select-none text-[10px] flex-shrink-0">
                      [NTP] {log.ntpTimestamp}
                    </span>
                  )}
                  {/* Log Text */}
                  <span className={`flex-1 text-left ${getLogColorClass(log.type)}`}>
                    {panel.filterKeyword 
                      ? highlightMatch(log.text, panel.filterKeyword, panel.filterRegex, panel.filterCase)
                      : log.text
                    }
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* CARD STATUS FOOTER */}
      <div className="bg-slate-50/50 dark:bg-slate-900/50 border-t border-slate-200/80 dark:border-slate-800/80 px-4 py-2 flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 select-none backdrop-blur-sm" id="log-card-footer">
        <div className="flex gap-4">
          <span>Port: <strong className="text-slate-700 dark:text-slate-300 font-bold">{panel.port ? panel.port.split(' ')[0] : 'None'}</strong></span>
          <span>Baudrate: <strong className="text-slate-700 dark:text-slate-300 font-bold">{panel.baudrate} bps</strong></span>
        </div>
        <div className="flex gap-4 font-mono font-medium">
          <span className="text-slate-700 dark:text-slate-300">RX: <strong className="font-bold">{formatByteCount(panel.rxBytes)}</strong></span>
          <span className="text-blue-600 dark:text-blue-400">TX: <strong className="font-bold">{formatByteCount(panel.txBytes)}</strong></span>
        </div>
      </div>
    </div>
  );
}

interface LogGridProps {
  panels: LogPanel[];
  activePanelIndex: number;
  setActivePanelIndex: (idx: number) => void;
  updatePanelSettings: (idx: number, settings: Partial<LogPanel>) => void;
  onClearLogs: (idx: number) => void;
}

export function LogGrid({
  panels,
  activePanelIndex,
  setActivePanelIndex,
  updatePanelSettings,
  onClearLogs
}: LogGridProps) {
  return (
    <div 
      className={`grid gap-4 h-full p-4 bg-slate-50 dark:bg-[#070709] flex-1 ${
        panels.length === 1 
          ? 'grid-cols-1 grid-rows-1' 
          : panels.length === 2 
            ? 'grid-cols-2 grid-rows-1' 
            : 'grid-cols-2 grid-rows-2'
      }`}
      id="logs-quadrants-grid"
    >
      {panels.map((panel, idx) => (
        <LogPanelCard
          key={panel.id}
          panel={panel}
          idx={idx}
          isActive={activePanelIndex === idx}
          setActivePanelIndex={setActivePanelIndex}
          updatePanelSettings={updatePanelSettings}
          onClearLogs={onClearLogs}
        />
      ))}
    </div>
  );
}
