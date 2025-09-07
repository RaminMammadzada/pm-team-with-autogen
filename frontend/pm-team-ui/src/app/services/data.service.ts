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

export interface ChatMessage {
  sender: string;
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  messages: ChatMessage[];
  reply?: ChatMessage;
  system_updates?: string[];
}

export interface PlanDiff {
  added: any[];
  removed: any[];
  modified: { id: string; changes: Record<string, { old: any; new: any }> }[];
  aggregate_risk_old?: number;
  aggregate_risk_new?: number;
  aggregate_risk_delta?: number;
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

  getChat(slug: string, runId: string): Observable<ChatResponse> {
    return this.http.get<ChatResponse>(`${this.env.apiBase}/projects/${slug}/runs/${runId}/chat`);
  }

  sendChat(
    slug: string,
    runId: string,
    message: string,
    opts?: { mode?: string; blocker?: string; order?: string[]; statuses?: Record<string, string> },
  ): Observable<ChatResponse> {
    const body: any = { message };
    if (opts?.mode) body.mode = opts.mode;
    if (opts?.blocker) body.blocker = opts.blocker;
    if (opts?.order) body.order = opts.order;
    if (opts?.statuses) body.statuses = opts.statuses;
    return this.http.post<ChatResponse>(
      `${this.env.apiBase}/projects/${slug}/runs/${runId}/chat`,
      body,
    );
  }

  planDiff(slug: string, oldRun: string, newRun: string) {
    return this.http.get<PlanDiff>(`${this.env.apiBase}/projects/${slug}/plan-diff`, {
      params: { old_run: oldRun, new_run: newRun },
    });
  }
}
