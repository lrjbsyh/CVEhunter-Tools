import sys
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
ICON_ICO = ASSETS / 'icon.ico'
DIST_DIR = ROOT / 'CVEhunter_V1.0'


def ensure_assets():
    ASSETS.mkdir(exist_ok=True)
    return


def build_exe():
    DIST_DIR.mkdir(exist_ok=True)
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean',
        '--workpath', str(ROOT / 'build'),
        '--distpath', str(DIST_DIR),
        '--name', 'CVEhunter',
        '--add-data', f"templates;templates",
        '--add-data', f"prompts;prompts",
        '--add-data', f"assets;assets",
        '--add-data', f"data;data",
    ]
    if ICON_ICO.exists():
        cmd += ['--icon', str(ICON_ICO)]
    else:
        print('[WARN] 未找到 icon.ico，exe 将使用默认图标')
    cmd.append(str(ROOT / 'run_app.py'))
    print('[RUN]', ' '.join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


if __name__ == '__main__':
    ensure_assets()
    build_exe()
    print(f'\n[DONE] 发行目录: {DIST_DIR}')
