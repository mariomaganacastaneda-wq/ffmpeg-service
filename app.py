"""
FFmpeg Service - Servicio completo de procesamiento de video
Para proyecto de videos educativos UNAM/IPN
"""
from flask import Flask, request, jsonify, send_file
import subprocess
import base64
import os
import uuid
import requests
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Configuración
TEMP_DIR = Path("/tmp/ffmpeg-service")
TEMP_DIR.mkdir(exist_ok=True)

# URL base del renderer Manim
MANIM_RENDERER_URL = os.environ.get(
    'MANIM_RENDERER_URL', 
    'https://manim-renderer-manim-renderer.5gad6x.easypanel.host'
)

# ============================================================
# UTILIDADES
# ============================================================

def get_job_dir(job_id):
    """Crear y retornar directorio para un job"""
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    return job_dir

def download_file(url, dest_path, timeout=120):
    """Descargar archivo desde URL"""
    response = requests.get(url, timeout=timeout, stream=True)
    response.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path

def save_base64_file(base64_data, dest_path):
    """Guardar archivo desde base64"""
    with open(dest_path, 'wb') as f:
        f.write(base64.b64decode(base64_data))
    return dest_path

def get_media_info(file_path):
    """Obtener información de un archivo multimedia"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return None

def run_ffmpeg(cmd, timeout=600):
    """Ejecutar comando FFmpeg con manejo de errores"""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {
        'success': result.returncode == 0,
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr[-1000:] if result.stderr else None
    }


# ============================================================
# ENDPOINTS DE SALUD E INFO
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "service": "ffmpeg-service",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/info', methods=['GET'])
def info():
    """Información del servicio y versión de FFmpeg"""
    ffmpeg_version = subprocess.run(
        ['ffmpeg', '-version'], 
        capture_output=True, text=True
    ).stdout.split('\n')[0]
    
    return jsonify({
        "service": "ffmpeg-service",
        "version": "1.0.0",
        "ffmpeg": ffmpeg_version,
        "endpoints": [
            "POST /merge - Combinar video + audio",
            "POST /concat - Concatenar múltiples videos",
            "POST /add-subtitles - Agregar subtítulos",
            "POST /add-background-music - Agregar música de fondo",
            "POST /resize - Cambiar resolución",
            "POST /extract-audio - Extraer audio de video",
            "POST /convert - Convertir formato",
            "POST /thumbnail - Generar thumbnail",
            "POST /trim - Cortar video",
            "POST /normalize-audio - Normalizar audio",
            "POST /full-pipeline - Pipeline completo para videos educativos",
            "GET /probe - Obtener info de archivo",
            "GET /download/{job_id} - Descargar resultado",
            "DELETE /cleanup/{job_id} - Limpiar archivos"
        ],
        "manim_renderer": MANIM_RENDERER_URL
    })


# ============================================================
# 1. MERGE VIDEO + AUDIO
# ============================================================

@app.route('/merge', methods=['POST'])
def merge_audio_video():
    """
    Combinar video + audio (TTS)
    
    Body:
    {
        "video_url": "url" | "video_job_id": "manim_job_id",
        "audio_base64": "base64" | "audio_url": "url",
        "volume": 1.0  // opcional, volumen del audio
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        # Obtener audio
        audio_path = job_dir / "input_audio.mp3"
        if data.get('audio_base64'):
            save_base64_file(data['audio_base64'], audio_path)
        elif data.get('audio_url'):
            download_file(data['audio_url'], audio_path)
        else:
            return jsonify({"success": False, "error": "audio_base64 or audio_url required"}), 400
        
        # Volumen del audio
        volume = data.get('volume', 1.0)
        
        output_path = job_dir / f"merged_{job_id}.mp4"
        
        # FFmpeg: merge con control de volumen
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(audio_path),
            '-filter_complex', f'[1:a]volume={volume}[a]',
            '-map', '0:v',
            '-map', '[a]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "merge",
            "output_url": f"/download/{job_id}/merged_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 2. CONCATENAR MÚLTIPLES VIDEOS
# ============================================================

@app.route('/concat', methods=['POST'])
def concat_videos():
    """
    Concatenar múltiples videos en uno
    
    Body:
    {
        "videos": [
            {"url": "url1"} | {"job_id": "manim_job1"} | {"base64": "..."},
            {"url": "url2"} | {"job_id": "manim_job2"},
            ...
        ],
        "transition": "none" | "fade" | "dissolve",  // opcional
        "transition_duration": 0.5  // segundos
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        videos = data.get('videos', [])
        if len(videos) < 2:
            return jsonify({"success": False, "error": "At least 2 videos required"}), 400
        
        transition = data.get('transition', 'none')
        trans_duration = data.get('transition_duration', 0.5)
        
        # Descargar todos los videos
        input_files = []
        for i, video in enumerate(videos):
            video_path = job_dir / f"input_{i}.mp4"
            
            if video.get('url'):
                download_file(video['url'], video_path)
            elif video.get('job_id'):
                url = f"{MANIM_RENDERER_URL}/video/{video['job_id']}"
                download_file(url, video_path)
            elif video.get('base64'):
                save_base64_file(video['base64'], video_path)
            else:
                return jsonify({"success": False, "error": f"Invalid video source at index {i}"}), 400
            
            input_files.append(video_path)
        
        output_path = job_dir / f"concat_{job_id}.mp4"
        
        if transition == 'none':
            # Concatenación simple con concat demuxer
            list_file = job_dir / "inputs.txt"
            with open(list_file, 'w') as f:
                for vf in input_files:
                    f.write(f"file '{vf}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c', 'copy',
                '-movflags', '+faststart',
                str(output_path)
            ]
        else:
            # Concatenación con transiciones (requiere re-encoding)
            filter_parts = []
            n = len(input_files)
            
            # Inputs
            inputs = []
            for i, vf in enumerate(input_files):
                inputs.extend(['-i', str(vf)])
            
            # Filter complex para transiciones
            if transition == 'fade':
                # Crear filtro de crossfade
                filter_complex = ""
                for i in range(n):
                    filter_complex += f"[{i}:v]setpts=PTS-STARTPTS[v{i}];"
                    filter_complex += f"[{i}:a]asetpts=PTS-STARTPTS[a{i}];"
                
                # Concatenar con xfade
                for i in range(n-1):
                    if i == 0:
                        filter_complex += f"[v0][v1]xfade=transition=fade:duration={trans_duration}:offset=0[vout{i}];"
                    else:
                        filter_complex += f"[vout{i-1}][v{i+1}]xfade=transition=fade:duration={trans_duration}:offset=0[vout{i}];"
                
                filter_complex += f"[vout{n-2}]null[vfinal]"
                
            cmd = [
                'ffmpeg', '-y',
                *inputs,
                '-filter_complex', filter_complex if transition != 'none' else '',
                '-map', '[vfinal]',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-movflags', '+faststart',
                str(output_path)
            ]
        
        result = run_ffmpeg(cmd, timeout=900)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "concat",
            "video_count": len(videos),
            "output_url": f"/download/{job_id}/concat_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 3. AGREGAR SUBTÍTULOS
# ============================================================

@app.route('/add-subtitles', methods=['POST'])
def add_subtitles():
    """
    Agregar subtítulos a video (hardcoded o soft)
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "subtitles": "contenido SRT" | "subtitles_url": "url",
        "style": "hardcoded" | "soft",
        "font_size": 24,
        "font_color": "white",
        "outline_color": "black",
        "position": "bottom"  // bottom, top, middle
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        # Obtener subtítulos
        srt_path = job_dir / "subtitles.srt"
        if data.get('subtitles'):
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(data['subtitles'])
        elif data.get('subtitles_url'):
            download_file(data['subtitles_url'], srt_path)
        else:
            return jsonify({"success": False, "error": "subtitles or subtitles_url required"}), 400
        
        style = data.get('style', 'hardcoded')
        font_size = data.get('font_size', 24)
        font_color = data.get('font_color', 'white')
        outline_color = data.get('outline_color', 'black')
        position = data.get('position', 'bottom')
        
        output_path = job_dir / f"subtitled_{job_id}.mp4"
        
        if style == 'hardcoded':
            # Subtítulos quemados en el video
            margin_v = 50 if position == 'bottom' else 50
            alignment = 2 if position == 'bottom' else 6  # SSA alignment
            
            subtitle_filter = (
                f"subtitles='{srt_path}':"
                f"force_style='FontSize={font_size},"
                f"PrimaryColour=&H00FFFFFF,"  # white
                f"OutlineColour=&H00000000,"  # black
                f"BorderStyle=3,"
                f"Outline=2,"
                f"MarginV={margin_v},"
                f"Alignment={alignment}'"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vf', subtitle_filter,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                str(output_path)
            ]
        else:
            # Subtítulos como stream separado (soft)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-i', str(srt_path),
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-c:s', 'mov_text',
                '-movflags', '+faststart',
                str(output_path)
            ]
        
        result = run_ffmpeg(cmd, timeout=600)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "add-subtitles",
            "style": style,
            "output_url": f"/download/{job_id}/subtitled_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 4. AGREGAR MÚSICA DE FONDO
