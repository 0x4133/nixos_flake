{

  description = "A very basic flake";

  inputs = { 
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    yabridge-nix.url = "github:robbert-vdh/yabridge-nix";
  };

  outputs = { nixpkgs, yabridge-nix,  ...} @ inputs: 

   {
   nixosConfigurations.nixos = nixpkgs.lib.nixosSystem {
    specialArgs = { inherit inputs; };
   	modules = [
   	    ./configuration.nix	
   	];
   };

  };
}
