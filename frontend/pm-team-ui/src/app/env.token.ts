import { InjectionToken } from '@angular/core';

export interface FrontendEnv {
  apiBase: string;
}

export const FRONTEND_ENV = new InjectionToken<FrontendEnv>('FRONTEND_ENV');

export function defaultFrontendEnv(): FrontendEnv {
  const win: any = window as any;
  return {
    apiBase: win.__PM_TEAM_API__ || 'http://localhost:8000'
  };
}
