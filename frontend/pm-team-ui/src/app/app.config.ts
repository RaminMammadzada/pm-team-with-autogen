import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZoneChangeDetection,
} from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { FRONTEND_ENV, defaultFrontendEnv } from './env.token';
import { NotificationService } from './services/notification.service';

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, tap } from 'rxjs/operators';
import { throwError } from 'rxjs';
const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const notifier = inject(NotificationService);
  return next(req).pipe(
    tap({ error: () => {} }),
    catchError((err: any) => {
      notifier.error(`HTTP ${err.status || 0}: ${req.method} ${req.url}`);
      return throwError(() => err);
    }),
  );
};
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([errorInterceptor])),
    { provide: FRONTEND_ENV, useFactory: defaultFrontendEnv },
  ],
};
