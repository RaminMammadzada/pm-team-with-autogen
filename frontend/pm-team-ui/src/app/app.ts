import { Component, computed, effect, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { NgFor, NgIf } from '@angular/common';

interface ProjectMeta { slug: string; name: string; created_at?: string; description?: string; }
interface RunMeta { run_id: string; created_at?: string; }
interface PlanTask { id: string; title: string; type?: string; priority?: string; wsjf_score?: number; risk_exposure?: number; status?: string; }
interface PlanArtifact { tasks?: PlanTask[]; [k: string]: any }

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HttpClientModule, NgFor, NgIf],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  // Basic app signals
  protected readonly title = signal('PM Team Dashboard');
  private readonly http = inject(HttpClient);

  // API base (allow override via window or env baked at build time later)
  protected readonly apiBase = signal((window as any).__PM_TEAM_API__ || 'http://localhost:8000');

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
    this.http.get<ProjectMeta[]>(`${this.apiBase()}/projects`).subscribe({
      next: (data) => {
        this.projects.set(data);
        if (!this.selectedProject() && data.length) {
          this.selectProject(data[0]);
        }
      },
      error: (err) => console.error('Failed to load projects', err),
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
    this.http.get<any[]>(`${this.apiBase()}/projects/${proj.slug}/runs`).subscribe({
      next: (data) => {
        // Expect list of run manifests with run_id
        this.runs.set(data.map(r => ({ run_id: r.run_id, created_at: r.created_at })));
        if (!this.selectedRun() && data.length) {
          this.selectRun(this.runs()[0]);
        }
      },
      error: (err) => console.error('Failed to load runs', err),
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
    this.http.get<PlanArtifact>(`${this.apiBase()}/projects/${proj.slug}/runs/${run.run_id}/artifact/plan.json`).subscribe({
      next: (data) => this.plan.set(data),
      error: (err) => console.error('Failed to load plan', err),
      complete: () => this.loadingPlan.set(false)
    });
  }
}