# ============================================================

@app.route('/add-background-music', methods=['POST'])
def add_background_music():
    """
    Agregar música de fondo a video
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "music_url": "url" | "music_base64": "base64",
        "music_volume": 0.15,  // volumen de la música (0.0-1.0)
        "voice_volume": 1.0,  // volumen del audio original
        "loop_music": true,   // repetir música si es más corta
        "fade_out": 2.0       // fade out al final (segundos)
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        # Obtener música
        music_path = job_dir / "music.mp3"
        if data.get('music_base64'):
            save_base64_file(data['music_base64'], music_path)
        elif data.get('music_url'):
            download_file(data['music_url'], music_path)
        else:
            return jsonify({"success": False, "error": "music_url or music_base64 required"}), 400
        
        music_vol = data.get('music_volume', 0.15)
        voice_vol = data.get('voice_volume', 1.0)
        loop_music = data.get('loop_music', True)
        fade_out = data.get('fade_out', 2.0)
        
        output_path = job_dir / f"with_music_{job_id}.mp4"
        
        # Obtener duración del video
        info = get_media_info(video_path)
        duration = float(info['format']['duration']) if info else 60
        
        # Construir filtro de audio
        music_filter = f"[1:a]volume={music_vol}"
        if loop_music:
            music_filter = f"[1:a]aloop=loop=-1:size=2e+09,volume={music_vol}"
        if fade_out > 0:
            music_filter += f",afade=t=out:st={duration-fade_out}:d={fade_out}"
        music_filter += "[music]"
        
        filter_complex = (
            f"[0:a]volume={voice_vol}[voice];"
            f"{music_filter};"
            f"[voice][music]amix=inputs=2:duration=first[aout]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-stream_loop', '-1' if loop_music else '0',
            '-i', str(music_path),
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "add-background-music",
            "output_url": f"/download/{job_id}/with_music_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 5. RESIZE / CAMBIAR RESOLUCIÓN
# ============================================================

@app.route('/resize', methods=['POST'])
def resize_video():
    """
    Cambiar resolución de video (para diferentes plataformas)
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "width": 1080,
        "height": 1920,
        "preset": "youtube_shorts" | "tiktok" | "instagram_reels" | "youtube_long",
        "fit": "contain" | "cover" | "stretch",
        "background_color": "black"
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Presets de plataformas
        presets = {
            'youtube_shorts': {'width': 1080, 'height': 1920},
            'tiktok': {'width': 1080, 'height': 1920},
            'instagram_reels': {'width': 1080, 'height': 1920},
            'instagram_feed': {'width': 1080, 'height': 1080},
            'youtube_long': {'width': 1920, 'height': 1080},
            'youtube_4k': {'width': 3840, 'height': 2160},
            'linkedin': {'width': 1920, 'height': 1080},
        }
        
        # Obtener dimensiones
        if data.get('preset') and data['preset'] in presets:
            width = presets[data['preset']]['width']
            height = presets[data['preset']]['height']
        else:
            width = data.get('width', 1920)
            height = data.get('height', 1080)
        
        fit = data.get('fit', 'contain')
        bg_color = data.get('background_color', 'black')
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        output_path = job_dir / f"resized_{job_id}.mp4"
        
        # Construir filtro según tipo de ajuste
        if fit == 'contain':
            # Mantener aspect ratio, agregar letterbox/pillarbox
            vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={bg_color},setsar=1"
        elif fit == 'cover':
            # Llenar todo, recortar si es necesario
            vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
        else:
            # Stretch - deformar
            vf = f"scale={width}:{height},setsar=1"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', vf,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "resize",
            "dimensions": f"{width}x{height}",
            "output_url": f"/download/{job_id}/resized_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 6. EXTRAER AUDIO
