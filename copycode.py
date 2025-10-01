import os
import pyperclip

def collect_code(directory, extensions=(".css", ".js", ".html", ".py",".md")):
    collected = []
    for root, dirs, files in os.walk(directory):
        # optional: skip unnecessary folders
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "venv", ".venv", "node_modules")]
        
        for file in files:
            if file.endswith(extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    collected.append(f"--- {path} ---\n{content}\n")
                except Exception as e:
                    print(f"⚠️ Skipping {path}: {e}")
    return "\n".join(collected)

if __name__ == "__main__":
    # auto-detect current directory where script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"🔍 Scanning directory: {current_dir}")

    big_string = collect_code(current_dir)

    pyperclip.copy(big_string)

    print("✅ All collected code has been copied to your clipboard.")
    print(f"📦 Total length: {len(big_string)} characters")
