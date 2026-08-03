

# Agentic Local Brain

[English](README.md) | [简体中文](README.zh-CN.md)

> Sistema de gestión de conocimiento personal: recopila, procesa y consulta conocimiento de múltiples fuentes.

## Inicio Rápido

**Opción 1: Instalar a través del Agente de Escritorio**

En tu agente de escritorio (OpenClaw / Hermes / Claude / Qoder / Codex / Trae, etc.), simplemente envía el siguiente mensaje para comenzar a construir tu cerebro local:

```
Please install or update this knowledge collection skill: http://localbrain.oss-cn-shanghai.aliyuncs.com/skills/localbrain-collect/SKILL.md
```

Eso es todo, tu agente se encargará del resto.

**Opción 2: Instalar a través de la CLI**

Si estás usando un agente basado en CLI, puedes instalar la habilidad directamente:

```bash
npx skills add agent-creativity/agentic-local-brain
```

## Características

- **Recopilación Multi-fuente**: Archivos (PDF, Markdown, texto), páginas web, marcadores, artículos académicos, correos electrónicos y notas
- **Extracción Inteligente**: Extracción de etiquetas y resúmenes en 3 niveles (proporcionado por el usuario → LLM → fallback integrado)
- **Búsqueda Inteligente**: Búsqueda semántica, por palabras clave, preguntas y respuestas basadas en RAG, con degradación elegante
- **Interfaz Dual**: CLI (`localbrain`) y API REST (FastAPI)
- **Servidor Web en Segundo Plano**: Ejecuta la interfaz web como un proceso daemon
- **Degradación Elegante**: Funciona sin servicios de LLM/embeddings utilizando algoritmos de fallback integrados
- **Multiplataforma**: Opciones de instalación flexibles — paquete Python (recomendado, sin advertencias de seguridad), binario independiente (sin Python requerido) o instalación desde código fuente
- **Minería de Conocimiento** (v0.6): Construcción automática de gráficos de conocimiento, descubrimiento de relaciones entre documentos, agrupación de temas y análisis de tendencias, recomendaciones inteligentes basadas en patrones de lectura
- **Recuperación Mejorada** (v0.7): Chat RAG multimensaje con expansión de consultas, recuperación híbrida (fusión de palabras clave + semántica vía RRF), reranking con LLM, enriquecimiento de contexto con gráficos de conocimiento, plantillas de prompt configurables y gestión del historial de conversaciones
- **Wiki LLM** (v0.7): Generación automática de artículos wiki a partir de clústeres de temas usando síntesis LLM, con tarjetas de resumen de entidades, referencias cruzadas wiki-link (`[[entity-slug]]`), seguimiento de obsolescencia y recompilación automática
- **Respaldo de la Base de Conocimiento** (v0.8): Respaldo automatizado con múltiples opciones de almacenamiento (local, Alibaba Cloud OSS, AWS S3), respaldos programados con expresiones cron, políticas de retención y restauración con un clic

<img width="3248" height="1674" alt="image" src="https://github.com/user-attachments/assets/ed6f3cb2-2acc-43ef-8791-f60aab420c7a" />


## Instalación

### Opción 1: Instalación del Paquete Python (Recomendada)

Funciona en todas las plataformas sin advertencias de seguridad. Requiere Python 3.8+.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/python_installer/install.ps1 | iex
```

El instalador:
- Verificará que Python 3.8+ esté instalado
- Creará un entorno virtual en `~/.localbrain/venv`
- Descargará e instalará el paquete wheel
- Agregará `localbrain` a tu PATH

### Opción 2: Instalación Binaria (Sin Python Requerido)

Para sistemas sin Python. Binario independiente sin dependencias.

**macOS / Linux:**
```bash
curl -fsSL http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.sh | sh
```

**Windows (PowerShell):**
```powershell
irm http://localbrain.oss-cn-shanghai.aliyuncs.com/binary_installer/install.ps1 | iex
```

**Nota para macOS:** El binario requiere omitir Gatekeeper:
```bash
xattr -cr ~/.localbrain/bin/localbrain
```

### Opción 3: Instalación desde Código Fuente

Para desarrollo o compilaciones personalizadas:

```bash
# Clone the repository
git clone <repository-url>
cd agentic-local-brain

# Install in development mode
pip install -e .

# Verify installation
localbrain --version
```

### Post-Instalación

Después de la instalación, verifica e inicializa:

```bash
# Check installation
localbrain doctor

