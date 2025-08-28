from flask import Flask, request, jsonify
import yt_dlp
import re
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

def clean_text(text):
    """Clean and format text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    # Remove extra spaces and newlines
    text = ' '.join(text.split())
    return text

def get_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Handle different YouTube URL formats
    if parsed_url.netloc in ['youtube.com', 'www.youtube.com']:
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        elif parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
        elif parsed_url.path.startswith('/shorts/'):
            return parsed_url.path.split('/')[2]
    
    elif parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    
    return None

def get_youtube_info(video_url):
    """Get complete information about a YouTube video"""
    try:
        # Get video ID first
        video_id = get_video_id(video_url)
        if not video_id:
            return {'success': False, 'error': 'Invalid YouTube URL'}
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'forcejson': True,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Extract available formats
            formats = []
            for fmt in info.get('formats', []):
                if fmt.get('url'):
                    formats.append({
                        'format_id': fmt.get('format_id'),
                        'extension': fmt.get('ext'),
                        'resolution': fmt.get('resolution', 'audio'),
                        'filesize': fmt.get('filesize'),
                        'filesize_mb': round(fmt.get('filesize', 0) / (1024 * 1024), 2) if fmt.get('filesize') else None,
                        'format_note': fmt.get('format_note'),
                        'audio_codec': fmt.get('acodec'),
                        'video_codec': fmt.get('vcodec'),
                    })
            
            # Extract thumbnails (sorted by quality)
            thumbnails = sorted(
                info.get('thumbnails', []),
                key=lambda x: x.get('width', 0) * x.get('height', 0),
                reverse=True
            )
            
            # Extract chapters if available
            chapters = []
            for chapter in info.get('chapters', []):
                chapters.append({
                    'start_time': chapter.get('start_time'),
                    'end_time': chapter.get('end_time'),
                    'title': chapter.get('title')
                })
            
            # Main video information
            video_info = {
                'video_id': info.get('id'),
                'title': info.get('title', ''),
                'description': clean_text(info.get('description', ''))[:500] + '...' if info.get('description') else '',
                'duration': info.get('duration', 0),
                'duration_formatted': f"{info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}",
                'upload_date': info.get('upload_date', ''),
                'upload_date_formatted': f"{info.get('upload_date', '')[:4]}-{info.get('upload_date', '')[4:6]}-{info.get('upload_date', '')[6:8]}" if info.get('upload_date') else '',
                'uploader': info.get('uploader', ''),
                'uploader_id': info.get('uploader_id', ''),
                'uploader_url': info.get('uploader_url', ''),
                'channel': info.get('channel', ''),
                'channel_id': info.get('channel_id', ''),
                'channel_url': info.get('channel_url', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'comment_count': info.get('comment_count', 0),
                'average_rating': info.get('average_rating', 0),
                'age_limit': info.get('age_limit', 0),
                'categories': info.get('categories', []),
                'tags': info.get('tags', [])[:10],
                'thumbnails': thumbnails[:5],
                'formats': formats[:10],
                'chapters': chapters[:10],
                'webpage_url': info.get('webpage_url', ''),
                'original_url': video_url,
                'is_live': info.get('is_live', False),
                'was_live': info.get('was_live', False),
            }
            
            return {'success': True, 'data': video_info}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/api/youtube/info', methods=['GET'])
def youtube_info():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "supported_urls": [
                "https://www.youtube.com/watch?v=VIDEO_ID",
                "https://youtu.be/VIDEO_ID", 
                "https://www.youtube.com/shorts/VIDEO_ID",
                "https://www.youtube.com/embed/VIDEO_ID"
            ],
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 400
    
    try:
        result = get_youtube_info(video_url)
        
        if result['success']:
            return jsonify({
                "success": True,
                "data": result['data'],
                "credit": "Made with ❤️ by @DIWANI_xD"
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error'],
                "url": video_url,
                "credit": "Made with ❤️ by @DIWANI_xD"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "url": video_url,
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 500

@app.route('/api/youtube/formats', methods=['GET'])
def youtube_formats():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube/formats?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'forcejson': True,
            'listformats': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            formats = []
            for fmt in info.get('formats', []):
                if fmt.get('url'):
                    formats.append({
                        'format_id': fmt.get('format_id'),
                        'extension': fmt.get('ext'),
                        'resolution': fmt.get('resolution', 'audio'),
                        'filesize': fmt.get('filesize'),
                        'filesize_mb': round(fmt.get('filesize', 0) / (1024 * 1024), 2) if fmt.get('filesize') else None,
                        'format_note': fmt.get('format_note'),
                        'audio_codec': fmt.get('acodec'),
                        'video_codec': fmt.get('vcodec'),
                        'quality': fmt.get('quality'),
                    })
            
            # Sort formats by resolution quality
            formats.sort(key=lambda x: (
                0 if 'audio' in str(x['resolution']) else 1,
                x['filesize'] or 0
            ), reverse=True)
            
            return jsonify({
                "success": True,
                "video_id": info.get('id'),
                "title": info.get('title'),
                "duration": info.get('duration'),
                "formats": formats[:15],  # Limit to 15 formats
                "credit": "Made with ❤️ by @DIWANI_xD"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "url": video_url,
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 500

@app.route('/api/youtube/thumbnail', methods=['GET'])
def youtube_thumbnail():
    video_url = request.args.get('url')
    quality = request.args.get('quality', 'maxres')
    
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube/thumbnail?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "quality_options": ["maxres", "high", "medium", "default"],
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 400
    
    try:
        video_id = get_video_id(video_url)
        if not video_id:
            return jsonify({
                "success": False,
                "error": "Invalid YouTube URL",
                "credit": "Made with ❤️ by @DIWANI_xD"
            }), 400
        
        # YouTube thumbnail URLs pattern
        qualities = {
            'maxres': f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg',
            'high': f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg',
            'medium': f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg',
            'default': f'https://i.ytimg.com/vi/{video_id}/default.jpg',
        }
        
        thumbnail_url = qualities.get(quality, qualities['maxres'])
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "thumbnail_url": thumbnail_url,
            "quality": quality,
            "all_qualities": qualities,
            "credit": "Made with ❤️ by @DIWANI_xD"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "url": video_url,
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 500

@app.route('/')
def home():
    return jsonify({
        "message": "YouTube Information API",
        "version": "1.0",
        "endpoints": {
            "video_info": "/api/youtube/info?url=YOUTUBE_URL",
            "available_formats": "/api/youtube/formats?url=YOUTUBE_URL",
            "thumbnails": "/api/youtube/thumbnail?url=YOUTUBE_URL&quality=maxres",
            "example": "/api/youtube/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        },
        "features": [
            "Complete video information",
            "Available formats & qualities", 
            "Thumbnail URLs",
            "Channel information",
            "View/like/comment counts",
            "Video metadata"
        ],
        "credit": "Made with ❤️ by @DIWANI_xD"
    })

if __name__ == '__main__':
    app.run(debug=True)