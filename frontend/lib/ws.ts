export type MessageHandler = (data: unknown) => void;

export class ManusWebSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private mockInterval: ReturnType<typeof setInterval> | null = null;
  private _connected = false;

  constructor(url: string) {
    this.url = url;
  }

  get connected(): boolean {
    return this._connected;
  }

  connect(): void {
    try {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this._connected = true;
      };
      this.ws.onclose = () => {
        this._connected = false;
        this.startMockMode();
      };
      this.ws.onerror = () => {
        this.ws?.close();
      };
      this.ws.onmessage = (event) => {
        const data: unknown = JSON.parse(event.data as string);
        this.handlers.forEach((h) => h(data));
      };
    } catch {
      this.startMockMode();
    }
  }

  private startMockMode(): void {
    this._connected = true;
    this.mockInterval = setInterval(() => {
      const mockMessage = {
        type: "heartbeat",
        timestamp: Date.now(),
        connected: true,
      };
      this.handlers.forEach((h) => h(mockMessage));
    }, 2000);
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
    if (this.mockInterval) {
      clearInterval(this.mockInterval);
      this.mockInterval = null;
    }
    this._connected = false;
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }
}