# Initialize knowledge base
localbrain init setup
```

### Comandos de Mantenimiento de la CLI

| Comando | Descripción |
|---------|-------------|
| `localbrain --version` | Mostrar versión instalada |
| `localbrain doctor` | Ejecutar diagnósticos del sistema y verificar configuración |
| `localbrain self-update` | Actualizar a la última versión |
| `localbrain self-update --check` | Verificar actualizaciones sin instalar |
| `localbrain self-update --rollback` | Revertir a la versión anterior |
| `localbrain uninstall` | Eliminar LocalBrain (conserva los datos) |

## Ejemplos de Uso

```bash
# Inicializar base de conocimiento
localbrain init

# Recopilar conocimiento
localbrain collect file add ~/documents/paper.pdf
localbrain collect webpage add https://example.com/article
localbrain collect paper add arxiv:2401.12345
localbrain collect email add ~/emails/message.eml
localbrain collect bookmark add https://example.com --tags "reference"
localbrain collect bookmark import --browser chrome
localbrain collect note add "Important insight about ML" --tags "ml" --summary "ML insight note"

# Buscar
localbrain search semantic "machine learning"
localbrain search keyword "python"
localbrain search rag "What is deep learning?"

# Gestionar etiquetas
localbrain tag list
localbrain tag merge "ml" "machine-learning"

# Iniciar interfaz web
localbrain web
localbrain web -b          # modo en segundo plano
localbrain web --status    # verificar estado
localbrain web --stop      # detener servidor en segundo plano
```

## Referencia de Comandos de la CLI

La CLI utiliza un patrón **objeto primero (sustantivo-verbo)** para mantener la consistencia. El comando principal es `localbrain` (`kb` está disponible como un alias compatible con versiones anteriores).

### Comandos de Recopilación

Todos los comandos de recopilación admiten:
- `--tags, -t` — Proporcionar etiquetas manualmente (múltiples permitidas)
- `--summary, -s` — Proporcionar un resumen manualmente
- `--auto-extract / --no-auto-extract` — Extraer automáticamente etiquetas y resumen (predeterminado: habilitado)
- `--skip-existing` — Omitir si el documento ya fue recopilado

| Comando | Descripción |
|---------|-------------|
| `localbrain collect file add <path>` | Agregar archivo local (PDF, Markdown, texto) |
| `localbrain collect webpage add <url>` | Agregar página web |
| `localbrain collect paper add <source>` | Agregar artículo académico (arxiv:ID o URL) |
| `localbrain collect email add <path>` | Agregar correo electrónico (.eml o .mbox) |
| `localbrain collect bookmark add <url>` | Agregar un solo marcador |
| `localbrain collect bookmark import --browser <type>` | Importar marcadores desde el navegador |
| `localbrain collect bookmark import --file <html_file>` | Importar marcadores desde exportación HTML |
| `localbrain collect note add <text>` | Crear una nota de conocimiento |

### Comandos de Búsqueda

Todas las operaciones de búsqueda se unifican bajo el grupo `search`:

| Comando | Descripción |
|---------|-------------|
| `localbrain search semantic <query>` | Búsqueda semántica basada en vectores |
| `localbrain search keyword <keywords>` | Búsqueda por palabras clave basada en texto |
| `localbrain search rag <question>` | Pregunta y respuesta basada en RAG con respuesta generada por IA |
| `localbrain search tags -t <tag>` | Buscar elementos por etiquetas |

### Comandos de Gestión

| Comando | Descripción |
|---------|-------------|
| `localbrain init` | Inicializar base de conocimiento y configuración |
| `localbrain config show` | Mostrar configuración actual |
| `localbrain stats` | Mostrar estadísticas de la base de conocimiento |
| `localbrain tag list` | Listar todas las etiquetas |
| `localbrain tag merge <source> <target>` | Fusionar dos etiquetas |
| `localbrain tag delete <name>` | Eliminar una etiqueta |
| `localbrain export` | Exportar base de conocimiento (markdown o JSON) |
| `localbrain test embedding` | Probar conectividad del servicio de embeddings |
| `localbrain test llm` | Probar conectividad del servicio LLM |
| `localbrain mine run` | Ejecutar minería de conocimiento por lotes (gráfico, relaciones, temas, recomendaciones) |
| `localbrain graph rebuild` | Reconstruir gráfico de conocimiento |
| `localbrain graph stats` | Mostrar estadísticas del gráfico de conocimiento |
| `localbrain topics rebuild` | Reconstruir clústeres de temas |
| `localbrain topics list` | Listar todos los clústeres de temas |
| `localbrain web` | Iniciar interfaz web (admite -b para segundo plano) |
| `localbrain doctor` | Ejecutar diagnósticos del sistema |
| `localbrain self-update` | Actualizar a la última versión |
| `localbrain self-update --check` | Verificar actualizaciones |
| `localbrain backup create` | Crear respaldo manual |
| `localbrain backup list` | Listar todos los respaldos |
| `localbrain backup restore <filename>` | Restaurar desde respaldo |
| `localbrain backup delete <filename>` | Eliminar un respaldo |
| `localbrain uninstall` | Eliminar LocalBrain (conserva los datos) |

## Respaldo de la Base de Conocimiento (v0.8)

Protege tu base de conocimiento con respaldos automatizados en almacenamiento local o proveedores en la nube:

**Opciones de Almacenamiento:**
- **Local** — Almacenar respaldos en `~/.localbrain/backups/`
- **Alibaba Cloud OSS** — Subir a bucket OSS con gestión automática de ciclo de vida
- **AWS S3** — Subir a bucket S3 con soporte para versiones

**Características:**
- Respaldos automáticos programados (expresiones cron)
- Políticas de retención configurables (eliminación automática de respaldos antiguos)
- Restauración con un clic desde cualquier respaldo
- Ejecución de tareas en segundo plano con seguimiento de progreso
- Interfaz web para gestión de respaldos y configuración de almacenamiento en la nube

**Comandos de la CLI:**
```bash
# Crear respaldo manual
localbrain backup create                    # almacenamiento local (predeterminado)
localbrain backup create --cloud oss        # subir a OSS
localbrain backup create --cloud s3         # subir a S3

