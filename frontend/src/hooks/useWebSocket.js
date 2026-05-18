import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(onMessage) {
  const ws = useRef(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(() => {
    const url = `ws://${window.location.hostname}:8000/ws`
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessageRef.current(data)
      } catch (e) {
        console.error('WS parse error', e)
      }
    }

    ws.current.onclose = () => {
      console.log('WebSocket disconnected — reconnecting in 3s')
      setTimeout(connect, 3000)
    }

    ws.current.onerror = (err) => {
      console.error('WebSocket error', err)
      ws.current.close()
    }
  }, [])

  useEffect(() => {
    connect()
    const ping = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send('ping')
      }
    }, 25000)
    return () => {
      clearInterval(ping)
      ws.current?.close()
    }
  }, [connect])
}