# ============================================================

@app.route('/extract-audio', methods=['POST'])
def extract_audio():
    """
    Extraer audio de video
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "format": "mp3" | "aac" | "wav"
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        audio_format = data.get('format', 'mp3')
        output_path = job_dir / f"audio_{job_id}.{audio_format}"
        
        codec_map = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'wav': 'pcm_s16le'
        }
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vn',
            '-c:a', codec_map.get(audio_format, 'libmp3lame'),
            '-b:a', '192k',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "extract-audio",
            "format": audio_format,
            "output_url": f"/download/{job_id}/audio_{job_id}.{audio_format}",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 7. GENERAR THUMBNAIL
# ============================================================

@app.route('/thumbnail', methods=['POST'])
def generate_thumbnail():
    """
    Generar thumbnail de video
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "timestamp": 5.0,  // segundos
        "width": 1280,
        "height": 720
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        timestamp = data.get('timestamp', 5.0)
        width = data.get('width', 1280)
        height = data.get('height', 720)
        
        output_path = job_dir / f"thumbnail_{job_id}.jpg"
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', str(video_path),
            '-vframes', '1',
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
            '-q:v', '2',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "thumbnail",
            "output_url": f"/download/{job_id}/thumbnail_{job_id}.jpg",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 8. TRIM / CORTAR VIDEO