# Listar respaldos
localbrain backup list                      # respaldos locales
localbrain backup list --cloud oss          # respaldos OSS
localbrain backup list --cloud s3           # respaldos S3

# Restaurar desde respaldo
localbrain backup restore backup-20260420-120000.tar.gz
localbrain backup restore backup-20260420-120000.tar.gz --cloud oss

# Eliminar respaldo
localbrain backup delete backup-20260420-120000.tar.gz
localbrain backup delete backup-20260420-120000.tar.gz --cloud oss
```

**Configuración de la Interfaz Web:**

Configura los ajustes de respaldo en la interfaz web (Ajustes → Respaldo):
1. Habilitar/deshabilitar respaldos automáticos
2. Establecer programa de respaldo (expresión cron, ej., `0 2 * * *` para diariamente a las 2 AM)
3. Configurar política de retención (días para conservar respaldos)
4. Elegir ubicación de almacenamiento (local, OSS o S3)
5. Configurar credenciales de almacenamiento en la nube (endpoint, claves de acceso, bucket)

**Ejemplo de Configuración:**
```yaml
backup:
  enabled: true
  schedule: "0 2 * * *"        # Diariamente a las 2 AM
  retention_days: 30            # Conservar respaldos por 30 días
  storage_location: oss         # local, oss o s3
  
  # Alibaba Cloud OSS
  oss:
    endpoint: oss-cn-shanghai.aliyuncs.com
    access_key_id: ${OSS_ACCESS_KEY_ID}
    access_key_secret: ${OSS_ACCESS_KEY_SECRET}
    bucket: my-localbrain-backups
  
  # AWS S3
  s3:
    region: us-west-2
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
    bucket: my-localbrain-backups
