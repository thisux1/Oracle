import os

source_art_path = '/home/thiago/Documentos/codesnippets/discbot/Oracle-V2/bot/tui_splash_art.py'
banner_out_path = '/home/thiago/Documentos/codesnippets/discbot/Oracle-V2/docs/banner.svg'

with open(source_art_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = 'GIANT_EYE_ART = r"""'
start_idx = content.find(start_marker)
if start_idx == -1:
    start_marker = 'GIANT_EYE_ART = """'
    start_idx = content.find(start_marker)

start_idx += len(start_marker)
end_idx = content.find('"""', start_idx)
giant_eye_art = content[start_idx:end_idx].strip('\n')

def decode_braille(char):
    code = ord(char)
    if 0x2800 <= code <= 0x28FF:
        val = code - 0x2800
        dots = []
        offsets = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)]
        for bit in range(8):
            if (val >> bit) & 1:
                dots.append(offsets[bit])
        return dots
    return []

points = []
lines = giant_eye_art.split('\n')
for y_char, line in enumerate(lines):
    for x_char, char in enumerate(line):
        if char == ' ' or char == '\u3000' or char == '\u2800':
            continue
        dots = decode_braille(char)
        for dx, dy in dots:
            pixel_x = x_char * 2.5 + dx * 1.2
            pixel_y = y_char * 4.5 + dy * 1.1
            points.append((pixel_x, pixel_y))

min_x = min(p[0] for p in points)
max_x = max(p[0] for p in points)
min_y = min(p[1] for p in points)
max_y = max(p[1] for p in points)

eye_w = max_x - min_x
eye_h = max_y - min_y

target_width = 280.0
scale = target_width / eye_w

tx = 100.0
ty = 25.0

shifted_dots = []
for sx, sy in points:
    shifted_dots.append(f'  <circle cx="{sx - min_x:.1f}" cy="{sy - min_y:.1f}" r="1.1" />')
dots_xml_str = '\n'.join(shifted_dots)

ascii_title = """ ██████╗ ██████╗  █████╗  ██████╗██╗     ███████╗   ██╗   ██╗██████╗ 
██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔════╝   ██║   ██║╚════██╗
██║   ██║██████╔╝███████║██║     ██║     █████╗     ██║   ██║ █████╔╝
██║   ██║██╔══██╗██╔══██║██║     ██║     ██╔══╝     ╚██╗ ██╔╝ ╚═══██╗
╚██████╔╝██║  ██║██║  ██║╚██████╗███████╗███████╗    ╚████╔╝ ██████╔╝
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝     ╚═══╝  ╚═════╝"""

title_lines = ascii_title.split('\n')
cw = 6.4
ch = 13.0
start_x = 27.0
start_y = 280.0

path_parts = []
for r, line in enumerate(title_lines):
    for c, char in enumerate(line):
        x = start_x + c * cw
        y = start_y + r * ch
        if char == '█':
            path_parts.append(f'M{x:.2f},{y:.2f}h{cw:.2f}v{ch:.2f}h{-cw:.2f}z')
        elif char == '═':
            path_parts.append(f'M{x:.2f},{y:.2f}h{cw:.2f}v3.0h{-cw:.2f}z')
        elif char == '║':
            path_parts.append(f'M{x:.2f},{y:.2f}h3.0v{ch:.2f}h-3.0z')
        elif char == '╔':
            path_parts.append(f'M{x:.2f},{y:.2f}h{cw:.2f}v3.0h{-cw+3.0:.2f}v{ch-3.0:.2f}h-3.0z')
        elif char == '╗':
            path_parts.append(f'M{x:.2f},{y:.2f}h{cw:.2f}v{ch:.2f}h-3.0v{-ch+3.0:.2f}h{-cw+3.0:.2f}v-3.0z')
        elif char == '╚':
            path_parts.append(f'M{x:.2f},{y:.2f}h3.0v{ch-3.0:.2f}h{cw-3.0:.2f}v3.0h{-cw:.2f}z')
        elif char == '╝':
            path_parts.append(f'M{x+cw-3.0:.2f},{y:.2f}h3.0v{ch:.2f}h{-cw:.2f}v-3.0h{cw-3.0:.2f}z')

