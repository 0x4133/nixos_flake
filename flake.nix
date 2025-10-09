# flake.nix
{
  description = "A very basic flake (nixos-unstable) with winapps";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    # Add winapps and make it follow our nixpkgs
    winapps = {
      url = "github:winapps-org/winapps";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, winapps, ... }:
  let
    # Change if you're on a different arch:
    system = "x86_64-linux";
  in {
    nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit nixpkgs self; };

      modules = [
        ./configuration.nix

        # Add winapps packages to your system
        ({ pkgs, ... }: {
          environment.systemPackages = [
            winapps.packages.${system}.winapps
            winapps.packages.${system}.winapps-launcher # optional
          ];
        })
      ];
    };
  };
}