```

## Extracción Inteligente

Al recopilar documentos, las etiquetas y los resúmenes se extraen automáticamente utilizando una **estrategia de fallback en 3 niveles**:

```
┌─────────────────────────────────────────────────────┐
│ Nivel 1: Proporcionado por el Usuario (prioridad máx)│
│   --tags "ai,ml" --summary "About ML"               │
│   → Se usa directamente, se omite la extracción     │
├─────────────────────────────────────────────────────┤
│ Nivel 2: Extracción LLM (DashScope / OpenAI)        │
│   Extrae 3-5 etiquetas + resumen de 1-2 frases      │
│   vía LLM configurable (qwen-plus, qwen-max, etc.)  │
├─────────────────────────────────────────────────────┤
│ Nivel 3: Extracción Integrada (siempre disponible)   │
│   Etiquetas: Puntuación TF-IDF con boost de título   │
│   Resumen: Extractivo (selecciona mejores frases)    │
│   Sin dependencias de IA, funciona sin conexión      │
└─────────────────────────────────────────────────────┘
```

Deshabilita la extracción automática con `--no-auto-extract`:
```bash
localbrain collect file add paper.pdf --no-auto-extract
```

## Degradación Elegante

El sistema sigue funcionando cuando los servicios de LLM o embeddings están indisponibles:

| Escenario | Impacto | Fallback |
|----------|--------|----------|
| Embedding indisponible | Búsqueda semántica deshabilitada | Recurre a búsqueda por palabras clave |
| LLM indisponible | Generación de respuestas RAG deshabilitada | Devuelve resultados de búsqueda sin respuesta de IA |
| LLM indisponible | Etiquetado automático degradado | Usa extracción integrada TF-IDF |
| Ambos indisponibles | Modo mínimo | Solo búsqueda por palabras clave + extracción integrada |

Los documentos **siempre se guardan** en el sistema de archivos y SQLite, independientemente de la disponibilidad del servicio. Usa `localbrain test embedding` y `localbrain test llm` para verificar la conectividad de los servicios.

## RAG Mejorada (v0.7)

El sistema RAG Mejorado proporciona una tubería de recuperación multietapa para obtener respuestas más precisas y contextuales:

```
Consulta → Expansión de Consulta → Recuperación Híbrida → Reranking LLM → Enriquecimiento de Contexto → Generación de Respuesta
            (reescribir y        (palabras clave +         (puntuación             (entidades + temas)
             expandir)           búsqueda semántica RRF)    de relevancia)
```

**Etapas de la Tubería:**
1. **Expansión de Consulta** — Reescribe y expande las consultas para mejorar la recuperación
2. **Recuperación Híbrida** — Combina búsqueda por palabras clave (FTS5) y semántica con Fusión de Rango Recíproco (RRF)
3. **Reranking LLM** — Usa LLM para puntuar y reordenar resultados por relevancia
4. **Enriquecimiento de Contexto** — Agrega contexto de entidades y temas desde el gráfico de conocimiento
5. **Ensamblaje de Contexto** — Construcción de contexto consciente de tokens dentro del presupuesto
6. **Generación de Respuesta** — LLM sintetiza la respuesta con atribución de fuentes

**Conversación Multimensaje:**
```bash
# CLI: Consulta RAG (monomensaje)
localbrain search rag "What is machine learning?"

# API: Chat multimensaje con gestión de sesiones
POST /api/rag/chat
{
  "query": "Can you elaborate on neural networks?",
  "session_id": "optional-session-id"
}
```

**Plantillas de Prompt Configurables:**
- `general` — Equilibrado para preguntas diarias
- `technical` — Optimizado para código y contenido técnico
- `academic` — Estructurado para temas de investigación
- `creative` — Flexible para exploración creativa

## Wiki LLM (v0.7)

La función Wiki LLM sintetiza el conocimiento recopilado en artículos wiki legibles:

**Qué hace:**
- **Artículos de Tema** — LLM sintetiza documentos de clústeres de temas en artículos de referencia coherentes
- **Tarjetas de Resumen de Entidades** — Resúmenes concisos de entidades que aparecen en múltiples documentos
- **Referencias Cruzadas Wiki-link** — Los artículos enlazan a entidades relacionadas usando la sintaxis `[[entity-slug]]`
- **Seguimiento de Obsolescencia** — Detecta automáticamente cuando los documentos fuente cambian y marca artículos para recompilación

**Comandos de la CLI:**
```bash
# Compilar artículos wiki desde clústeres de temas
localbrain wiki compile                 # compilar solo artículos obsoletos
localbrain wiki compile --force         # recompilar todos los artículos

# Listar artículos compilados
localbrain wiki list                    # vista jerárquica (predeterminado)
localbrain wiki list --flat             # vista de lista plana
localbrain wiki list --type entity      # solo tarjetas de entidad

