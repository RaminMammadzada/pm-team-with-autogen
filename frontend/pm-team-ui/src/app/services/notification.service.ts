import { Injectable, signal } from '@angular/core';

export interface ToastMessage { id: number; level: 'info'|'error'|'warn'; text: string; ts: number; }

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private seq = 0;
  readonly toasts = signal<ToastMessage[]>([]);

  push(level: ToastMessage['level'], text: string) {
    const msg: ToastMessage = { id: ++this.seq, level, text, ts: Date.now() };
    this.toasts.update(list => [...list, msg]);
    setTimeout(() => this.dismiss(msg.id), 6000);
  }

  info(t: string) { this.push('info', t); }
  error(t: string) { this.push('error', t); }
  warn(t: string) { this.push('warn', t); }

  dismiss(id: number) { this.toasts.update(list => list.filter(t => t.id !== id)); }
  clear() { this.toasts.set([]); }
}
