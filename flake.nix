{
  description = "Scarb package manager for Cairo/Starknet development";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};

      # Safely read versions file with fallback
      versions = let
        versionsFile = ./versions/versions.json;
        fallbackVersion = {
          "2.8.2" = {
            hashes = {
              "aarch64-apple-darwin" = "59d041fca5404b0c60e0e1ff22e9d1929b118c9914ba80c012cac7c372168e2c";
              "x86_64-apple-darwin" = "209979076e65ba3e0d53506cab826516a647f44c0d77fc4be221fea5bcb6607e";
              "aarch64-unknown-linux-gnu" = "c4e0066b00af0e644585f4c27ecea55abed732679b7e8654876303bae982e2f6";
              "x86_64-unknown-linux-gnu" = "2033173c4b8e72fd4bf1779baca6d5348d4f0b53327a14742cb2f65c2f0e892c";
              "aarch64-unknown-linux-musl" = "35bb6f035691fe71faf5836b8e90d05671f4407a14758e31658fd5c7e97d2a08";
              "x86_64-unknown-linux-musl" = "b8c99d5f917880f4416e443abfaeab9eb2af7b8d34d34a84e5c913b0e8149d22";
              "x86_64-pc-windows-msvc" = "ef9161f4305c4ac3262810fb0e888835a00204b98dd185ec07d2cc4e3e9c0330";
            };
            metadata = {
              releaseDate = "2024-01-05T15:30:00Z";
              prerelease = false;
              draft = false;
            };
          };
        };
      in
        if builtins.pathExists versionsFile
        then builtins.fromJSON (builtins.readFile versionsFile)
        else fallbackVersion;

      # Get stable versions (non-prerelease, non-draft)
      stableVersions =
        pkgs.lib.filterAttrs
        (version: data: !(data.metadata.prerelease || data.metadata.draft))
        versions;

      # Get latest stable version
      latestStableVersion = builtins.head (
        builtins.sort
        (a: b: builtins.compareVersions a b > 0)
        (builtins.attrNames stableVersions)
      );

      # Get latest version including prereleases
      latestVersion = builtins.head (
        builtins.sort
        (a: b: builtins.compareVersions a b > 0)
        (builtins.attrNames versions)
      );

      # Common scarb builder function
      mkScarb = versionStr: let
        versionData = versions.${versionStr} or (throw "Version ${versionStr} not found");

        # System mapping
        systemMap = {
          "aarch64-darwin" = "aarch64-apple-darwin";
          "x86_64-darwin" = "x86_64-apple-darwin";
          "aarch64-linux" = "aarch64-unknown-linux-gnu";
          "x86_64-linux" = "x86_64-unknown-linux-gnu";
          "aarch64-linux-musl" = "aarch64-unknown-linux-musl";
          "x86_64-linux-musl" = "x86_64-unknown-linux-musl";
          "x86_64-windows" = "x86_64-pc-windows-msvc";
        };

        platform = systemMap.${system} or (throw "Unsupported system: ${system}");
        extension =
          if platform == "x86_64-pc-windows-msvc"
          then "zip"
          else "tar.gz";
        sha256 = versionData.hashes.${platform} or (throw "Hash not found for ${platform} in version ${versionStr}");
      in
        pkgs.stdenv.mkDerivation {
          pname = "scarb";
          version = versionStr;

          src = pkgs.fetchurl {
            url = "https://github.com/software-mansion/scarb/releases/download/v${versionStr}/scarb-v${versionStr}-${platform}.${extension}";
            inherit sha256;
          };

          nativeBuildInputs = with pkgs;
            [
              gnutar
              gzip
            ]
            ++ pkgs.lib.optionals (extension == "zip") [
              unzip
            ];

          installPhase = ''
            mkdir -p $out/{bin,doc}

            ${
              if extension == "zip"
              then ''
                unzip $src
                cd scarb-v${versionStr}-${platform}
              ''
              else ''
                tar xf $src
                cd scarb-v${versionStr}-${platform}
              ''
            }

            mv bin/* $out/bin/
            mv doc/* $out/doc/
            chmod +x $out/bin/*

            # Verify installation
            required_bins=(
              scarb
              scarb-cairo-language-server
              scarb-cairo-run
              scarb-cairo-test
              scarb-doc
              # scarb-snforge-test-collector
            )

            for bin in "''${required_bins[@]}"; do
              if [ ! -x "$out/bin/$bin" ]; then
                echo "Error: Required binary $bin not found or not executable"
                exit 1
              fi
            done

            # Create version info file
            mkdir -p $out/share/scarb
            cat > $out/share/scarb/version-info.json << EOF
            ${builtins.toJSON {
              inherit versionStr;
              inherit (versionData.metadata) releaseDate prerelease;
              buildSystem = system;
              buildPlatform = platform;
            }}
            EOF
          '';

          meta = with pkgs.lib; {
            description = "Scarb package manager for Cairo/Starknet development";
            homepage = "https://github.com/software-mansion/scarb";
            license = licenses.mit;
            platforms = builtins.attrNames systemMap;
            maintainers = with maintainers; [
              /*
              add yourself here
              */
            ];
            inherit (versionData.metadata) changelog;
          };
        };
    in {
      # Expose all versions with additional convenience attributes
      packages = let
        versionStrings = builtins.attrNames versions;
        versionPackages = builtins.listToAttrs (
          map
          (ver: {
            name = ver;
            value = mkScarb ver;
          })
          versionStrings
        );
      in
        versionPackages
        // {
          default = mkScarb latestStableVersion;
          latest = mkScarb latestVersion;
          latest-stable = mkScarb latestStableVersion;
        };

      # Development shell with update script dependencies
      devShells.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python3
          python3Packages.requests
          alejandra
        ];
      };

      # System info
      lib = {
        inherit versions stableVersions;
        inherit latestVersion latestStableVersion;
      };
    });
}