# Ver artículo
localbrain wiki show <article-slug>     # mostrar contenido del artículo
```

**Interfaz Web:** Explora el wiki a través de la interfaz web en la página Wiki, con navegación jerárquica por tema y categoría.

**Integración con la Tubería de Minería:** La compilación del wiki está integrada como el Paso 5 de `localbrain mine run`. Omítelo con `--skip-wiki` si es necesario.

## API Web

Inicia el servidor web:
```bash
localbrain web                    # primer plano
localbrain web -b                 # segundo plano (daemon)
localbrain web -b -p 9090         # puerto personalizado, segundo plano
localbrain web --stop             # detener servidor en segundo plano
localbrain web --status           # verificar estado del servidor
```

Endpoints de la API (predeterminado: http://localhost:11201):

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Estadísticas de la base de conocimiento |
| GET | `/api/items` | Listar elementos de conocimiento |
| GET | `/api/items/{id}` | Obtener elemento por ID |
| GET | `/api/tags` | Listar todas las etiquetas |
| POST | `/api/search/keyword` | Búsqueda por palabras clave |
| POST | `/api/search/semantic` | Búsqueda semántica |
| POST | `/api/search/rag` | Consulta RAG |
| GET | `/api/graph` | Datos del gráfico de conocimiento |
| GET | `/api/knowledge/{id}/related` | Documentos relacionados |
| GET | `/api/topics` | Clústeres de temas |
| GET | `/api/topics/{id}/documents` | Documentos en tema |
| GET | `/api/topics/trend` | Tendencias de temas |
| GET | `/api/recommendations` | Recomendaciones inteligentes |
| POST | `/api/rag/chat` | RAG mejorada con conversación multimensaje |
| GET | `/api/rag/conversations` | Listar sesiones de conversación |
| GET | `/api/rag/conversations/{session_id}` | Obtener conversación completa |
| DELETE | `/api/rag/conversations/{session_id}` | Eliminar conversación |
| POST | `/api/rag/suggest` | Sugerencias de consulta |
| GET | `/api/dashboard/rag-stats` | Analíticas RAG |
| GET | `/api/wiki/tree` | Árbol de estructura del wiki |
| GET | `/api/wiki/articles` | Listar artículos (parámetros: article_type, limit, offset) |
| GET | `/api/wiki/articles/{article_id}` | Obtener contenido del artículo |
| GET | `/api/wiki/search` | Buscar artículos wiki |
| GET | `/api/wiki/categories/{category_id}/articles` | Artículos por categoría |
| GET | `/api/wiki/topics/{topic_id}/articles` | Artículos por tema |
| GET | `/api/wiki/entities` | Listar tarjetas de entidad |
| GET | `/api/wiki/entities/{entity_id}` | Obtener tarjeta de entidad |
| GET | `/api/wiki/stats` | Estadísticas del wiki |

La documentación de la API está disponible en `http://localhost:11201/docs` cuando el servidor está en ejecución.

Página de Inicio:
<img width="2914" height="1548" alt="image" src="https://github.com/user-attachments/assets/8e1fa67a-28dc-4876-9067-eefcaf0230b5" />

Gráfico de conocimiento:
<img width="2920" height="1544" alt="image" src="https://github.com/user-attachments/assets/4c4a277f-5f2f-4f19-9d04-79581b471981" />


## Configuración

Archivo de configuración: `~/.localbrain/config.yaml`

```yaml
data_dir: ~/.knowledge-base

# URL del servidor de actualización (para la funcionalidad de auto-actualización)
update_server_url: http://localbrain.oss-cn-shanghai.aliyuncs.com

embedding:
  provider: litellm
  model: openai/text-embedding-v4
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  encoding_format: float

llm:
  provider: litellm
  model: dashscope/qwen-plus
  api_key: ${DASHSCOPE_API_KEY}

chunking:
  max_chunk_size: 1000
  chunk_overlap: 100

storage:
  type: chroma
  persist_directory: ~/.knowledge-base/db/chroma

query:
  rag:
    top_k: 5
    temperature: 0.3
    max_tokens: 1000
    context_budget: 4000
    context_format: hierarchical
    reranking:
      enabled: true
      top_n_candidates: 20
      weight_retrieval: 0.4
      weight_rerank: 0.6
    conversation:
      max_turns: 20
      session_timeout_minutes: 30
      history_turns_in_context: 5
    templates:
      default: general
  pipeline:
    top_k: 10
    rerank_top_k: 5
    context_budget: 4000

logging:
  log_dir: ""
  level: INFO
  max_bytes: 10485760
  backup_count: 5
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

wiki:
  enabled: true
  max_source_tokens_per_topic: 8000
  entity_card_threshold: 3
  temperature: 0.3
  model: null
  max_article_words: 3000
  max_subcategories: 5
```

### Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `DASHSCOPE_API_KEY` | Clave API de Alibaba DashScope para embeddings y LLM |
| `OPENAI_API_KEY` | Clave API de OpenAI (si se usa el proveedor OpenAI) |
| `KB_CONFIG_PATH` | Ruta personalizada del archivo de configuración (opcional, predeterminado: `~/.localbrain/config.yaml`) |

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Interfaz de Usuario                   │
│  ┌──────────────┐              ┌─────────────────────┐  │
│  │ CLI (Click)  │              │  API Web (FastAPI)   │  │
│  │ localbrain   │              │  REST + Dashboard    │  │
│  └──────┬───────┘              └──────────┬──────────┘  │
└─────────┼────────────────────────────────┼──────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Módulos Core                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Coletores   │  │  Procesadores │  │     Consulta   │  │
│  │ - Archivo   │  │ - Chunker    │  │ - Semántica    │  │
│  │ - Página Web│  │ - Embedder   │  │ - Palabras Key │  │
│  │ - Marcador  │  │ - TagExtract │  │ - RAG          │  │
│  │ - Artículo  │  │ - BuiltinExt │  │ - Gráfico      │  │
│  │ - Correo    │  │ - EntityExt  │  │ - Temas        │  │
│  │ - Nota      │  │ - TopicClust │  │ - Recomendación│  │
│  │             │  │ - DocRelation│  │                │  │
│  │             │  │ - Recommend  │  │                │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────┘
          │                                │
          ▼                                ▼
┌─────────────────────────────────────────────────────────┐
│                    Capa de Almacenamiento                │
│  ┌─────────────────────┐    ┌─────────────────────────┐ │
│  │   Almacenamiento    │    │    Almacenamiento       │ │
│  │   SQLite            │    │    ChromaDB             │ │
│  │ (Metadatos + Etq.)  │    │  (Embeddings Vectoriales)│ │
│  └─────────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Desarrollo

### Configuración de Desarrollo

```bash
# Clone the repository
git clone <repository-url>
cd agentic-local-brain
```

### Construir Paquete Python Wheel

Construye el paquete wheel de Python para distribución:

```bash
# Construir wheel para la versión actual
python scripts/build_wheel.py --version 0.5.0

# Salida:
# dist/localbrain-0.5.0-py3-none-any.whl
# dist/localbrain-0.5.0-py3-none-any.whl.sha256
```

El wheel puede instalarse con:

```bash
pip install dist/localbrain-0.5.0-py3-none-any.whl
```

### Construir Binarios

Construye binarios independientes para distribución:

```bash
# Construir para la plataforma actual
python scripts/build_binary.py --version 0.5.0

# Construir para una plataforma específica
python scripts/build_binary.py --version 0.5.0 --platform macos-arm64
python scripts/build_binary.py --version 0.5.0 --platform linux-x64
python scripts/build_binary.py --version 0.5.0 --platform win-x64
```

Los binarios construidos se colocan en el directorio `dist/` con checksums SHA256.

### Construir Publicación Completa

Construye el paquete de publicación completo listo para implementar:

```bash
# Construir todo (wheel + binario de plataforma actual)
python scripts/build_release.py --version 0.5.0

# Construir solo Python wheel
python scripts/build_release.py --version 0.5.0 --wheel-only

# Construir solo binario para plataforma específica
python scripts/build_release.py --version 0.5.0 --binary-only --platform macos-arm64
```

### Estructura de la Publicación

El directorio `dist/` está organizado para una implementación sencilla en tu servidor web:

```
dist/
├── version.json                      # Información de versión para verificaciones de actualización
├── python_installer/
│   ├── install.sh                    # Instalador Python macOS/Linux
│   ├── install.ps1                   # Instalador Windows PowerShell
│   └── packages/
│       ├── localbrain-0.5.0-py3-none-any.whl
│       └── localbrain-0.5.0-py3-none-any.whl.sha256
└── binary_installer/
    ├── install.sh                    # Instalador binario macOS/Linux
    ├── install.ps1                   # Instalador binario Windows
    └── releases/
        └── v0.5.0/
            ├── localbrain-macos-arm64
            ├── localbrain-macos-arm64.sha256
            ├── localbrain-macos-x64
            ├── localbrain-linux-arm64
            ├── localbrain-linux-x64
            ├── localbrain-win-x64.exe
            └── ...
```

**Implementación:** Copia todo el directorio `dist/` a tu servidor web. Los instaladores descargan archivos basándose en rutas relativas desde `version.json`.

## Licencia

MIT
