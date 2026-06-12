export type LogType = 'rx' | 'tx' | 'info' | 'warn' | 'error' | 'sys';

export interface LogItem {
  id: string;
  timestamp: string;
  type: LogType;
  text: string;
  ntpTimestamp?: string;
}

export interface QuickCommand {
  id: string;
  name: string;
  content: string;
  send_type: 'text' | 'hex';
  line_ending: string;
  encoding: string;
  target_session_id?: string;
}

export interface QuickGroup {
  id: string;
  name: string;
  commands: QuickCommand[];
}

export interface QuickProject {
  id: string;
  name: string;
  groups: QuickGroup[];
}

export interface ScriptStep {
  cmd: string;
  priority: number;
  wait_ms: number;
  wait_keyword: string;
  wait_timeout_ms: number;
}

export interface Script {
  id: string;
  name: string;
  loop: boolean;
  loop_count: number;
  steps: ScriptStep[];
}

export interface SerialConfig {
  port: string;
  baudrate: number;
  databits: number;
  stopbits: '1' | '1.5' | '2';
  parity: 'None' | 'Even' | 'Odd' | 'Mark' | 'Space';
  flowControl: 'None' | 'RTS/CTS' | 'XON/XOFF';
  autoDetect: boolean;
}

export interface LogPanel {
  id: string;
  title: string;
  port: string;
  baudrate: number;
  databits: number;
  stopbits: '1' | '1.5' | '2';
  parity: 'None' | 'Even' | 'Odd' | 'Mark' | 'Space';
  flowControl: 'None' | 'RTS/CTS' | 'XON/XOFF';
  rxBytes: number;
  txBytes: number;
  isConnected: boolean;
  isMock: boolean;
  allLogs: LogItem[];
  filterKeyword: string;
  filterRegex: boolean;
  filterCase: boolean;
  filterInvert: boolean;
  filterBefore: number;
  filterAfter: number;
  autoScroll: boolean;
  showTime: boolean;
  useNtp: boolean;
  showSent: boolean;
  lineByLine: boolean;
  maxLines: number;
  rxFormat: 'ASCII' | 'HEX';
  txFormat: 'ASCII' | 'HEX';
  lineEnding: string;
  autoFlush: boolean;
  autoFlushMs: number;
}

export interface AutoBaudSettings {
  enabled: boolean;
  runtimeRedetectEnabled: boolean;
  candidateBaudrates: number[];
  lockThreshold: number;
  badThreshold: number;
  badWindowsToSuspect: number;
  suspectWindowsToScan: number;
  monitorWindowMaxTimeMs: number;
  switchCooldownMs: number;
  switchScoreMargin: number;
  confirmScanRounds: number;
}
