import { Component, computed, inject, signal, ViewChild, ElementRef, effect } from '@angular/core';
import { NgFor, NgIf, DatePipe, KeyValuePipe } from '@angular/common';
import { ToastContainerComponent } from './components/toast-container.component';
import {
  DataService,
  ProjectMeta,
  RunMeta,
  PlanArtifact,
  ChatMessage,
} from './services/data.service';
import { NotificationService } from './services/notification.service';

@Component({
  selector: 'app-root',
  imports: [NgFor, NgIf, DatePipe, KeyValuePipe, ToastContainerComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  // Basic app signals
  protected readonly title = signal('PM Team Dashboard');
  private readonly data = inject(DataService);
  private readonly notify = inject(NotificationService);

  // Data signals
  protected readonly loadingProjects = signal(false);
  protected readonly projects = signal<ProjectMeta[]>([]);
  protected readonly selectedProject = signal<ProjectMeta | null>(null);

  protected readonly loadingRuns = signal(false);
  protected readonly runs = signal<RunMeta[]>([]);
  protected readonly selectedRun = signal<RunMeta | null>(null);

  protected readonly loadingPlan = signal(false);
  protected readonly plan = signal<PlanArtifact | null>(null);
  protected readonly planTasks = computed(() => this.plan()?.tasks || []);
  protected readonly planSummary = computed(() => {
    const tasks = this.planTasks();
    if (!tasks.length) return null;
    const total = tasks.length;
    const risks = tasks
      .map((t) => (t as any).risk_exposure)
      .filter((v: any) => typeof v === 'number');
    const avgRisk = risks.length
      ? risks.reduce((a: number, b: number) => a + b, 0) / risks.length
      : null;
    const types = new Set(tasks.map((t) => (t as any).type).filter(Boolean));
    const priorities = tasks.map((t) => (t as any).priority).filter(Boolean);
    const highPrio = priorities.filter((p) => /high/i.test(p)).length;
    return { total, avgRisk, types: types.size, highPrio };
  });

  // Chat state
  protected readonly chatMessages = signal<ChatMessage[]>([]);
  protected readonly chatLoading = signal(false);
  protected readonly chatSending = signal(false);
  protected readonly chatInput = signal('');
  protected readonly chatMode = signal<string | null>(null);
  protected readonly blockerInput = signal('');
  protected readonly reorderInput = signal('');
  protected readonly systemUpdates = signal<string[]>([]);
  protected readonly diffOldRun = signal<string | null>(null);
  protected readonly diffNewRun = signal<string | null>(null);
  protected readonly diffLoading = signal(false);
  protected readonly planDiff = signal<any | null>(null);

  // Chat container ref for auto-scrolling
  @ViewChild('chatContainer') private chatContainer?: ElementRef<HTMLDivElement>;

  // Project creation UX state
  protected readonly creatingProject = signal(false);
  protected readonly newProjectName = signal('');
  protected readonly newProjectSlug = computed(
    () =>
      this.newProjectName()
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_\- ]+/g, '')
        .replace(/\s+/g, '_') || '',
  );
  protected readonly tagInput = signal('');
  protected readonly tagChips = computed(() =>
    this.tagInput()
      .split(',')
      .map((t) => t.trim())
      .filter((t, i, arr) => t && arr.indexOf(t) === i),
  );

  constructor() {
    this.fetchProjects();
    // Auto-scroll effect when chat messages change
    effect(() => {
      // Depend on messages length & sending state
      const _len = this.chatMessages().length;
      const _sending = this.chatSending();
      // Defer to next microtask so DOM has rendered new messages
      queueMicrotask(() => this.scrollChatToBottom());
    });
  }

  protected createProject(ev: Event) {
    ev.preventDefault();
    const form = ev.target as HTMLFormElement;
    const fd = new FormData(form);
    const name = (fd.get('name') || '').toString().trim();
    if (!name) {
      this.notify.warn('Name is required');
      return;
    }
    if (this.creatingProject()) return; // guard
    const tagsRaw = (fd.get('tags') || '').toString().trim();
    const tags = tagsRaw
      ? tagsRaw
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
      : undefined;
    this.creatingProject.set(true);
    this.data
      .createProject({
        name,
        description: opt(fd.get('description')),
        domain: opt(fd.get('domain')),
        owner: opt(fd.get('owner')),
        priority: opt(fd.get('priority')),
        tags,
      })
      .subscribe({
        next: (proj) => {
          this.notify.info('Project created');
          form.reset();
          this.newProjectName.set('');
          this.tagInput.set('');
          this.fetchProjects();
          // select the newly created project
          setTimeout(() => {
            const found = this.projects().find((p) => p.slug === (proj as any).slug);
            if (found) this.selectProject(found);
            // Collapse details element if open
            const details = form.closest('details');
            if (details) (details as HTMLDetailsElement).open = false;
          }, 300);
        },
        error: () => this.notify.error('Cannot create project'),
        complete: () => this.creatingProject.set(false),
      });

    function opt(v: FormDataEntryValue | null): string | undefined {
      if (v == null) return undefined;
      const s = v.toString().trim();
      return s ? s : undefined;
    }
  }

  // Live update handlers (bound in template)
  protected onNameInput(value: string) {
    this.newProjectName.set(value);
  }
  protected onTagsInput(value: string) {
    this.tagInput.set(value);
  }

  protected fetchProjects() {
    this.loadingProjects.set(true);
    this.data.projects().subscribe({
      next: (data) => {
        this.projects.set(data);
        if (!this.selectedProject() && data.length) this.selectProject(data[0]);
      },
      error: () => this.notify.error('Cannot load projects'),
      complete: () => this.loadingProjects.set(false),
    });
  }

  protected selectProject(p: ProjectMeta) {
    this.selectedProject.set(p);
    this.selectedRun.set(null);
    this.plan.set(null);
    this.fetchRuns();
  }

  protected fetchRuns() {
    const proj = this.selectedProject();
    if (!proj) return;
    this.loadingRuns.set(true);
    this.data.runs(proj.slug).subscribe({
      next: (data) => {
        this.runs.set(
          data.map((r) => ({ run_id: (r as any).run_id, created_at: (r as any).created_at })),
        );
        if (!this.selectedRun() && data.length) this.selectRun(this.runs()[0]);
      },
      error: () => this.notify.error('Cannot load runs'),
      complete: () => this.loadingRuns.set(false),
    });
  }

  protected runLabel(r: RunMeta): string {
    const raw = r.run_id;
    const idx = raw.indexOf('_');
    if (idx === -1) return raw;
    const rest = raw.substring(idx + 1).replace(/_/g, ' ');
    return rest.length > 50 ? rest.slice(0, 47) + '…' : rest;
  }

  protected fmt(n: any): string {
    if (n == null || n === '') return '–';
    if (typeof n === 'number') return Number.isInteger(n) ? n.toString() : n.toFixed(2);
    return n;
  }

  protected selectRun(r: RunMeta) {
    this.selectedRun.set(r);
    this.plan.set(null);
    this.chatMessages.set([]);
    this.fetchPlan();
    this.loadChat();
  }

  protected fetchPlan() {
    const proj = this.selectedProject();
    const run = this.selectedRun();
    if (!proj || !run) return;
    this.loadingPlan.set(true);
    this.data.plan(proj.slug, run.run_id).subscribe({
      next: (data) => this.plan.set(data),
      error: () => this.notify.error('Cannot load plan'),
      complete: () => this.loadingPlan.set(false),
    });
  }

  protected createRun(ev: Event) {
    ev.preventDefault();
    const proj = this.selectedProject();
    if (!proj) return;
    const form = ev.target as HTMLFormElement;
    const fd = new FormData(form);
    const initiative = (fd.get('initiative') || '').toString().trim() || 'New initiative';
    this.notify.info('Generating run…');
    this.data.createRun(proj.slug, { initiative }).subscribe({
      next: (r) => {
        this.notify.info('Run created');
        form.reset();
        this.fetchRuns();
        setTimeout(() => {
          const found = this.runs().find((x) => x.run_id === r.run_id);
          if (found) this.selectRun(found);
        }, 400);
      },
      error: () => this.notify.error('Cannot create run'),
    });
  }

  protected loadChat() {
    const proj = this.selectedProject();
    const run = this.selectedRun();
    if (!proj || !run) return;
    this.chatLoading.set(true);
    this.data.getChat(proj.slug, run.run_id).subscribe({
      next: (resp) => this.chatMessages.set(resp.messages || []),
      error: () => this.notify.error('Cannot load chat'),
      complete: () => this.chatLoading.set(false),
    });
  }

  protected sendChat(ev: Event) {
    ev.preventDefault();
    if (this.chatSending()) return;
    const text = this.chatInput().trim();
    const mode = this.chatMode();
    const blocker = this.blockerInput().trim();
    const orderRaw = this.reorderInput().trim();
    if (!text && !mode) return;
    const proj = this.selectedProject();
    const run = this.selectedRun();
    if (!proj || !run) return;
    // Optimistic append user message
    const optimistic: ChatMessage = {
      sender: 'user',
      content: text || `(mode: ${mode})`,
      timestamp: new Date().toISOString(),
    };
    this.chatMessages.set([...this.chatMessages(), optimistic]);
    this.chatSending.set(true);
    this.chatInput.set('');
    const opts: any = {};
    if (mode) opts.mode = mode;
    if (mode === 'add_blocker' && blocker) opts.blocker = blocker;
    if (mode === 'reprioritize' && orderRaw) opts.order = orderRaw.split(/[,\s]+/).filter(Boolean);
    this.data.sendChat(proj.slug, run.run_id, text).subscribe({
      next: (resp) => {
        if (resp.messages) this.chatMessages.set(resp.messages);
        if (resp.system_updates) this.systemUpdates.set(resp.system_updates);
      },
      error: () => {
        this.notify.error('Chat send failed');
        // Roll back optimistic on failure
        this.chatMessages.set(this.chatMessages().filter((m) => m !== optimistic));
      },
      complete: () => this.chatSending.set(false),
    });
  }

  protected roleClass(m: ChatMessage): string {
    return m.sender === 'user' ? 'msg user' : 'msg agent';
  }

  protected setMode(mode: string | null) {
    this.chatMode.set(mode);
  }

  protected clearMode() {
    this.chatMode.set(null);
    this.blockerInput.set('');
    this.reorderInput.set('');
  }

  protected computeDiff(ev: Event) {
    ev.preventDefault();
    const proj = this.selectedProject();
    if (!proj || !this.diffOldRun() || !this.diffNewRun()) return;
    if (this.diffOldRun() === this.diffNewRun()) {
      this.notify.warn('Select two different runs');
      return;
    }
    this.diffLoading.set(true);
    this.planDiff.set(null);
    this.data.planDiff(proj.slug, this.diffOldRun()!, this.diffNewRun()!).subscribe({
      next: (d) => this.planDiff.set(d),
      error: () => this.notify.error('Cannot load diff'),
      complete: () => this.diffLoading.set(false),
    });
  }

  private scrollChatToBottom() {
    const el = this.chatContainer?.nativeElement;
    if (!el) return;
    try {
      el.scrollTop = el.scrollHeight;
    } catch (_) {
      /* noop */
    }
  }
}
