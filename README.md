# 🎬 FFmpeg Service

Servicio completo de procesamiento de video para el proyecto de videos educativos UNAM/IPN.

## Características

| Operación | Endpoint | Descripción |
|-----------|----------|-------------|
| **Merge** | `/merge` | Combinar video + audio TTS |
| **Concat** | `/concat` | Concatenar múltiples videos |
| **Subtítulos** | `/add-subtitles` | Agregar subtítulos (hardcoded/soft) |
| **Música** | `/add-background-music` | Agregar música de fondo |
| **Resize** | `/resize` | Cambiar resolución/plataforma |
| **Extract Audio** | `/extract-audio` | Extraer audio de video |
| **Thumbnail** | `/thumbnail` | Generar imagen thumbnail |
| **Trim** | `/trim` | Cortar segmento de video |
| **Normalize** | `/normalize-audio` | Normalizar audio (LUFS) |
| **Full Pipeline** | `/full-pipeline` | Pipeline completo automático |

---

## 🚀 Despliegue en Easypanel

### Opción 1: Desde GitHub (Recomendado)

1. Sube estos archivos a un repo de GitHub
2. En Easypanel:
   - **+ Create** → **App**
   - Nombre: `ffmpeg-service`
   - Source: **GitHub**
   - Build: **Dockerfile**
   - Port: `5000`
3. **Deploy**

### Opción 2: Docker Compose

1. En Easypanel: **+ Create** → **App**
2. Source: **Docker Compose**
3. Pega el contenido de `docker-compose.yml`
4. **Deploy**

---

## 📚 API Reference

### Health Check
```bash
GET /health
```

### Info del Servicio
```bash
GET /info
```

---

### 1. Merge Video + Audio

Combina video Manim con audio TTS.

```bash
POST /merge
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "audio_base64": "//uQxAAA...",
  "volume": 1.0
}
```

**Alternativas:**
- `video_url` en lugar de `video_job_id`
- `audio_url` en lugar de `audio_base64`

---

### 2. Concatenar Videos

Une múltiples videos en uno.

```bash
POST /concat
Content-Type: application/json

{
  "videos": [
    {"job_id": "video1_job"},
    {"job_id": "video2_job"},
    {"url": "https://example.com/video3.mp4"}
  ],
  "transition": "none"
}
```

**Transiciones disponibles:** `none`, `fade`, `dissolve`

---

### 3. Agregar Subtítulos

```bash
POST /add-subtitles
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "subtitles": "1\n00:00:00,000 --> 00:00:05,000\nHola, bienvenidos\n\n2\n00:00:05,000 --> 00:00:10,000\nHoy aprenderemos física",
  "style": "hardcoded",
  "font_size": 24,
  "position": "bottom"
}
```

**Estilos:** `hardcoded` (quemados) o `soft` (stream separado)

---

### 4. Agregar Música de Fondo

```bash
POST /add-background-music
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "music_url": "https://example.com/lofi.mp3",
  "music_volume": 0.15,
  "voice_volume": 1.0,
  "loop_music": true,
  "fade_out": 2.0
}
```

---

### 5. Resize / Cambiar Plataforma

```bash
POST /resize
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "preset": "youtube_shorts"
}
```

**Presets disponibles:**
| Preset | Resolución | Aspect Ratio |
|--------|------------|--------------|
| `youtube_shorts` | 1080x1920 | 9:16 |
| `tiktok` | 1080x1920 | 9:16 |
| `instagram_reels` | 1080x1920 | 9:16 |
| `instagram_feed` | 1080x1080 | 1:1 |
| `youtube_long` | 1920x1080 | 16:9 |
| `youtube_4k` | 3840x2160 | 16:9 |
| `linkedin` | 1920x1080 | 16:9 |

**Modos de ajuste (`fit`):**
- `contain`: Mantiene aspect ratio, agrega letterbox
- `cover`: Llena todo, recorta si es necesario
- `stretch`: Deforma para llenar

---

### 6. Extraer Audio

```bash
POST /extract-audio
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "format": "mp3"
}
```

**Formatos:** `mp3`, `aac`, `wav`

---

### 7. Generar Thumbnail

```bash
POST /thumbnail
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "timestamp": 5.0,
  "width": 1280,
  "height": 720
}
```

---

### 8. Trim / Cortar Video

```bash
POST /trim
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "start": 5,
  "end": 30
}
```

O usar `duration` en lugar de `end`.

---

### 9. Normalizar Audio

```bash
POST /normalize-audio
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "target_lufs": -14,
  "peak_limit": -1.0
}
```

**Targets LUFS recomendados:**
- YouTube: -14
- Spotify: -14
- Broadcast TV: -24
- Podcast: -16

---

### 10. 🌟 Full Pipeline (Recomendado)

Pipeline completo para videos educativos.

```bash
POST /full-pipeline
Content-Type: application/json

{
  "video_job_id": "1b3d77a1",
  "audio_base64": "//uQxAAA...",
  "subtitles": "1\n00:00:00,000 --> 00:00:05,000\nHola",
  "background_music_url": "https://example.com/lofi.mp3",
  "music_volume": 0.1,
  "platform": "youtube_shorts",
  "normalize": true
}
```

**Pasos ejecutados automáticamente:**
1. ✅ Descargar video Manim
2. ✅ Merge con audio TTS
3. ✅ Agregar música de fondo
4. ✅ Agregar subtítulos
5. ✅ Resize para plataforma
6. ✅ Normalizar audio

---

### Probe / Info de Archivo

```bash
POST /probe
Content-Type: application/json

{
  "job_id": "1b3d77a1"
}
```

---

### Descargar Resultado

```bash
GET /download/{job_id}/{filename}
```

---

### Limpiar Archivos

```bash
DELETE /cleanup/{job_id}
DELETE /cleanup-all
```

---

## 🔧 Integración con n8n

### Ejemplo: Workflow de Video Educativo

```javascript
// 1. Render Manim → obtiene job_id
// 2. Generar TTS → obtiene audio_base64
// 3. FFmpeg Full Pipeline

// Nodo HTTP Request
{
  "method": "POST",
  "url": "https://ffmpeg-service.../full-pipeline",
  "body": {
    "video_job_id": "={{ $json.manim_job_id }}",
    "audio_base64": "={{ $binary.audio.data }}",
    "platform": "youtube_shorts",
    "normalize": true
  }
}
```

---

## 📊 Especificaciones Técnicas

- **Video codec**: H.264 (libx264)
- **Audio codec**: AAC
- **Audio bitrate**: 192 kbps
- **Video CRF**: 23 (calidad media-alta)
- **Preset encoding**: medium
- **Container**: MP4 con faststart

---

## 🗂️ Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MANIM_RENDERER_URL` | `https://manim-renderer-manim-renderer.5gad6x.easypanel.host` | URL del renderer Manim |

---

## 📝 Notas

- Timeout máximo: 10 minutos por operación
- Los archivos temporales se eliminan automáticamente después de 1 hora
- El full-pipeline es la forma recomendada para producción
