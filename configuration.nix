## Edit this configuration file to define what should be installed on
# your system.  Help is available in the configuration.nix(5) man page
# and in the NixOS manual (accessible by running ‘nixos-help’).
##
{ config, pkgs, inputs, ... }:

{
  # Enable OpenGL
  hardware.graphics = {
    enable = true;
  };

  virtualisation.docker.enable = true;

  # Load nvidia driver for Xorg and Wayland
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    modesetting.enable = true;
    powerManagement.enable = false;
    powerManagement.finegrained = false;
    open = false;
    nvidiaSettings = true;
    package = config.boot.kernelPackages.nvidiaPackages.production;
  };

  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  imports = [
    /etc/nixos/hardware-configuration.nix
  ];

  # Bootloader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.hostName = "nixos";
  networking.networkmanager.enable = true;

  time.timeZone = "America/Phoenix";

  i18n.defaultLocale = "en_US.UTF-8";
  i18n.extraLocaleSettings = {
    LC_ADDRESS = "en_US.UTF-8";
    LC_IDENTIFICATION = "en_US.UTF-8";
    LC_MEASUREMENT = "en_US.UTF-8";
    LC_MONETARY = "en_US.UTF-8";
    LC_NAME = "en_US.UTF-8";
    LC_NUMERIC = "en_US.UTF-8";
    LC_PAPER = "en_US.UTF-8";
    LC_TELEPHONE = "en_US.UTF-8";
    LC_TIME = "en_US.UTF-8";
  };

  # X11 + GNOME (use new option names to silence deprecations)
  services.xserver.enable = true;
  services.displayManager.gdm.enable = true;
  services.desktopManager.gnome.enable = true;

  services.xserver.xkb = {
    layout = "us";
    variant = "";
  };

  services.printing.enable = true;

  # PipeWire
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    # jack.enable = true;  # uncomment if needed
  };

  services.ollama = {
    enable = true;
    host = "0.0.0.0";
    openFirewall = true;
    loadModels = [ "gpt-oss" ];
  };

  # SDR udev & groups
  services.udev.packages = [ pkgs.hackrf ];
  users.groups.plugdev = { };

  programs.obs-studio = {
    enable = true;
    package = (pkgs.obs-studio.override { cudaSupport = true; });
    plugins = with pkgs.obs-studio-plugins; [
      wlrobs
      obs-backgroundremoval
      obs-pipewire-audio-capture
      # obs-vaapi
      obs-gstreamer
      obs-vkcapture
    ];
  };

  users.users.aaron = {
    isNormalUser = true;
    description = "aaron";
    extraGroups = [ "networkmanager" "wheel" "plugdev" "dialout" "docker" "incus-admin" ];
    packages = with pkgs; [
      tesseract
      poppler_utils
      clipse
      slurp
      grim
      fish
      kitty
      wofi
      firefox
      yt-dlp
      waypaper
      swaybg
      bash
      micro
      fastfetch
      google-chrome
      spotify
      git
      tealdeer
      xclip
      bat
      ani-cli
      mpv
      discord
      ffmpeg
      fzf
      go
      code-cursor
      nodejs_24

      # Minimal, GUI-free system Python for the user:
      (python311.withPackages (ps: with ps; [ numpy pip ]))

      system76-keyboard-configurator
      wl-clipboard
      gruppled-white-cursors
      claude-code
      zbar
      gnuradio
      gnuradioPackages.lora_sdr
      gnuradioPackages.bladeRF
      quartus-prime-lite
      cmake
      screen
      gnuradioPackages.osmosdr
      hackrf
      libbladeRF
      gephi
      nmap
      conda
      gnumake
      ollama
      (pkgs.ollama.override { acceleration = "cuda"; })
      asciinema
      asciinema-agg
      arduino-ide
      transmission
      obsidian
      git-credential-manager
      lmms
      libusb1
      yt-dlp
      imagemagick
      usbutils
      gqrx
      hackrf
      sdrangel
      qgis
      ubertooth
      timg
      bloodhound
      neo4j
      openjdk17
      maltego
      pavucontrol
      kismet
      wireshark
      ffmpeg
      v4l-utils
      SDL2
      pkg-config
      cabextract
      unzip
      p7zip
      wineWowPackages.waylandFull
      winetricks
      gcc
      libGL
      picocom
      minicom
      fritzing
      kicad
      xorg.libX11
      xorg.libXcursor
      xorg.libXrandr
      xorg.libXinerama
      xorg.libXi
      xorg.libXxf86vm
      wf-recorder
      qflipper
      yabridge
      yabridgectl
      carla
      xorg.xhost
      ncdu
      piper
      quickshell
      vscode
      cherrytree
      gimp
      audacity
      
      # Sectools
      nmap masscan rustscan amass subfinder nuclei fierce dnsenum
      theharvester responder netexec enum4linux-ng nikto
    ];
   
  };





  networking.firewall.trustedInterfaces = [ "incusbr0" ];
  networking.firewall.allowedTCPPorts = [ 7474 7687 ];
  networking.firewall.enable = false;

  virtualisation.incus.ui.enable = true;
  virtualisation.incus.enable = true;

  networking.nftables.enable = true;

  services.neo4j = {
    enable = true;
    bolt.enable = true;
    https.enable = true;
    http.enable = true;
    # directories.home = "/var/lib/neo4j";
  };

  programs.appimage = {
    enable = true;
    binfmt = true;
  };

  fonts.packages = with pkgs; [
    nerd-fonts.fira-code
    nerd-fonts.droid-sans-mono
  ];

  programs.thunar.enable = true;

  nixpkgs.overlays = [
    (self: super: {
      mpv = super.mpv.override {
        scripts = [ self.mpvScripts.mpris ];
      };
    })
  ];

  programs.hyprland = {
    enable = true;
    xwayland.enable = true;
  };

  programs.firefox.enable = true;

  nixpkgs.config.allowUnfree = true;

  environment.systemPackages = with pkgs; [
    (dmenu.overrideAttrs (oldAttrs: {
      patches = (oldAttrs.patches or []) ++ [
        /home/aaron/flakes/scripts/dmenu-center-20250407-b1e217b.diff
      ];
    }))
    hyprpaper
    nwg-look

    # System-wide Python for all users (no GUI deps):
    (python311.withPackages (ps: with ps; [ numpy pip ]))
  ];

  environment.sessionVariables = {
    NIX_PROFILES = "/nix/store/mgm684yazy2rz7c7nflrjxckdzvg9hah-yabridge-5.1.1";
    YABRIDGE_PLUGIN_DIRS = "/home/aaron/.wine/drive_c/Program Files/Common Files/VST3";
  };

  services.udev.extraRules = ''
    # bladeRF udev rule
    SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6066", MODE="0660", GROUP="dialout"
  '';

  system.stateVersion = "25.05";
}
