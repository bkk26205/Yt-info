from flask import Flask, request, jsonify
import yt_dlp
import re
from urllib.parse import urlparse, parse_qs
import random

app = Flask(__name__)

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def clean_text(text):
    """Clean and format text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    text = ' '.join(text.split())
    return text

def get_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    try:
        parsed_url = urlparse(url)
        
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
            return parsed_url.path[1:].split('?')[0]  # Remove query parameters
        
        return None
    except:
        return None

def get_youtube_info(video_url):
    """Get complete information about a YouTube video with bot bypass"""
    try:
        video_id = get_video_id(video_url)
        if not video_id:
            return {'success': False, 'error': 'Invalid YouTube URL'}
        
        # Updated yt-dlp options to avoid bot detection
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'forcejson': True,
            'noplaylist': True,
            'geo_bypass': True,
            'geo_bypass_country': 'US',
            'http_headers': {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_client': ['android', 'web']
                }
            }
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
                    })
            
            # Extract thumbnails
            thumbnails = []
            for thumb in info.get('thumbnails', []):
                if thumb.get('url'):
                    thumbnails.append({
                        'url': thumb.get('url'),
                        'width': thumb.get('width'),
                        'height': thumb.get('height')
                    })
            
            # Main video information
            video_info = {
                'video_id': info.get('id'),
                'title': info.get('title', ''),
                'description': clean_text(info.get('description', ''))[:300] if info.get('description') else '',
                'duration': info.get('duration', 0),
                'duration_formatted': f"{info.get('duration', 0) // 60}:{info.get('duration', 0) % 60:02d}",
                'upload_date': info.get('upload_date', ''),
                'uploader': info.get('uploader', ''),
                'channel': info.get('channel', ''),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'thumbnails': thumbnails[:3],
                'formats': formats[:8],
                'webpage_url': info.get('webpage_url', ''),
            }
            
            return {'success': True, 'data': video_info}
            
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm you're not a bot" in error_msg:
            return {'success': False, 'error': 'YouTube bot detection triggered. Please try again later.'}
        elif "Private video" in error_msg:
            return {'success': False, 'error': 'This video is private and cannot be accessed.'}
        elif "Video unavailable" in error_msg:
            return {'success': False, 'error': 'Video is unavailable or has been removed.'}
        else:
            return {'success': False, 'error': f'Error: {error_msg}'}

def get_basic_youtube_info(video_id):
    """Alternative method using YouTube oEmbed API"""
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        
        response = requests.get(oembed_url, headers={
            'User-Agent': random.choice(USER_AGENTS)
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': {
                    'video_id': video_id,
                    'title': data.get('title', ''),
                    'author_name': data.get('author_name', ''),
                    'thumbnail_url': data.get('thumbnail_url', ''),
                    'type': 'basic'
                }
            }
        return {'success': False, 'error': 'Could not fetch basic info'}
    except:
        return {'success': False, 'error': 'Basic info fetch failed'}

@app.route('/api/youtube/info', methods=['GET'])
def youtube_info():
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
            "example": "/api/youtube/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 400
    
    try:
        # Clean the URL (remove tracking parameters)
        clean_url = video_url.split('?')[0] if '?si=' in video_url else video_url
        
        result = get_youtube_info(clean_url)
        
        # If main method fails, try basic method
        if not result['success']:
            video_id = get_video_id(clean_url)
            if video_id:
                result = get_basic_youtube_info(video_id)
        
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
                "url": clean_url,
                "credit": "Made with ❤️ by @DIWANI_xD"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "url": video_url,
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 500

@app.route('/api/youtube/basic', methods=['GET'])
def youtube_basic():
    """Basic info endpoint that works with oEmbed"""
    video_url = request.args.get('url')
    
    if not video_url:
        return jsonify({
            "success": False,
            "error": "URL parameter is required",
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
        
        result = get_basic_youtube_info(video_id)
        
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
                "credit": "Made with ❤️ by @DIWANI_xD"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "credit": "Made with ❤️ by @DIWANI_xD"
        }), 500

@app.route('/')
def home():
    return jsonify({
        "message": "YouTube Information API - Fixed Version",
        "endpoints": {
            "video_info": "/api/youtube/info?url=YOUTUBE_URL",
            "basic_info": "/api/youtube/basic?url=YOUTUBE_URL",
            "example": "/api/youtube/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        },
        "note": "Now with bot detection bypass and fallback methods",
        "credit": "Made with ❤️ by @DIWANI_xD"
    })

if __name__ == '__main__':
    app.run(debug=True)
