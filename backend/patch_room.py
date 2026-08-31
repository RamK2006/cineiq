import re

with open('../frontend/src/app/room/[id]/RoomClient.tsx', 'r') as f:
    content = f.read()

# Add new states
state_addition = """
  const [networkOffset, setNetworkOffset] = useState<number>(0);
  const [hostStatus, setHostStatus] = useState<string>('');
"""

content = re.sub(
    r"(const \[connectionStatus, setConnectionStatus\] = useState<'connecting' \| 'connected' \| 'disconnected'>\('connecting'\);)",
    r"\1" + state_addition,
    content
)

# Update ws onopen to start PING loop
onopen_replacement = """
    ws.current.onopen = () => {
      console.log('Connected to WS');
      setConnectionStatus('connected');
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      
      // Start NTP Clock Sync Loop
      const pingInterval = setInterval(() => {
        if (ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: 'PING', payload: { client_time: Date.now() } }));
        }
      }, 5000);
      
      // Cleanup on close
      const oldOnClose = ws.current.onclose;
      ws.current.onclose = (e) => {
        clearInterval(pingInterval);
        if (oldOnClose) oldOnClose(e);
      };
    };
"""

content = re.sub(
    r"ws\.current\.onopen = \(\) => \{[\s\S]*?if \(reconnectTimeout\.current\) clearTimeout\(reconnectTimeout\.current\);\n    \};",
    onopen_replacement,
    content
)

# Handle new cases in onmessage
onmessage_replacement = """
          case 'PONG':
            if (message.payload) {
              const rtt = Date.now() - message.payload.client_time;
              const serverTime = message.payload.server_time;
              const newOffset = serverTime - (Date.now() - rtt / 2);
              setNetworkOffset(prev => (prev * 0.8) + (newOffset * 0.2)); // Smooth the offset
            }
            break;
          case 'SYNC_TIME':
            if (message.payload) {
                const { server_time, progress: sProgress, action, state_timestamp } = message.payload;
                const now = Date.now();
                const currentServerTime = now + networkOffset;
                
                let expectedProgress = sProgress;
                if (action === 'play') {
                    const elapsed = (currentServerTime - state_timestamp) / 1000;
                    expectedProgress += elapsed;
                    setIsPlaying(true);
                    setHostStatus('Playing');
                } else {
                    setIsPlaying(false);
                    setHostStatus('Paused');
                }
                
                // If drifted by more than 0.3s, seek
                setProgress(prev => {
                    if (Math.abs(prev - expectedProgress) > 0.3) {
                        return expectedProgress;
                    }
                    return prev;
                });
            }
            break;
          case 'HOST_ACTION_DENIED':
            console.warn("Host Action Denied:", message.error);
            break;
"""

content = re.sub(
    r"(switch \(message\.type\) \{)",
    r"\1" + onmessage_replacement,
    content
)

# Request sync function
req_sync = """
  const requestSync = useCallback(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({ type: 'REQUEST_SYNC', payload: {} }));
      }
  }, []);
"""

content = re.sub(
    r"(const emitSync = useCallback)",
    req_sync + r"\n  \1",
    content
)

# Request sync button in UI
ui_replacement = """
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px' }}>00:00 / 02:45:00</span>
          
          <button onClick={requestSync} title="Request Resync" style={{ background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', cursor: 'pointer' }}>
            Sync
          </button>
          
          {hostStatus && (
             <span style={{ fontSize: '12px', color: 'var(--accent-primary)', marginLeft: '8px' }}>
                Host: {hostStatus}
             </span>
          )}
"""

content = re.sub(
    r"<span style=\{\{ fontFamily: 'var\(--font-body\)', fontSize: '14px' \}\}>00:00 / 02:45:00</span>",
    ui_replacement,
    content
)

with open('../frontend/src/app/room/[id]/RoomClient.tsx', 'w') as f:
    f.write(content)
