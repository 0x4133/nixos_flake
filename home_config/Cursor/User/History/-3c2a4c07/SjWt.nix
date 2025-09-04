{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    (python3.withPackages (ps: [ ps.numpy ps.matplotlib ps.pyserial]))
  ];
}