from flask import Blueprint, render_template_string, request # <--- Tambah request
from ..models import Post, User
from ..extensions import limiter
web_bp = Blueprint('web', __name__)

@web_bp.route('/join/<string:chat_id>')
@limiter.limit("20 per minute")
def join_group_redirect(chat_id):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Redirecting...</title></head>
    <body><script>window.location.href = "amica://join/{chat_id}";</script></body>
    </html>
    """
    return render_template_string(html_content)


@web_bp.route('/post/<string:post_id>')
@limiter.limit("30 per minute")
def view_post_redirect(post_id):
    base_url = request.host_url.rstrip('/') 
    meta_image = f"{base_url}/static/images/logo_dark.png"
    
    meta_title = "Amica App"
    meta_desc = "Lihat postingan menarik di Amica."
    author_name = "Pengguna Amica"
    
    try:
        post = Post.query.filter_by(id=str(post_id)).first()
        if post:
            author = User.query.get(post.user_id)
            author_name = author.display_name if author else "User"
            
            meta_title = f"Postingan dari {author_name}"
            caption = post.caption if post.caption else "Lihat konten ini di Amica"
            meta_desc = (caption[:150] + '...') if len(caption) > 150 else caption
            
            if post.image_url:
                if post.image_url.startswith('http'):
                    meta_image = post.image_url
                else:

                    clean_path = post.image_url.lstrip('/')
                    meta_image = f"{base_url}/{clean_path}"
                    
    except Exception as e:
        print(f"Error generating preview: {e}")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="id" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{meta_title}</title>
        
        <meta property="og:title" content="{meta_title}" />
        <meta property="og:description" content="{meta_desc}" />
        <meta property="og:image" content="{meta_image}" />
        <meta property="og:type" content="article" />
        
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        
        <script>
            tailwind.config = {{
                darkMode: 'class',
                theme: {{
                    extend: {{
                        fontFamily: {{ sans: ['Inter', 'sans-serif'] }},
                        colors: {{
                            dark: {{ bg: '#0d1117', card: '#161b22', border: 'rgba(255,255,255,0.1)' }}
                        }},
                        animation: {{ 'fade-in': 'fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1)' }},
                        keyframes: {{
                            fadeIn: {{
                                '0%': {{ opacity: '0', transform: 'translateY(20px)' }},
                                '100%': {{ opacity: '1', transform: 'translateY(0)' }}
                            }}
                        }}
                    }}
                }}
            }}
        </script>
        <style>body {{ font-family: 'Inter', sans-serif; }}</style>
    </head>
    
    <body class="bg-[#0d1117] text-gray-200 h-screen flex flex-col items-center justify-center relative overflow-hidden">

        <div class="absolute inset-0 z-0 opacity-20 pointer-events-none">
            <div class="absolute top-0 left-0 w-full h-full bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-900/30 via-[#0d1117] to-[#0d1117]"></div>
        </div>

        <div class="relative z-10 w-full max-w-sm mx-4 bg-[#161b22] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-fade-in">
            
            <div class="px-6 py-4 border-b border-white/5 flex items-center justify-center bg-[#161b22]">
                <span class="text-lg font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent tracking-tight">
                    Amica App
                </span>
            </div>

            <!-- Bagian Gambar -->
            <!-- Tambahkan background gray biar kalau loading gak hitam pekat -->
            <div class="relative w-full aspect-video bg-gray-800 overflow-hidden group border-b border-white/5">
                <img src="{meta_image}" 
                     class="w-full h-full object-cover transition-transform duration-700 ease-in-out group-hover:scale-105" 
                     alt="Preview">
                
                <div class="absolute inset-0 bg-gradient-to-t from-[#161b22] to-transparent opacity-50"></div>
            </div>

            <div class="p-6 text-center">
                <h2 class="text-lg font-bold text-white mb-2 leading-tight">
                    {meta_title}
                </h2>
                
                <p class="text-sm text-gray-400 mb-6 line-clamp-2 leading-relaxed">
                    {meta_desc}
                </p>

                <a href="amica://post/{post_id}" 
                   class="flex items-center justify-center w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-lg shadow-blue-900/20 transition-all duration-200 transform active:scale-95 group">
                    <span>Buka di Aplikasi</span>
                    <svg class="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                </a>

                <div class="mt-4 flex items-center justify-center gap-2">
                    <div class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
                    <p class="text-xs text-gray-500">Mengalihkan secara otomatis...</p>
                </div>
            </div>

            <div class="h-1 w-full bg-[#0d1117]">
                <div class="h-full bg-gradient-to-r from-blue-600 to-cyan-500 animate-progress w-0"></div>
            </div>
        </div>

        <script>
            setTimeout(function() {{
                window.location.href = "amica://post/{post_id}";
            }}, 1200); 
        </script>

    </body>
    </html>
    """
    return render_template_string(html_content)