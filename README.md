# Scarb Nix Flake

This repository provides Nix flake packages for [Scarb](https://github.com/software-mansion/scarb), the package manager for Cairo/Starknet development.

## Features

- Automated version tracking and updates
- Support for all platforms (Linux, macOS, Windows)
- Pre-release and stable version management
- Secure checksums verification
- Rich metadata and changelog information

## Quick Start

Add this flake to your `flake.nix`:

```nix
{
  inputs.scarb-nix.url = "github:jbcaron/scarb-nix";
  
  outputs = { self, nixpkgs, scarb-nix }: {
    # Use latest stable version (recommended)
    packages.x86_64-linux.default = scarb-nix.packages.x86_64-linux.default;
  };
}
```

## Installation Methods

### Latest Stable Version

```nix
scarb-nix.packages.${system}.default
# or
scarb-nix.packages.${system}.latest-stable
```

### Latest Version (including pre-releases)

```nix
scarb-nix.packages.${system}.latest
```

### Specific Stable Version

```nix
scarb-nix.packages.${system}.stable."2.8.2"
```

### Specific Version (including pre-releases)

```nix
scarb-nix.packages.${system}."2.8.2"
```

## Development Shell Example

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    scarb-nix.url = "github:your-username/scarb-nix";
  };

  outputs = { self, nixpkgs, scarb-nix }:
    let
      system = "x86_64-linux";  # or "aarch64-darwin", etc.
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          scarb-nix.packages.${system}.default
        ];
      };
    };
}
```

## Supported Systems

- aarch64-darwin (Apple Silicon)
- x86_64-darwin (Intel Mac)
- aarch64-linux (ARM Linux)
- x86_64-linux (Intel/AMD Linux)
- x86_64-windows (Windows)

## Version Information

Each package includes detailed version information in `/share/scarb/version-info.json`:

```json
{
  "version": "2.8.2",
  "releaseDate": "2024-01-05T15:30:00Z",
  "prerelease": false,
  "buildSystem": "x86_64-linux",
  "buildPlatform": "x86_64-unknown-linux-gnu"
}
```

## Maintaining the Repository

### Updating Versions

1. Enter the development shell:
```bash
nix develop
```

2. Run the update script:
```bash
python scripts/update-versions.py
```

The script will:
- Fetch all releases from GitHub
- Download and verify checksums
- Update version metadata
- Create a backup of the previous versions file
- Generate an update log

### Manual Version Addition

If needed, you can manually add versions by editing `versions/versions.json`:

```json
{
  "2.8.2": {
    "hashes": {
      "aarch64-apple-darwin": "hash...",
      "x86_64-apple-darwin": "hash..."
    },
    "metadata": {
      "releaseDate": "2024-01-05T15:30:00Z",
      "prerelease": false,
      "draft": false,
      "changelog": "## What's Changed\n* Changes description..."
    }
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the update script to verify everything works
5. Submit a pull request

## License

This repository is licensed under the MIT License. However, Scarb itself has its own license terms that you should review.

## Acknowledgments

- [Software Mansion](https://github.com/software-mansion) for creating Scarb
- The Nix community for the packaging infrastructure