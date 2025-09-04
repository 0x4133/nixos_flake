{ pkgs ? import <nixpkgs> {} }:
(pkgs.buildFHSEnv {
  name = "tkinter test";
  targetPkgs = pkgs: (with pkgs; [
    python310
    python310Packages.pip
    python310Packages.tkinter
    tk
  ]);
  runScript = "bash";
}).env