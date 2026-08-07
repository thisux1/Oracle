import os

files = [
    '/home/thiago/Documentos/codesnippets/discbot/Oracle-V2/README.md',
    '/home/thiago/Documentos/codesnippets/discbot/Oracle-V2/docs/README.pt-BR.md'
]

old_divider = '───────────────────────────────────────── ▪ ─────────────────────────────────────────'
new_divider = '─────── ▪ ───────'

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        count = content.count(old_divider)
        if count > 0:
            content = content.replace(old_divider, new_divider)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {os.path.basename(file_path)}: replaced {count} occurrences of divider.")
        else:
            print(f"No dividers found in {os.path.basename(file_path)}.")
    else:
        print(f"File not found: {file_path}")
