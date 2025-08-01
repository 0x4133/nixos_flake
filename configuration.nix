# Edit this configuration file to define what should be installed on
# your system.  Help is available in the configuration.nix(5) man page
# and in the NixOS manual (accessible by running ‘nixos-help’).

{ config, pkgs, inputs, ... }:

  {   # Enable OpenGL
    hardware.graphics = {
      enable = true;
    };

    
   virtualisation.docker.enable = true;
    
  # Load nvidia driver for Xorg and Wayland
  services.xserver.videoDrivers = ["nvidia"];
  hardware.nvidia = {
 # Modesetting is required.
    modesetting.enable = true;
    # Nvidia power management. Experimental, and can cause sleep/suspend to fail.
    # Enable this if you have graphical corruption issues or application crashes after waking
    # up from sleep. This fixes it by saving the entire VRAM memory to /tmp/ instead 
    # of just the bare essentials.
    powerManagement.enable = false;

    # Fine-grained power management. Turns off GPU when not in use.
    # Experimental and only works on modern Nvidia GPUs (Turing or newer).
    powerManagement.finegrained = false;

    # Use the NVidia open source kernel module (not to be confused with the
    # independent third-party "nouveau" open source driver).
    # Support is limited to the Turing and later architectures. Full list of 
    # supported GPUs is at: 
    # https://github.com/NVIDIA/open-gpu-kernel-modules#compatible-gpus 
    # Only available from driver 515.43.04+
    open = false;

    # Enable the Nvidia settings menu,
	# accessible via `nvidia-settings`.
    nvidiaSettings = true;

    # Optionally, you may need to select the appropriate driver version for your specific GPU.
    package = config.boot.kernelPackages.nvidiaPackages.production;
  };
  
    
  nix.settings.experimental-features = ["nix-command" "flakes"];
  imports =
    [ # Include the results of the hardware scan.
      /etc/nixos/hardware-configuration.nix
    ];

  # Bootloader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.hostName = "nixos"; # Define your hostname.
  # networking.wireless.enable = true;  # Enables wireless support via wpa_supplicant.

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  # Enable networking
  networking.networkmanager.enable = true;

  # Set your time zone.
  time.timeZone = "America/Phoenix";

  # Select internationalisation properties.
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

  # Enable the X11 windowing system.
  services.xserver.enable = true;

  # Enable the GNOME Desktop Environment.
  services.xserver.displayManager.gdm.enable = true;
  services.xserver.desktopManager.gnome.enable = true;

  # Configure keymap in X11
  services.xserver.xkb = {
    layout = "us";
    variant = "";
  };

  # Enable CUPS to print documents.
  services.printing.enable = true;

  # Enable sound with pipewire.
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    # If you want to use JACK applications, uncomment this
    #jack.enable = true;

    # use the example session manager (no others are packaged yet so this is enabled by default,
    # no need to redefine it in your config for now)
    #media-session.enable = true;
  };

  # Enable touchpad support (enabled default in most desktopManager).
  # services.xserver.libinput.enable = true;

  # Define a user account. Don't forget to set a password with ‘passwd’.
  users.users.aaron = {
    isNormalUser = true;
    description = "aaron";
    extraGroups = [ "networkmanager" "wheel" "plugdev" "dialout" "docker" "incus-admin"];
    packages = with pkgs; [
    #  thunderbird
      # hyprland
       tesseract
       clipse
       slurp
       grim
       fish
       kitty
     # hyprpaper
       wofi
     # dolphin
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
      python3
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
    ];
  };

virtualisation.incus.ui.enable = true;
virtualisation.incus.enable = true;
networking.nftables.enable = true;


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
    # Install the packages from nixpkgs
    enable = true;
    # Whether to enable XWayland
    xwayland.enable = true;
   };
  # Install firefox.
  programs.firefox.enable = true;

  # Allow unfree packages
  nixpkgs.config.allowUnfree = true;




  # List packages installed in system profile. To search, run:
  # $ nix search wget
environment.systemPackages = with pkgs; [
  #  vim # Do not forget to add an editor to edit configuration.nix! The Nano editor is also installed by default.
  #  wget
  (dmenu.overrideAttrs (oldAttrs: {
    patches = (oldAttrs.patches or []) ++ [
      # Specify local patches:
      /home/aaron/flakes/scripts/dmenu-center-20250407-b1e217b.diff
    ];
  }))
  hyprpaper
  nwg-look

   # hyprpaper is added as a separate package after the dmenu override
  # If you want the unpatched dmenu as well, you would list it separately.
  # dmenu 
];
services.udev.extraRules = ''
  # bladeRF udev rule
  SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="6066", MODE="0660", GROUP="dialout"
'';
  # Some programs need SUID wrappers, can be configured further or are
  # started in user sessions.
  # programs.mtr.enable = true;
  # programs.gnupg.agent = {
  #   enable = true;
  #   enableSSHSupport = true;
  # };

  # List services that you want to enable:

  # Enable the OpenSSH daemon.
  # services.openssh.enable = true;

  # Open ports in the firewall.
  # networking.firewall.allowedTCPPorts = [ ... ];
  # networking.firewall.allowedUDPPorts = [ ... ];
  # Or disable the firewall altogether.
  # networking.firewall.enable = false;

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It‘s perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  # Before changing this value read the documentation for this option
  # (e.g. man configuration.nix or on https://nixos.org/nixos/options.html).
  system.stateVersion = "25.05"; # Did you read the comment?

}
