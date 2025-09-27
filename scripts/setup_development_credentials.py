#!/usr/bin/env python3
"""
Development Credential Setup Script

Sets up secure local development credentials for env-agents.
Creates symlinks from config/ to credentials/ directory to keep
actual API keys outside Git tracking while maintaining functionality.
"""

import os
import sys
from pathlib import Path
import shutil

def setup_development_credentials():
    """Set up secure development credential system"""

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    config_dir = project_root / "config"
    credentials_dir = project_root / "credentials"
    templates_dir = config_dir / "templates"

    print("🔧 Setting up development credentials for env-agents...")
    print(f"Project root: {project_root}")

    # Ensure directories exist
    credentials_dir.mkdir(exist_ok=True)

    # Check for existing credentials
    credential_files = [
        ("credentials.yaml", "credentials.yaml.backup"),
        ("ecognita-470619-e9e223ea70a7.json", "ecognita-470619-e9e223ea70a7.json")
    ]

    # Check current setup
    config_creds = config_dir / "credentials.yaml"
    backup_creds = credentials_dir / "credentials.yaml.backup"

    if config_creds.exists() and config_creds.is_symlink():
        print("✅ Development credentials already set up")
        print("📊 Current status:")

        # Show current credential status
        for config_file, backup_file in credential_files:
            config_path = config_dir / config_file
            backup_path = credentials_dir / backup_file

            if config_path.exists():
                if config_path.is_symlink():
                    target = config_path.resolve()
                    print(f"  - {config_file}: ✅ Symlinked to {target}")
                else:
                    print(f"  - {config_file}: ⚠️  Regular file (not symlinked)")
            else:
                print(f"  - {config_file}: ❌ Missing")

                if backup_path.exists():
                    print(f"    - Backup available at {backup_path}")

        return

    if backup_creds.exists():
        print("✅ Found existing credential backup")

        # Create symlinks
        print("🔗 Creating secure symlinks...")
        for config_file, backup_file in credential_files:
            config_path = config_dir / config_file
            backup_path = credentials_dir / backup_file

            if backup_path.exists():
                # Remove existing file/symlink if present
                if config_path.exists():
                    config_path.unlink()

                # Create relative symlink
                relative_path = Path("..") / "credentials" / backup_file
                config_path.symlink_to(relative_path)
                print(f"  - Created {config_file} -> {relative_path}")
            else:
                print(f"  - Skipped {config_file} (no backup found)")

    else:
        print("📋 No existing credentials found")
        print("🔧 Setting up fresh credential system...")

        # Copy template to credentials directory
        template_file = templates_dir / "credentials.yaml.template"
        if template_file.exists():
            new_creds = credentials_dir / "credentials.yaml"
            shutil.copy2(template_file, new_creds)

            # Create symlink
            relative_path = Path("..") / "credentials" / "credentials.yaml"
            config_creds.symlink_to(relative_path)

            print(f"✅ Created {new_creds}")
            print(f"🔗 Symlinked config/credentials.yaml -> {relative_path}")
            print("📝 Please edit credentials/credentials.yaml with your API keys")
        else:
            print(f"❌ Template not found: {template_file}")
            return

    # Verify setup
    print("\n🧪 Verifying setup...")

    try:
        import yaml
        if config_creds.exists():
            with open(config_creds) as f:
                creds = yaml.safe_load(f)
            print(f"✅ Credentials loaded successfully ({len(creds)} services)")
        else:
            print("❌ Credentials file not accessible")
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")

    # Check Git status
    print("\n🛡️  Security check...")
    os.chdir(project_root)
    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "config/credentials.yaml", "config/ecognita-*.json"],
            capture_output=True, text=True
        )

        if result.stdout.strip():
            print("⚠️  WARNING: Credential files detected in Git staging area!")
            print(result.stdout)
        else:
            print("✅ Credential files properly ignored by Git")

    except Exception as e:
        print(f"⚠️  Could not check Git status: {e}")

    print("\n🎉 Development credentials setup complete!")
    print("\n📚 Next steps:")
    print("1. Edit credentials/credentials.yaml with your API keys")
    print("2. See docs/CREDENTIALS.md for where to get API keys")
    print("3. Run tests with: python run_tests.py")
    print("4. Your credentials are safely outside Git tracking")

if __name__ == "__main__":
    setup_development_credentials()