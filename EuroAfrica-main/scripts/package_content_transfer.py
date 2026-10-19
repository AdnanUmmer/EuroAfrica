"""Create a private, portable UTF-8 content/media archive; never include .env or users."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New .zip path; existing archives are never overwritten.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = Path(args.output).resolve()
    if output.suffix.lower() != '.zip' or output.exists() or output.with_suffix('.zip.sha256').exists():
        parser.error('Use a new .zip filename.')
    if not output.parent.is_dir():
        parser.error('Output parent directory must already exist.')
    with tempfile.TemporaryDirectory(prefix='euroafrica-transfer-') as temporary:
        stage = Path(temporary)
        subprocess.run([sys.executable, '-X', 'utf8', str(root/'manage.py'), 'transfer_content',
                        'export', '--output', str(stage/'package')], cwd=root, check=True)
        data = json.loads((stage/'package/content.json').read_text(encoding='utf-8'))
        summary = {'package_sha256': data['package_sha256'], 'created_at': data['created_at'],
                   'counts': {name: len(rows) for name, rows in data['records'].items()},
                   'media_files': len(data['media']), 'media_bytes': sum(f['bytes'] for f in data['media'].values()),
                   'excluded': data['excluded']}
        with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((stage/'package').rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
            for name in ('trade/content_transfer.py', 'trade/management/commands/transfer_content.py',
                         'trade/test_content_transfer.py', 'scripts/package_content_transfer.py'):
                archive.write(root/name, 'tooling/'+name)
            archive.write(root/'CONTENT_TRANSFER.md', 'CONTENT_TRANSFER.md')
            archive.writestr('package-summary.json', json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n', encoding='ascii')
    print(f'Created archive with {sum(summary["counts"].values())} editorial records and {summary["media_files"]} media files.')
    print('Keep the archive private. It contains editorial content, but no database credentials or user accounts.')


if __name__ == '__main__':
    main()
