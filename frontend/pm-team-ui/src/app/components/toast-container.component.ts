import { Component, computed, inject } from '@angular/core';
import { NgFor, NgClass } from '@angular/common';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'toast-container',
  standalone: true,
  imports: [NgFor, NgClass],
  styles: [`
  :host { position: fixed; top: 0.75rem; right: 0.75rem; display:flex; flex-direction:column; gap:.5rem; z-index:1000; }
  .toast { min-width:220px; max-width:340px; padding:.55rem .7rem; border-radius:4px; color:#fff; font-size:.8rem; box-shadow:0 2px 6px rgba(0,0,0,.25); display:flex; justify-content:space-between; align-items:center; gap:.5rem; }
  .info { background:#2563eb; }
  .error { background:#dc2626; }
  .warn { background:#d97706; }
  button { background:transparent; color:inherit; border:0; cursor:pointer; font-size:.9rem; }
  `],
  template: `
    <div *ngFor="let t of toasts()" class="toast" [ngClass]="t.level">
      <span>{{ t.text }}</span>
      <button (click)="dismiss(t.id)" aria-label="Dismiss">×</button>
    </div>
  `
})
export class ToastContainerComponent {
  private svc = inject(NotificationService);
  readonly toasts = this.svc.toasts.asReadonly();
  dismiss(id:number){ this.svc.dismiss(id); }
}
