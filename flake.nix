{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
    fenix.url = "github:nix-community/fenix";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs =
    { self
    , nixpkgs
    , devenv
    , systems
    , ...
    } @ inputs:
    let
      forEachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    {
      packages = forEachSystem (system: {
        devenv-up = self.devShells.${system}.default.config.procfileScript;
      });

      devShells =
        forEachSystem
          (system:
            let
              pkgs = nixpkgs.legacyPackages.${system};
            in
            {
              default = devenv.lib.mkShell {
                inherit inputs pkgs;
                modules = [
                  {
                    scripts.build-libscanmem.exec = ''
                      compile_libscanmem() {
                        sh autogen.sh
                        ./configure --prefix="$(pwd)"
                        make -j"$NUM_MAKE_JOBS"
                        return 0
                      }

                      echo "[i] Downloading libscanmem"
                      git submodule update --init --recursive

                      echo "[i] Compiling libscanmem"
                      if [ ! -d "libpince/libscanmem" ]; then
                          mkdir libpince/libscanmem
                      fi
                      cd libscanmem-PINCE
                      if [ -d "./.libs" ]; then
                          echo "[*] Artifacts found, recompile anyway ? [y/n] "
                          read -r answer
                          if echo "$answer" | grep -iq "^[Yy]"; then
                              compile_libscanmem
                          fi
                      else
                          compile_libscanmem
                      fi

                      echo "[i] Copying libscanmem artifacts to libpince"
                      cp --preserve .libs/libscanmem.so ../libpince/libscanmem/
                      cp --preserve wrappers/scanmem.py ../libpince/libscanmem
                    '';

                    scripts.pince.exec = ''
                      sudo -E PYTHONPATH=$PYTHONPATH PYTHONDONTWRITEBYTECODE=1 ./PINCE.py
                    '';

                    languages = {
                      c.enable = true;

                      python = {
                        enable = true;
                        venv = {
                          enable = true;
                          requirements = builtins.readFile ./requirements.txt;
                        };
                      };
                    };

                    packages = with pkgs; [
                      # PINCE
                      gdb
                      libtool
                      cairo
                      gobject-introspection
                      qt6.qttools
                      python311Packages.pyqt6
                      gtk3

                      # libscanmem
                      automake
                      autoconf
                    ];
                  }
                ];
              };
            });
    };
}
