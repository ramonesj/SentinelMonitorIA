# Informe de validación local

Este informe registra el estado verificable de SentinelMonitorIA después de completar las mejoras locales. No se desplegaron recursos AWS, no se usaron credenciales cloud y no sustituye una validación de infraestructura en una cuenta real.

## Alcance

La validación cubre:

- Backend FastAPI, PostgreSQL, Redis, worker local y endpoints de observabilidad.
- Frontend React/Vite en modo manual y en una imagen Docker autocontenida.
- Compose de desarrollo, override opcional del frontend y perfil `local-production`.
- Dependencias frontend, tests, build, auditoría npm y ejecución como usuario no root.
- Exclusión de archivos `.env` y secretos de los contextos e imágenes Docker.
- Documentación y diseño CloudFormation offline.

## Comandos reproducibles

Ejecutar desde la raíz del repositorio en PowerShell.

### Stack base

```powershell
.\scripts\check-docker.ps1
.\scripts\start-local.ps1 -Build
.\scripts\test-local.ps1
```

El Compose principal publica el backend en `8000`, PostgreSQL en `5432`, Redis en `6379`, Adminer en `8080` y Redis Commander en `8081`. `docker compose down` conserva los volúmenes; no usar `down -v` salvo que se quiera borrar deliberadamente el estado local.

### Frontend manual

```powershell
Push-Location frontend
npm ci
npm test
npm run build
npm audit --audit-level=high
npm run dev
Pop-Location
```

El servidor manual usa `http://localhost:3000` y el backend local `http://localhost:8000`.

### Frontend Docker integrado

El frontend Docker se construye desde la raíz, copia el código y `Imagenes/` a la imagen, instala las dependencias fijadas por `package-lock.json` y se ejecuta como usuario `node`. No monta `frontend/` ni un volumen persistente de `node_modules`; después de cambiar el código o las dependencias se debe reconstruir.

```powershell
# Detener primero cualquier Vite manual que use el puerto 3000
.\scripts\start-local.ps1 -Build -Frontend
.\scripts\test-local.ps1 -RequireFrontend
```

Validación del override sin ocupar el puerto del host:

```powershell
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml build frontend
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml run -T --rm --no-deps frontend npm run build
```

### Backend y Compose

```powershell
docker exec sentinel-backend pytest -q
docker compose -f backend\docker-compose.yml config --quiet
docker compose -f backend\docker-compose.yml -f backend\docker-compose.frontend.yml config --quiet
docker compose --env-file backend\.env.local-production.example -f backend\docker-compose.local-production.yml config --quiet
git diff --check
```

Para el perfil `local-production` real se debe copiar el ejemplo a un archivo local, reemplazar todos los secretos y no versionarlo.

## Resultados verificados

| Comprobación | Resultado |
|---|---|
| Tests frontend | 3 archivos, 9 tests correctos |
| Build frontend local | Vite `8.1.5`, correcto |
| Auditoría frontend | `0 vulnerabilities` |
| Tests backend | 19 correctos, 1 omitido por requerir `QUEUE_PROVIDER=redis` |
| Imagen frontend | Build correcto con Node fijado por digest y Vite `8.1.5` |
| Imagen backend | Build correcto y usuario runtime `sentinel` |
| Usuarios runtime | Frontend `node`; backend `sentinel` |
| Archivos secretos en imágenes | `/app/.env` ausente en frontend y backend |
| Smoke backend | Root, health, liveness, readiness, metrics y telemetry: HTTP 200 |
| Smoke frontend | HTTP 200 en modo manual y en contenedor de validación |
| Compose | Desarrollo, frontend opcional y `local-production` válidos |
| Formato Git | `git diff --check` limpio |

El test omitido no indica un fallo del backend: el stack predeterminado usa `QUEUE_PROVIDER=mock`. Para ejecutarlo se necesita levantar el override Redis/worker y repetir la suite con ese proveedor.

## Seguridad y secretos

- `backend/.env` es local e ignorado por Git; no se debe leer, copiar ni publicar.
- `.dockerignore` raíz y `backend/.dockerignore` excluyen `.env`, `.env.*`, logs, cachés y dependencias locales de los contextos de build.
- Los ejemplos de entorno contienen placeholders o credenciales exclusivamente locales; deben reemplazarse antes de un entorno compartido.
- Las imágenes Docker verificadas ejecutan como usuarios no root.
- No se deben usar `down -v`, `start-local.ps1 -Clean` ni comandos de reset como parte de una validación normal porque eliminan datos locales.

## Limitaciones conocidas

- AWS, CloudFormation contra una cuenta, costes, cuotas, conectividad, DNS, ACM, IAM y despliegues ECS no se validaron.
- `infra/cloudformation/` contiene diseño offline y parámetros de ejemplo, no recursos creados.
- El frontend manual y el frontend Docker no pueden usar simultáneamente el puerto `3000`.
- La suite backend muestra warnings de deprecación de Pydantic y `datetime.utcnow`; no bloquean la validación actual, pero deben atenderse en una futura actualización técnica.
- Las fuentes host/journald/Docker del agente Vector requieren validación adicional en un host Linux real; el flujo E2E aislado para Windows + Docker está documentado en `agent/README.md`.

## Diagnóstico rápido

```powershell
docker compose -f backend\docker-compose.yml ps
docker compose -f backend\docker-compose.yml logs --tail 200 backend postgres redis
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/health
.\scripts\test-local.ps1
```

Si `localhost:3000` devuelve conexión rechazada, iniciar el frontend manual con `npm run dev` o usar el override Docker después de liberar el puerto. Si el frontend Docker ejecuta una versión antigua, reconstruir con `.\scripts\start-local.ps1 -Build -Frontend`; la imagen actual no depende de un volumen persistente de `node_modules`.

## Estado Git de esta fase

La validación se realizó con cambios locales sin commit ni push. Antes de crear un commit, revisar:

```powershell
git status --short
git diff --check
git diff --stat
```
