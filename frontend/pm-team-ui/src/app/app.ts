import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { ToastContainerComponent } from './components/toast-container.component';
import { DataService, ProjectMeta, RunMeta, PlanArtifact } from './services/data.service';
import { NotificationService } from './services/notification.service';

@Component({
  selector: 'app-root',
  imports: [NgFor, NgIf, ToastContainerComponent],
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

  constructor() {
    this.fetchProjects();
  }

  protected fetchProjects() {
    this.loadingProjects.set(true);
    this.data.projects().subscribe({
      next: data => {
        this.projects.set(data);
        if (!this.selectedProject() && data.length) this.selectProject(data[0]);
      },
      error: () => this.notify.error('Cannot load projects'),
      complete: () => this.loadingProjects.set(false)
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
      next: data => {
        this.runs.set(data.map(r => ({ run_id: (r as any).run_id, created_at: (r as any).created_at })));
        if (!this.selectedRun() && data.length) this.selectRun(this.runs()[0]);
      },
      error: () => this.notify.error('Cannot load runs'),
      complete: () => this.loadingRuns.set(false)
    });
  }

  protected selectRun(r: RunMeta) {
    this.selectedRun.set(r);
    this.plan.set(null);
    this.fetchPlan();
  }

  protected fetchPlan() {
    const proj = this.selectedProject();
    const run = this.selectedRun();
    if (!proj || !run) return;
    this.loadingPlan.set(true);
    this.data.plan(proj.slug, run.run_id).subscribe({
      next: data => this.plan.set(data),
      error: () => this.notify.error('Cannot load plan'),
      complete: () => this.loadingPlan.set(false)
    });
  }
}
