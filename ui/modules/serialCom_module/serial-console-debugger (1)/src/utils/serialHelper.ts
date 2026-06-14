import { LogItem, QuickProject, Script, LogType } from '../types';

export const SUPPORTED_BAUDRATES = [
  9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1152000, 2000000, 3000000
];

// Helper to check browser Web Serial support
export function isWebSerialSupported(): boolean {
  return typeof navigator !== 'undefined' && 'serial' in navigator;
}

// Convert string to Uint8Array with specific encoding
export function encodeText(text: string, encoding: string = 'utf-8'): Uint8Array {
  // Mostly browsers natively support UTF-8/ASCII via TextEncoder
  const encoder = new TextEncoder();
  return encoder.encode(text);
}

// Decode Uint8Array to string
export function decodeText(bytes: Uint8Array): string {
  const decoder = new TextDecoder('utf-8', { fatal: false });
  return decoder.decode(bytes);
}

// Convert HEX string to bytes
export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.replace(/[^0-9A-Fa-f]/g, '');
  if (clean.length % 2 !== 0) {
    throw new Error('Invalid hexadecimal string');
  }
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < clean.length; i += 2) {
    bytes[i / 2] = parseInt(clean.substring(i, i + 2), 16);
  }
  return bytes;
}

// Convert bytes to HEX string spaced every 2 characters
export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0').toUpperCase())
    .join(' ');
}

// Format byte counts into human readable strings
export function formatByteCount(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// NTP offset simulation
let ntpOffsetMs = 0;
let ntpSynced = false;

export function simulateNtpSync(): Promise<{ offset: number; rtt: number }> {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Simulate typical network latency and alignment offset (-200ms to +200ms)
      const offset = (Math.random() * 400) - 200;
      const rtt = Math.random() * 80 + 10; // 10ms - 90ms latency
      ntpOffsetMs = offset;
      ntpSynced = true;
      resolve({ offset, rtt });
    }, 800);
  });
}

// Return formatted time (local or simulated NTP) with millisecond precision
export function getFormattedTimestamp(useNtp: boolean = false): string {
  const now = new Date();
  if (useNtp && ntpSynced) {
    now.setTime(now.getTime() + ntpOffsetMs);
  }
  const hrs = now.getHours().toString().padStart(2, '0');
  const mins = now.getMinutes().toString().padStart(2, '0');
  const secs = now.getSeconds().toString().padStart(2, '0');
  const ms = now.getMilliseconds().toString().padStart(3, '0');
  return `${hrs}:${mins}:${secs}.${ms}`;
}

// Generates simulated Serial feedback when ports are working in simulation mode
export const MOCK_DEVICES = [
  { port: 'COM3 (Simulation)', name: 'ESP32 NodeMCU Development Board' },
  { port: 'COM5 (Simulation)', name: 'Arduino Nano ATMega328P' },
  { port: 'COM9 (Simulation)', name: 'Modbus Industrial Temp/Humidity Sensor' },
  { port: 'COM12 (Simulation)', name: 'High-speed UART GPS/Biometric Receiver' }
];

// Returns beautiful mock startup messages
export function generateMockDeviceBoot(port: string, baudrate: number): string[] {
  if (port.includes('COM9') || port.includes('Sensor')) {
    return [
      `[MOCK MODBUS DEVICE DETECTED] Baudrate: ${baudrate}bps`,
      `[INFO] Initializing Modbus RTU protocol engine...`,
      `[INFO] Handshake complete. Listening on address 0x01.`,
      `[RX] 01 03 04 01 E2 02 A8 B9 FA  (Temp: 24.1°C, Humidity: 68.0%)`
    ];
  }
  if (port.includes('COM5') || port.includes('Arduino')) {
    return [
      `Initializing Arduino Nano Board...`,
      `[INFO] CPU: ATmega328P micro-controller operating at 16MHz`,
      `[INFO] SRAM buffer size: 2048 Bytes`,
      `Analog sensors calibrated successfully. Starting loop().`,
      `[RX] SENSOR_A: 512, SENSOR_B: 88, STATUS: SECURE`,
      `[RX] SENSOR_A: 510, SENSOR_B: 92, STATUS: SECURE`
    ];
  }
  
  // ESP32 default template
  return [
    `rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)`,
    `configsip: 0, SPIWP:0xee`,
    `clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00`,
    `mode:DIO, clock div:1`,
    `load:0x3fff0018,len:4`,
    `load:0x3fff001c,len:1044`,
    `ho 0 tail 12 room 4`,
    `load:0x40078000,len:8896`,
    `load:0x40080400,len:5816`,
    `entry 0x400806ec`,
    `[UART] Serial speed synced at ${baudrate} bps.`,
    `[WIFI] Initializing Station Mode...`,
    `[WIFI] Connected to AP. Local IP assigned: 192.168.1.134`,
    `[WIFI] Network Socket listening on port 80 [HTTPD]`,
    `esp32_device_ready>`
  ];
}

