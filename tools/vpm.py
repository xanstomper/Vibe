#!/usr/bin/env python3
"""
Vibe Package Manager (vpm)

Package management for the Vibe programming language
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Package:
    """Package information"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    repository: str = ""
    dependencies: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'repository': self.repository,
            'dependencies': self.dependencies,
            'keywords': self.keywords,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Package':
        """Create from dictionary"""
        return cls(
            name=data.get('name', ''),
            version=data.get('version', ''),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', ''),
            repository=data.get('repository', ''),
            dependencies=data.get('dependencies', []),
            keywords=data.get('keywords', []),
        )


@dataclass
class ProjectConfig:
    """Project configuration"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'dependencies': self.dependencies,
            'dev_dependencies': self.dev_dependencies,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create from dictionary"""
        return cls(
            name=data.get('name', ''),
            version=data.get('version', ''),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', ''),
            dependencies=data.get('dependencies', []),
            dev_dependencies=data.get('dev_dependencies', []),
        )


class VibePackageManager:
    """Vibe package manager"""
    
    # Package registry (simplified - in production this would be a remote registry)
    REGISTRY_URL = "https://packages.vibe-lang.org"
    LOCAL_REGISTRY = Path.home() / ".vibe" / "packages"
    CACHE_DIR = Path.home() / ".vibe" / "cache"
    
    def __init__(self):
        self.ensure_directories()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        self.LOCAL_REGISTRY.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_project_config(self) -> Optional[ProjectConfig]:
        """Load project configuration from vibe.json"""
        config_file = Path("vibe.json")
        
        if not config_file.exists():
            return None
        
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        return ProjectConfig.from_dict(data)
    
    def save_project_config(self, config: ProjectConfig):
        """Save project configuration to vibe.json"""
        with open('vibe.json', 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
    
    def init(self, name: str = None, version: str = "0.1.0"):
        """Initialize a new project"""
        if Path("vibe.json").exists():
            print("Error: vibe.json already exists")
            return False
        
        if name is None:
            name = Path.cwd().name
        
        config = ProjectConfig(
            name=name,
            version=version,
            description=f"A new Vibe project: {name}",
            author=os.getenv('USER', 'unknown'),
        )
        
        self.save_project_config(config)
        
        # Create basic project structure
        Path("src").mkdir(exist_ok=True)
        Path("tests").mkdir(exist_ok=True)
        
        # Create main.vibe
        main_file = Path("src/main.vibe")
        if not main_file.exists():
            with open(main_file, 'w') as f:
                f.write(f"""module {name}

intent:
    Main application entry point

import std.io

proc main() -> int:
    std.io.println("Hello from {name}!")
    return 0
""")
        
        print(f"Initialized project: {name}")
        return True
    
    def install(self, package_name: str, version: str = None):
        """Install a package"""
        config = self.load_project_config()
        
        if config is None:
            print("Error: Not in a Vibe project directory")
            return False
        
        # Check if already installed
        if package_name in config.dependencies:
            print(f"Package {package_name} is already installed")
            return True
        
        # In a real implementation, this would:
        # 1. Fetch package metadata from registry
        # 2. Download package
        # 3. Extract to local registry
        # 4. Update vibe.json
        
        print(f"Installing {package_name}...")
        
        # Simulate installation
        package = Package(
            name=package_name,
            version=version or "latest",
            description=f"Package {package_name}",
        )
        
        # Add to dependencies
        config.dependencies.append(f"{package_name}@{package.version}")
        self.save_project_config(config)
        
        # Create package directory
        package_dir = self.LOCAL_REGISTRY / package_name
        package_dir.mkdir(exist_ok=True)
        
        # Write package metadata
        with open(package_dir / "package.json", 'w') as f:
            json.dump(package.to_dict(), f, indent=2)
        
        print(f"Installed {package_name}@{package.version}")
        return True
    
    def uninstall(self, package_name: str):
        """Uninstall a package"""
        config = self.load_project_config()
        
        if config is None:
            print("Error: Not in a Vibe project directory")
            return False
        
        # Remove from dependencies
        config.dependencies = [
            dep for dep in config.dependencies
            if not dep.startswith(package_name)
        ]
        self.save_project_config(config)
        
        # Remove package directory
        package_dir = self.LOCAL_REGISTRY / package_name
        if package_dir.exists():
            import shutil
            shutil.rmtree(package_dir)
        
        print(f"Uninstalled {package_name}")
        return True
    
    def update(self, package_name: str = None):
        """Update packages"""
        config = self.load_project_config()
        
        if config is None:
            print("Error: Not in a Vibe project directory")
            return False
        
        if package_name:
            # Update specific package
            print(f"Updating {package_name}...")
            # In real implementation, fetch latest version
        else:
            # Update all packages
            print("Updating all packages...")
            for dep in config.dependencies:
                name = dep.split('@')[0]
                print(f"  Updating {name}...")
        
        return True
    
    def search(self, query: str):
        """Search for packages"""
        print(f"Searching for '{query}'...")
        
        # In real implementation, this would query the registry
        # For now, return some example packages
        packages = [
            ("web", "0.1.0", "Web framework for Vibe"),
            ("http", "1.0.0", "HTTP client and server"),
            ("json", "0.5.0", "JSON parsing and generation"),
            ("sqlite", "0.3.0", "SQLite database bindings"),
            ("test", "1.0.0", "Testing framework"),
            ("assert", "0.1.0", "Assertion library"),
            ("math", "1.0.0", "Mathematical functions"),
            ("random", "0.2.0", "Random number generation"),
            ("crypto", "0.1.0", "Cryptographic functions"),
            ("io", "1.0.0", "Input/output operations"),
        ]
        
        results = [
            (name, version, desc)
            for name, version, desc in packages
            if query.lower() in name.lower() or query.lower() in desc.lower()
        ]
        
        if results:
            print(f"\nFound {len(results)} packages:\n")
            for name, version, desc in results:
                print(f"  {name}@{version} - {desc}")
        else:
            print(f"\nNo packages found for '{query}'")
        
        return results
    
    def list_installed(self):
        """List installed packages"""
        config = self.load_project_config()
        
        if config is None:
            print("Error: Not in a Vibe project directory")
            return False
        
        if not config.dependencies:
            print("No dependencies installed")
            return True
        
        print("\nInstalled packages:\n")
        for dep in config.dependencies:
            name, version = dep.split('@') if '@' in dep else (dep, 'latest')
            print(f"  {name}@{version}")
        
        return True
    
    def publish(self, package_name: str = None):
        """Publish a package to the registry"""
        config = self.load_project_config()
        
        if config is None:
            print("Error: Not in a Vibe project directory")
            return False
        
        if package_name is None:
            package_name = config.name
        
        print(f"Publishing {package_name}@{config.version}...")
        
        # In real implementation, this would:
        # 1. Build package
        # 2. Create archive
        # 3. Upload to registry
        
        print(f"Published {package_name}@{config.version}")
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Vibe Package Manager (vpm)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vpm init                          # Initialize new project
  vpm install sqlite                # Install package
  vpm install sqlite@0.3.0          # Install specific version
  vpm uninstall sqlite              # Uninstall package
  vpm update                        # Update all packages
  vpm update sqlite                 # Update specific package
  vpm search "http server"          # Search for packages
  vpm list                          # List installed packages
  vpm publish                       # Publish package
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # init
    init_parser = subparsers.add_parser('init', help='Initialize new project')
    init_parser.add_argument('--name', help='Project name')
    init_parser.add_argument('--version', default='0.1.0', help='Initial version')
    
    # install
    install_parser = subparsers.add_parser('install', help='Install package')
    install_parser.add_argument('package', help='Package name')
    install_parser.add_argument('--version', help='Package version')
    
    # uninstall
    uninstall_parser = subparsers.add_parser('uninstall', help='Uninstall package')
    uninstall_parser.add_argument('package', help='Package name')
    
    # update
    update_parser = subparsers.add_parser('update', help='Update packages')
    update_parser.add_argument('package', nargs='?', help='Package name (optional)')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search for packages')
    search_parser.add_argument('query', help='Search query')
    
    # list
    subparsers.add_parser('list', help='List installed packages')
    
    # publish
    publish_parser = subparsers.add_parser('publish', help='Publish package')
    publish_parser.add_argument('package', nargs='?', help='Package name')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    pm = VibePackageManager()
    
    if args.command == 'init':
        pm.init(args.name, args.version)
    
    elif args.command == 'install':
        pm.install(args.package, args.version)
    
    elif args.command == 'uninstall':
        pm.uninstall(args.package)
    
    elif args.command == 'update':
        pm.update(args.package)
    
    elif args.command == 'search':
        pm.search(args.query)
    
    elif args.command == 'list':
        pm.list_installed()
    
    elif args.command == 'publish':
        pm.publish(args.package)


if __name__ == '__main__':
    main()
