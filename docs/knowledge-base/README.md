# Corpus de Knowledge Base

Esta carpeta contiene documentos **redactados y no confidenciales** para la Knowledge Base de Bedrock. La fase `19-ai-platform` publica el bucket S3 privado y limita la fuente de datos al prefijo `knowledge-base/`.

## Qué se puede agregar

- Runbooks operativos sin credenciales.
- Descripciones de arquitectura y componentes.
- Procedimientos de diagnóstico.
- Documentación de reglas, métricas y eventos.
- Archivos Markdown, texto plano, JSON o HTML.

No agregues API keys, access keys, tokens, contraseñas, JWT, URLs con credenciales, secretos de Secrets Manager, dumps de base de datos ni telemetry sin anonimizar. El script excluye nombres de archivos que parecen secretos y escanea los formatos de texto admitidos, pero la revisión humana del contenido sigue siendo obligatoria. Los PDF no se publican automáticamente porque este script no los inspecciona.

## Publicación e ingesta

Desde la raíz del repositorio, después de desplegar la fase 19 y revisar el presupuesto:

```powershell
.\scripts\publish-bedrock-knowledge-base.ps1 -Profile sentinel-monitoria -DryRun
.\scripts\publish-bedrock-knowledge-base.ps1 -Profile sentinel-monitoria
.\scripts\publish-bedrock-knowledge-base.ps1 -Profile sentinel-monitoria -StartIngestion
```

El primer comando sólo muestra los documentos que serían publicados. El segundo carga o actualiza archivos bajo `knowledge-base/` sin iniciar una ingesta; no elimina objetos remotos que ya no existan localmente. El tercero carga los archivos y ejecuta `start-ingestion-job`. Ninguno debe ejecutarse con credenciales reales hasta aprobar el Change Set, los costes y el corpus.

La Knowledge Base usa `amazon.titan-embed-text-v2:0` para embeddings y S3 Vectors como vector store. El AI worker usa `amazon.nova-lite-v1:0` para explicaciones, mantiene `AI_ENABLE_ACTIONS=false` y envía las notificaciones a `log` inicialmente.
