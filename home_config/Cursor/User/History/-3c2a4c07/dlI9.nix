    { pkgs ? import <nixpkgs> {} }:

    pkgs.mkShell {
      buildInputs = [
        pkgs.python311 # Or your desired Python version
        pkgs.python311Packages.numpy
        # Add other Python packages as needed, e.g., pkgs.python311Packages.pandas
      ];
      # You may need to add additional libraries for some packages to work correctly,
      # for example, for certain binary dependencies:
      # LD_LIBRARY_PATH = "${pkgs.libGL}/lib/:${pkgs.stdenv.cc.cc.lib}/lib/";
    }