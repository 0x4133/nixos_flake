    let
      pkgs = import <nixpkgs> {};
      python = pkgs.python3.withPackages (python-pkgs: with python-pkgs; [
        numpy pyserial laspy
        # Add other Python packages here as needed, e.g., pandas, matplotlib
      ]);
    in
    pkgs.mkShell {
      packages = [
        python
      ];
  
    }