// Simple Auto Baud Scorer logic (scores highest when text contains common ASCII or command prompts)
export function countGoodAsciiRatio(bytes: Uint8Array): number {
  if (bytes.length === 0) return 0;
  let goodChars = 0;
  for (let i = 0; i < bytes.length; i++) {
    const x = bytes[i];
    // Printable ASCII, line feeds, carriage return, tabs
    if ((x >= 32 && x <= 126) || x === 10 || x === 13 || x === 9) {
      goodChars++;
    }
  }
  return Math.round((goodChars / bytes.length) * 100);
}

// Generate premium mock quick commands match Python defaults
export function getDefaultQuickCommands(): QuickProject[] {
  return [
    {
      id: 'project_1',
      name: 'ESP32 Control',
      groups: [
        {
          id: 'group_esp_sys',
          name: 'Core Commands',
          commands: [
            { id: 'esp_1', name: 'Check System Status', content: 'AT+STATUS', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_2', name: 'Get Core Version', content: 'AT+GMR', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_3', name: 'Ping Connection', content: 'AT', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_4', name: 'Reset Chip', content: 'AT+RST', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_5', name: 'Wifi RSSI', content: 'AT+CWJAP?', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' }
          ]
        },
        {
          id: 'group_esp_net',
          name: 'Network Commands',
          commands: [
            { id: 'esp_6', name: 'List APs', content: 'AT+CWLAP', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_7', name: 'Get IP Address', content: 'AT+CIFSR', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' },
            { id: 'esp_8', name: 'Close Connection', content: 'AT+CIPCLOSE', send_type: 'text', line_ending: '\r\n', encoding: 'utf-8' }
          ]
        }
      ]
    },
    {
      id: 'project_2',
      name: 'Modbus RTU Sensors',
      groups: [
        {
          id: 'group_mod_sens1',
          name: 'Temperature Sensor',
          commands: [
            { id: 'mod_1', name: 'Read Registers (0-2)', content: '01 03 00 00 00 02 C4 0B', send_type: 'hex', line_ending: '', encoding: 'utf-8' },
            { id: 'mod_2', name: 'Read Device ID', content: '01 11 C0 2C', send_type: 'hex', line_ending: '', encoding: 'utf-8' },
            { id: 'mod_3', name: 'Query Status Register', content: '01 04 00 00 00 01 31 CA', send_type: 'hex', line_ending: '', encoding: 'utf-8' }
          ]
        }
      ]
    }
  ];
}

// Predefined responsive scripts sequence matching python config file loaders
export function getDefaultScripts(): Script[] {
  return [
    {
      id: "script_wifi_burn",
      name: "ESP32 WiFi Handshake Suite",
      loop: false,
      loop_count: 1,
      steps: [
        { cmd: "AT", priority: 1, wait_ms: 500, wait_keyword: "OK", wait_timeout_ms: 2000 },
        { cmd: "AT+GMR", priority: 2, wait_ms: 1000, wait_keyword: "SDK version", wait_timeout_ms: 3000 },
        { cmd: "AT+CWMODE=1", priority: 3, wait_ms: 1200, wait_keyword: "OK", wait_timeout_ms: 2000 },
        { cmd: "AT+CWLAP", priority: 4, wait_ms: 3000, wait_keyword: "esp32_device_ready", wait_timeout_ms: 5000 }
      ]
    },
    {
      id: "script_modbus_stress",
      name: "Modbus RTU Sensor Stress-Test",
      loop: true,
      loop_count: 5,
      steps: [
        { cmd: "01 03 00 00 00 02 C4 0B", priority: 1, wait_ms: 600, wait_keyword: "", wait_timeout_ms: 0 },
        { cmd: "01 04 00 00 00 01 31 CA", priority: 2, wait_ms: 600, wait_keyword: "", wait_timeout_ms: 0 }
      ]
    }
  ];
}
