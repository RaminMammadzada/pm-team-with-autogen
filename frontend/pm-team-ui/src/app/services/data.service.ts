import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FRONTEND_ENV } from '../env.token';
import { Observable } from 'rxjs';

export interface ProjectMeta {
  slug: string;
  name: string;
  created_at?: string;
  description?: string;
}
export interface RunMeta {
  run_id: string;
  created_at?: string;
}
export interface PlanTask {
  id: string;
  title: string;
  type?: string;
  priority?: string;
  wsjf_score?: number;
  risk_exposure?: number;
  status?: string;
}
export interface PlanArtifact {
  tasks?: PlanTask[];
  [k: string]: any;
}

@Injectable({ providedIn: 'root' })
export class DataService {
  private http = inject(HttpClient);
  private env = inject(FRONTEND_ENV);

  projects(): Observable<ProjectMeta[]> {
    return this.http.get<ProjectMeta[]>(`${this.env.apiBase}/projects`);
  }

  createProject(body: {
    name: string;
    description?: string | null;
    domain?: string | null;
    owner?: string | null;
    priority?: string | null;
    tags?: string[] | null;
  }): Observable<ProjectMeta> {
    return this.http.post<ProjectMeta>(`${this.env.apiBase}/projects`, body);
  }

  runs(slug: string): Observable<RunMeta[]> {
    return this.http.get<RunMeta[]>(`${this.env.apiBase}/projects/${slug}/runs`);
  }

  plan(slug: string, runId: string): Observable<PlanArtifact> {
    return this.http.get<PlanArtifact>(
      `${this.env.apiBase}/projects/${slug}/runs/${runId}/artifact/plan.json`,
    );
  }

  createRun(
    slug: string,
    body: { initiative: string; blocker?: string; blockers?: string[]; max_runs?: number },
  ): Observable<{ run_id: string; initiative: string }> {
    return this.http.post<{ run_id: string; initiative: string }>(
      `${this.env.apiBase}/projects/${slug}/runs`,
      body,
    );
  }
}