# ============================================================

@app.route('/trim', methods=['POST'])
def trim_video():
    """
    Cortar video
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "start": 0,     // segundos
        "end": 30,      // segundos (o duration)
        "duration": 30  // alternativa a end
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        start = data.get('start', 0)
        duration = data.get('duration')
        end = data.get('end')
        
        if duration is None and end is not None:
            duration = end - start
        
        output_path = job_dir / f"trimmed_{job_id}.mp4"
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', str(video_path),
        ]
        
        if duration:
            cmd.extend(['-t', str(duration)])
        
        cmd.extend([
            '-c', 'copy',
            '-movflags', '+faststart',
            str(output_path)
        ])
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "trim",
            "output_url": f"/download/{job_id}/trimmed_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 9. NORMALIZAR AUDIO
# ============================================================

@app.route('/normalize-audio', methods=['POST'])
def normalize_audio():
    """
    Normalizar audio de video
    
    Body:
    {
        "video_url": "url" | "video_job_id": "id",
        "target_lufs": -14,  // LUFS target (YouTube: -14, Spotify: -14, broadcast: -24)
        "peak_limit": -1.0   // dB
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # Obtener video
        video_path = job_dir / "input_video.mp4"
        if data.get('video_url'):
            download_file(data['video_url'], video_path)
        elif data.get('video_job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['video_job_id']}"
            download_file(url, video_path)
        else:
            return jsonify({"success": False, "error": "video_url or video_job_id required"}), 400
        
        target_lufs = data.get('target_lufs', -14)
        peak_limit = data.get('peak_limit', -1.0)
        
        output_path = job_dir / f"normalized_{job_id}.mp4"
        
        # Usar loudnorm filter
        af = f"loudnorm=I={target_lufs}:TP={peak_limit}:LRA=11"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-c:v', 'copy',
            '-af', af,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        result = run_ffmpeg(cmd)
        
        if not result['success']:
            return jsonify({"success": False, "error": "FFmpeg failed", "details": result['stderr']}), 500
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "normalize-audio",
            "target_lufs": target_lufs,
            "output_url": f"/download/{job_id}/normalized_{job_id}.mp4",
            "file_size": output_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# 10. PIPELINE COMPLETO PARA VIDEOS EDUCATIVOS
# ============================================================

@app.route('/full-pipeline', methods=['POST'])
def full_pipeline():
    """
    Pipeline completo: Video Manim + Audio TTS + Música + Subtítulos + Resize
    
    Body:
    {
        "video_job_id": "manim_job_id",
        "audio_base64": "tts_audio_base64",
        "subtitles": "contenido SRT" (opcional),
        "background_music_url": "url" (opcional),
        "music_volume": 0.1,
        "platform": "youtube_shorts" | "tiktok" | "instagram_reels",
        "normalize": true
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        # 1. Descargar video Manim
        video_path = job_dir / "01_video.mp4"
        video_job_id = data.get('video_job_id')
        if not video_job_id:
            return jsonify({"success": False, "error": "video_job_id required"}), 400
        
        url = f"{MANIM_RENDERER_URL}/video/{video_job_id}"
        download_file(url, video_path)
        
        current_video = video_path
        steps_completed = ["download_video"]
        
        # 2. Merge con audio TTS
        if data.get('audio_base64'):
            audio_path = job_dir / "tts_audio.mp3"
            save_base64_file(data['audio_base64'], audio_path)
            
            merged_path = job_dir / "02_merged.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-i', str(current_video),
                '-i', str(audio_path),
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-movflags', '+faststart',
                str(merged_path)
            ]
            
            result = run_ffmpeg(cmd)
            if not result['success']:
                return jsonify({"success": False, "error": "Merge failed", "details": result['stderr']}), 500
            
            current_video = merged_path
            steps_completed.append("merge_tts")
        
        # 3. Agregar música de fondo
        if data.get('background_music_url'):
            music_path = job_dir / "music.mp3"
            download_file(data['background_music_url'], music_path)
            
            music_vol = data.get('music_volume', 0.1)
            music_path_out = job_dir / "03_with_music.mp4"
            
            info = get_media_info(current_video)
            duration = float(info['format']['duration']) if info else 60
            
            filter_complex = (
                f"[0:a]volume=1.0[voice];"
                f"[1:a]aloop=loop=-1:size=2e+09,volume={music_vol},"
                f"afade=t=out:st={duration-2}:d=2[music];"
                f"[voice][music]amix=inputs=2:duration=first[aout]"
            )
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(current_video),
                '-stream_loop', '-1',
                '-i', str(music_path),
                '-filter_complex', filter_complex,
                '-map', '0:v',
                '-map', '[aout]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-movflags', '+faststart',
                str(music_path_out)
            ]
            
            result = run_ffmpeg(cmd)
            if result['success']:
                current_video = music_path_out
                steps_completed.append("add_music")
        
        # 4. Agregar subtítulos
        if data.get('subtitles'):
            srt_path = job_dir / "subtitles.srt"
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(data['subtitles'])
            
            subtitled_path = job_dir / "04_subtitled.mp4"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(current_video),
                '-vf', f"subtitles='{srt_path}':force_style='FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,MarginV=50'",
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                str(subtitled_path)
            ]
            
            result = run_ffmpeg(cmd)
            if result['success']:
                current_video = subtitled_path
                steps_completed.append("add_subtitles")
        
        # 5. Resize para plataforma
        platform = data.get('platform')
        presets = {
            'youtube_shorts': (1080, 1920),
            'tiktok': (1080, 1920),
            'instagram_reels': (1080, 1920),
            'instagram_feed': (1080, 1080),
            'youtube_long': (1920, 1080),
        }
        
        if platform and platform in presets:
            width, height = presets[platform]
            resized_path = job_dir / "05_resized.mp4"
            
            vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(current_video),
                '-vf', vf,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                str(resized_path)
            ]
            
            result = run_ffmpeg(cmd)
            if result['success']:
                current_video = resized_path
                steps_completed.append(f"resize_{platform}")
        
        # 6. Normalizar audio
        if data.get('normalize', False):
            normalized_path = job_dir / "06_normalized.mp4"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', str(current_video),
                '-c:v', 'copy',
                '-af', 'loudnorm=I=-14:TP=-1:LRA=11',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                str(normalized_path)
            ]
            
            result = run_ffmpeg(cmd)
            if result['success']:
                current_video = normalized_path
                steps_completed.append("normalize_audio")
        
        # Copiar resultado final
        final_path = job_dir / f"final_{job_id}.mp4"
        import shutil
        shutil.copy(current_video, final_path)
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "operation": "full-pipeline",
            "steps_completed": steps_completed,
            "output_url": f"/download/{job_id}/final_{job_id}.mp4",
            "file_size": final_path.stat().st_size
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PROBE / INFO DE ARCHIVO
# ============================================================

@app.route('/probe', methods=['POST'])
def probe_media():
    """
    Obtener información de archivo multimedia
    
    Body:
    {
        "url": "url" | "job_id": "manim_job_id"
    }
    """
    try:
        data = request.json
        job_id = str(uuid.uuid4())[:8]
        job_dir = get_job_dir(job_id)
        
        file_path = job_dir / "probe_file"
        if data.get('url'):
            download_file(data['url'], file_path)
        elif data.get('job_id'):
            url = f"{MANIM_RENDERER_URL}/video/{data['job_id']}"
            download_file(url, file_path)
        else:
            return jsonify({"success": False, "error": "url or job_id required"}), 400
        
        info = get_media_info(file_path)
        
        # Limpiar archivos temporales
        import shutil
        shutil.rmtree(job_dir)
        
        return jsonify({
            "success": True,
            "info": info
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# DOWNLOAD Y CLEANUP
# ============================================================

@app.route('/download/<job_id>/<filename>', methods=['GET'])
def download_file_route(job_id, filename):
    """Descargar archivo procesado"""
    file_path = TEMP_DIR / job_id / filename
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    mimetype = 'video/mp4'
    if filename.endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif filename.endswith('.jpg'):
        mimetype = 'image/jpeg'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    
    return send_file(
        file_path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )


@app.route('/cleanup/<job_id>', methods=['DELETE'])
def cleanup(job_id):
    """Limpiar archivos temporales"""
    import shutil
    job_dir = TEMP_DIR / job_id
    
    if job_dir.exists():
        shutil.rmtree(job_dir)
        return jsonify({"success": True, "message": f"Cleaned up {job_id}"})
    
    return jsonify({"success": False, "error": "Job not found"}), 404


@app.route('/cleanup-all', methods=['DELETE'])
def cleanup_all():
    """Limpiar TODOS los archivos temporales"""
    import shutil
    
    count = 0
    for item in TEMP_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
            count += 1
    
    return jsonify({"success": True, "cleaned": count})


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