title_vector_path = ' '.join(path_parts)

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 420" width="100%" height="100%">
  <defs>
    <!-- Background subtle grid pattern -->
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(0, 242, 255, 0.015)" stroke-width="1"/>
    </pattern>

    <!-- Color gradients matching the screenshot -->
    <linearGradient id="eye-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#b5179e">
        <animate attributeName="stop-color" values="#b5179e;#7209b7;#00f2ff;#00ffaa;#b5179e" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="50%" stop-color="#00f2ff">
        <animate attributeName="stop-color" values="#00f2ff;#00ffaa;#b5179e;#7209b7;#00f2ff" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="100%" stop-color="#7209b7">
        <animate attributeName="stop-color" values="#7209b7;#b5179e;#7209b7;#00f2ff;#7209b7" dur="8s" repeatCount="indefinite" />
      </stop>
    </linearGradient>

    <!-- UserSpaceOnUse maps the gradient from start coordinate x1=27 to end coordinate x2=453 -->
    <linearGradient id="glitch-grad" x1="27" y1="0" x2="453" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#b5179e">
        <animate attributeName="stop-color" values="#b5179e;#7209b7;#00f2ff;#00ffaa;#b5179e" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="50%" stop-color="#00f2ff">
        <animate attributeName="stop-color" values="#00f2ff;#00ffaa;#b5179e;#7209b7;#00f2ff" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="100%" stop-color="#7209b7">
        <animate attributeName="stop-color" values="#7209b7;#b5179e;#7209b7;#00f2ff;#7209b7" dur="8s" repeatCount="indefinite" />
      </stop>
    </linearGradient>

    <filter id="glow-cyan" x="-10%" y="-10%" width="120%" height="120%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <style>
    /* Terminal styling */
    .bg-terminal {{ fill: #07090e; }}
    .grid-bg {{ fill: url(#grid); }}
    .window-bg {{ fill: #0b0e14; }}
    .window-header {{ fill: #121824; }}
    
    /* Breathing / pulse animation for the centered eye */
    @keyframes pulse-eye {{
      0% {{ opacity: 0.85; }}
      50% {{ opacity: 1.0; }}
      100% {{ opacity: 0.85; }}
    }}

    @keyframes cursor-blink-anim {{
      0%, 49% {{ opacity: 1; }}
      50%, 100% {{ opacity: 0; }}
    }}

    .eye-group {{
      animation: pulse-eye 4s ease-in-out infinite;
    }}

    .cursor-blink {{
      animation: cursor-blink-anim 1s infinite;
    }}

    .term-text {{
      font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', Courier, monospace;
    }}

    /* Progress bar and text animation logic */
    .progress-stage {{
      opacity: 0;
      position: absolute;
    }}

    .status-text {{
      opacity: 0;
      position: absolute;
    }}

    .log-line {{
      opacity: 0;
      position: absolute;
    }}

    @keyframes stage-0 {{ 0%, 10% {{ opacity: 1; }} 10.1%, 100% {{ opacity: 0; }} }}
    @keyframes stage-1 {{ 10.1%, 35% {{ opacity: 1; }} 0%, 10%, 35.1%, 100% {{ opacity: 0; }} }}
    @keyframes stage-2 {{ 35.1%, 60% {{ opacity: 1; }} 0%, 35%, 60.1%, 100% {{ opacity: 0; }} }}
    @keyframes stage-3 {{ 60.1%, 85% {{ opacity: 1; }} 0%, 60%, 85.1%, 100% {{ opacity: 0; }} }}
    @keyframes stage-4 {{ 85.1%, 98% {{ opacity: 1; }} 0%, 85%, 98.1%, 100% {{ opacity: 0; }} }}

    /* Log lines stage appearance transitions */
    @keyframes stage-1-up {{ 0%, 10% {{ opacity: 0; }} 10.1%, 100% {{ opacity: 0.7; }} }}
    @keyframes stage-2-up {{ 0%, 35% {{ opacity: 0; }} 35.1%, 100% {{ opacity: 0.7; }} }}
    @keyframes stage-3-up {{ 0%, 60% {{ opacity: 0; }} 60.1%, 100% {{ opacity: 0.7; }} }}
    @keyframes stage-4-up {{ 0%, 85% {{ opacity: 0; }} 85.1%, 100% {{ opacity: 1; }} }}

    /* Status text animation timings */
    @keyframes status-0 {{ 0%, 35% {{ opacity: 0.8; }} 35.1%, 100% {{ opacity: 0; }} }}
    @keyframes status-1 {{ 35.1%, 85% {{ opacity: 0.8; }} 0%, 35%, 85.1%, 100% {{ opacity: 0; }} }}
    @keyframes status-2 {{ 85.1%, 98% {{ opacity: 1; }} 0%, 85%, 98.1%, 100% {{ opacity: 0; }} }}

    .p-0 {{ animation: stage-0 8s infinite; }}
    .p-1 {{ animation: stage-1 8s infinite; }}
    .p-2 {{ animation: stage-2 8s infinite; }}
    .p-3 {{ animation: stage-3 8s infinite; }}
    .p-4 {{ animation: stage-4 8s infinite; }}

    .p-1-up {{ animation: stage-1-up 8s infinite; }}
    .p-2-up {{ animation: stage-2-up 8s infinite; }}
    .p-3-up {{ animation: stage-3-up 8s infinite; }}
    .p-4-up {{ animation: stage-4-up 8s infinite; }}

    .s-0 {{ animation: status-0 8s infinite; }}
    .s-1 {{ animation: status-1 8s infinite; }}
    .s-2 {{ animation: status-2 8s infinite; }}
  </style>

  <!-- BACKGROUND -->
  <rect class="bg-terminal" width="100%" height="100%"/>
  <rect class="grid-bg" width="100%" height="100%"/>

  <!-- ==================== LEFT BRANDING PANEL ==================== -->
  <!-- CYBER EYE: MATHEMATICALLY CENTERED AND SCALED DOWN FOR BANNER HEIGHT -->
  <g class="eye-group" transform="translate({tx:.1f}, {ty:.1f}) scale({scale:.4f})" fill="url(#eye-grad)">
    {dots_xml_str}
  </g>

  <!-- TITLE ORACLE V3: PURE SVG VECTOR PATH (Font-independent, perfect on all devices/mobile) -->
  <g>
    <path d="{title_vector_path}" fill="url(#glitch-grad)" />
  </g>

  <!-- SUBTITLE -->
  <text x="240" y="380" class="term-text" font-size="12" fill="#ffffff" xml:space="preserve" text-anchor="middle" font-weight="bold" letter-spacing="1">
    Epic RPG Automation CLI
  </text>

  <!-- SPLIT COLUMN DASHED SEPARATOR -->
  <line x1="495" y1="20" x2="495" y2="400" stroke="rgba(255, 255, 255, 0.05)" stroke-width="1" stroke-dasharray="5 5" />

  <!-- ==================== RIGHT CLI TERMINAL WINDOW PANEL ==================== -->
  <g>
    <!-- Terminal Shell Frame -->
    <rect x="510" y="25" width="460" height="370" class="window-bg" stroke="#00f2ff" stroke-width="1.5" rx="4" filter="url(#glow-cyan)" />
    
    <!-- Window Header -->
    <path d="M 511,26 L 969,26 L 969,50 L 511,50 Z" class="window-header" />
    <line x1="510" y1="50" x2="970" y2="50" stroke="#00f2ff" stroke-width="1" />
    <!-- Window Header Control Buttons -->
    <circle cx="525" cy="38" r="3" fill="#ff5f56" />
    <circle cx="535" cy="38" r="3" fill="#ffbd2e" />
    <circle cx="545" cy="38" r="3" fill="#27c93f" />
    <!-- Window Header Label -->
    <text x="560" y="42" class="term-text" fill="rgba(255,255,255,0.7)" font-size="10" font-weight="bold">oracle_v3_session.sh</text>

    <!-- Simulated TUI Boot logs -->
    <g transform="translate(535, 75)">
      <text x="0" y="10" class="term-text" font-size="11" fill="#ffffff" opacity="0.7">[SYS] Initializing Oracle V3...</text>
      <text x="0" y="32" class="term-text log-line p-1-up" font-size="11" fill="#ffffff">[SYS] Loading TFLite CNN model... ok</text>
      <text x="0" y="54" class="term-text log-line p-2-up" font-size="11" fill="#ffffff">[SYS] Connecting to Discord gateway...</text>
      <text x="0" y="76" class="term-text log-line p-3-up" font-size="11" fill="#ffffff">[SYS] Authenticating gateway session... ok</text>
      <text x="0" y="98" class="term-text log-line p-4-up" font-size="11" fill="#00ffaa" font-weight="bold">[SYS] Connection established: ONLINE</text>
    </g>

    <!-- Vector progress bar group -->
    <g transform="translate(550, 215)">
      <!-- Left Border -->
      <text x="0" y="15" class="term-text" font-size="15" fill="#3f4e5a">│</text>
      
      <!-- Progress Bar Track -->
      <rect x="18" y="1" width="310" height="17" fill="#141923" rx="2" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
      
      <!-- Progress Bar Fill (Discrete width jumps to match percentage updates) -->
      <rect x="20" y="3" height="13" fill="#00ffaa" rx="1">
        <animate attributeName="width" 
                 values="0;87;167;254;306;306" 
                 keyTimes="0;0.101;0.351;0.601;0.851;1"
                 calcMode="discrete" 
                 dur="8s" 
                 repeatCount="indefinite" />
      </rect>
      
      <!-- Right Border -->
      <text x="338" y="15" class="term-text" font-size="15" fill="#3f4e5a">│</text>
      
      <!-- Percentage texts (matching progress stages) -->
      <g transform="translate(355, 15)">
        <text x="0" y="0" class="term-text progress-stage p-0" font-size="14" fill="#00ffaa" font-weight="bold">0%</text>
        <text x="0" y="0" class="term-text progress-stage p-1" font-size="14" fill="#00ffaa" font-weight="bold">28%</text>
        <text x="0" y="0" class="term-text progress-stage p-2" font-size="14" fill="#00ffaa" font-weight="bold">54%</text>
        <text x="0" y="0" class="term-text progress-stage p-3" font-size="14" fill="#00ffaa" font-weight="bold">82%</text>
        <text x="0" y="0" class="term-text progress-stage p-4" font-size="14" fill="#00ffaa" font-weight="bold">100%</text>
      </g>
    </g>

    <!-- Connecting status messages -->
    <g transform="translate(740, 275)">
      <text x="0" y="0" class="term-text status-text s-0" font-size="12" fill="#ffffff" opacity="0.8" xml:space="preserve" text-anchor="middle">Connecting...</text>
      <text x="0" y="0" class="term-text status-text s-1" font-size="12" fill="#ffffff" opacity="0.8" xml:space="preserve" text-anchor="middle">Authenticating gateway session...</text>
      <text x="0" y="0" class="term-text status-text s-2" font-size="12" fill="#00ffaa" opacity="1" xml:space="preserve" text-anchor="middle" font-weight="bold">Connection established: ONLINE</text>
    </g>

    <!-- Typing bar separator -->
    <line x1="510" y1="340" x2="970" y2="340" stroke="#00f2ff" stroke-width="1" opacity="0.25" />

    <!-- CLI Input Command typing simulation -->
    <g transform="translate(530, 368)">
      <text x="0" y="0" class="term-text" font-size="11" fill="rgba(255, 255, 255, 0.45)" text-anchor="start">
        OracleCLI | <tspan fill="#00ffaa">type /help for commands...</tspan>
      </text>
      <!-- Blinking Cursor -->
      <text x="234" y="0" class="term-text cursor-blink" font-size="11" fill="#00ffaa">█</text>
    </g>
  </g>
</svg>
"""

with open(banner_out_path, 'w', encoding='utf-8') as out_f:
    out_f.write(svg_content)

print("Generated vector banner.svg successfully.")
