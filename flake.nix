{
  description = "A very basic flake (nixos-unstable)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }:
  let
    # Change if you're on a different arch:
    system = "x86_64-linux";
  in {
    nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
      inherit system;
      specialArgs = { inherit nixpkgs self; }; # plus anything else you want to pass
      modules = [
        ./configuration.nix
      ];
    };
  };
}
